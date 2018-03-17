import threading
import sqlobject
import signal

import functools
import time
import xmlrpclib
import socket
from twisted.web import client
import sys

from models import Job, JobStatus, Package

from urlparse import urljoin

from config import config

def urlappend(baseurl, path):
    assert not path.startswith('/')
    if not baseurl.endswith('/'):
        baseurl += '/'

    return urljoin(baseurl, path)

class BuilderStatus:
    IDLE     = "BuilderStatus.IDLE"
    BUILDING = "BuilderStatus.BUILDING"
    WAITING  = "BuilderStatus.WAITING"
    ABORTING = "BuilderStatus.ABORTING"
    UNKNOWN  = "BuilderStatus.UNKNOWN"
    OFFLINE  = "BuilderStatus.OFFLINE"

class FileWritingQueue():
    def __init__(self):
        self.working = False
        self.tasks = []
        self.drain = None
    
    def download(self, data):
        url = data[0]
        filename = data[1]
        basepath = os.path.dirname(filename)
        if not os.path.exists(basepath):
            os.makedirs(basepath)
        d = client.downloadPage(url, filename, timeout=300)
        return d
    
    def push(self, data):
        self.tasks.append(data)
        self.process()

    def task_finished(self, *args):
        self.working = False
        if len(self.tasks) == 0 and self.drain:
            self.drain()
        self.process()

    def process(self):
        if len(self.tasks) != 0 and self.working:
            return
        task = self.tasks.pop(0)
        self.working = True
        d = self.download(task)
        d.addBoth(self.task_finished)


class BuilderSlave():
    def __init__(self, name, url, interval=5):
        self.name = name
        self.url = url
        self.enabled = False
        self.status = {}
        self.interval = interval

        self.uploading = False
        self.proxy = xmlrpclib.ServerProxy(urlappend(self.url, 'rpc'))
        self._file_cache_url = urlappend(self.url, 'filecache')
        self.stop = None
    
    def build(self, buildid, builder, *args):
        return self.proxy.build(buildid, builder, *args)

    def proxy_complete(self):
        if self.uploading:
            return

        if self.status.get('builder_status', None) == "BuilderStatus.ABORTING":
            buildid = self.status.get('buildid', None)
            job = Jobs.get_all_jobs(id=buildid)[0]
            self.complete(job, JobStatus.CANCELED)
        
        if self.status.get('builder_status', None) == 'BuilderStatus.WAITING':
            buildid = self.status.get('build_id', None)
            job = Jobs.get_all_jobs(id=buildid)[0]
            if self.status.get('build_status') == "BuildStatus.OK":
                status = JobStatus.BUILD_OK
            else:
                status = JobStatus.FAILED
                
            self.complete(job, status)
    
    def complete(self, job, status):
        files = self.status.get("filemap", {})
        files.add('buildlog')
        self.uploading = True
        queue = FileWritingQueue()
        queue.drain = functools.partial(self.upload_done, job, status)
        for file in files:
            url = urlappend(self._file_cache_url, file)
            save = os.path.join(basepath, file)
            queue.push([url, save])
    
    def upload_done(self, job, status):
        self.uploading = False
        self.proxy.clean()
        job.status = status

    def _heartbeat(self):
        stopped = threading.Event()
        def loop():
            while not stopped.wait(self.interval):
                try:
                    self.status = self.proxy.status()
                except:
                    self.status = {'status': 'BuilderStatus.OFFLINE'}
                self.proxy_complete()
                
        threading.Thread(target=loop).start()    
        return stopped.set

    def active(self):
        if not self.enabled:
            self.enabled = True
            self.stop = self._heartbeat()

    def inactive(self):
        if self.enabled:
            self.enabled = False
            if self.stop:
                self.stop()

            self.status = {}


class ShuttleBuildersDaemon(threading.Thread):

    slaves = []
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init()
        return cls._instance

    def init(self):
        self._sqlconnection = sqlobject.connectionForURI(config['runtime'].get('database_uri'))
        sqlobject.sqlhub.processConnection = self._sqlconnection

        self.jobs_locker = threading.Lock()
        self.do_quit = threading.Event()

    def daemonize(self):
        signal.signal(signal.SIGTERM, self.handle_sigterm)
        signal.signal(signal.SIGINT, self.handle_sigterm)
        try:
            sys.stdout = sys.stderr = open("builder.log", "a")
        except Exception as err:
            print("Error: unstable to open logfile: %s" % err)
    
    def loop(self):
        counter = 5
        while not self.do_quit.isSet():
            if counter == 5:
                counter = 0
            self.do_quit.wait(1)
            counter += 1

    def daemon(self):
        self.daemonize()
        self.loop()

    def register_slave(self, slave):
        for _slave in self.slaves:
            if _slave.url == slave.url or _slave.name == slave.name:
                return
        slave.active()
        self.slaves.append(slave)
    
    def toggle_slave(self, slave_name):
        for _slave in self.slaves:
            if _slave.name == slave_name:
                if _slave.enable:
                    _slave.inactive()
                else:
                    _slave.active()
                break
    
    def handle_sigterm(self, signum, stack):
        self.do_quit.set()
        for slave in self.slaves:
            slave.inactive()

if __name__ == '__main__':
    sqlconnection = sqlobject.connectionForURI(config['runtime'].get('database_uri'))
    sqlobject.sqlhub.processConnection = sqlconnection
    Package.createTable(ifNotExists=True)
    Job.createTable(ifNotExists=True)
    daemon = ShuttleBuildersDaemon()
    slave = BuilderSlave('debian-builder-01', 'http://10.0.10.29:8221/')
    daemon.register_slave(slave)
    daemon.daemon()
