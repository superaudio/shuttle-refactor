#!/usr/bin/env python

__metaclass__ = type

from twisted.internet import protocol
from twisted.internet import process 
from twisted.internet import reactor as default_reactor
from twisted.python import log

import urllib2
import requests
import hashlib
import os
import xmlrpclib
import ConfigParser

from twisted.web import xmlrpc

devnull = open("/dev/null", "r")

class BuilderStatus:
    IDLE         = "BuilderStatus.IDLE"
    BUILDING     = "BuilderStatus.BUILDING"
    WAITING      = "BuilderStatus.WAITING"
    ABORTING     = "BuilderStatus.ABORTING"
    UNKNOWN      = "BuilderStatus.UNKNOWN"
    OFFLINE      = "BuilderStatus.OFFLINE"

class BuildStatus:
    OK            = "BuildStatus.OK"
    GIVENBACK     = "BuildStatus.GIVENBACK"
    DEPFAIL       = "BuildStatus.DEPFAIL"
    BUILDFAIL     = "BuildStatus.BUILDFAIL"
    ABORTED       = "BuildStatus.ABORTED"

class BuildDSlave:
    """Build Daemon slave"""
    def __init__(self, config):
        self._config = config
        self.builderstatus = BuilderStatus.IDLE
        self._cachepath = self._config.get("slave", "filecache")
        try:
            self._binpath = self._config.get("slave", "tools")
        except ConfigParser.NoOptionError:
            self._binpath = None
        self.buildstatus = BuildStatus.OK
        self.waitingfiles = {}
        self.builddependencies = ""
        self._log = None
        if not os.path.exists(self._cachepath):
            os.makedirs(self._cachepath)

        if not os.path.isdir(self._cachepath):
            raise ValueError("FileCache path: %s is not a dir" % self._cachepath)

    def getArches(self):
        return self._config.get("slave", "arches").split()
 
    def getDists(self):
        return self._config.get("slave", "dists").split()

    def cachePath(self, file):
        return os.path.join(self._cachepath, file)

    def log(self, data):
        #if isinstance(data, bytes):
        #    data = data.decode()
        if self._log is not None:
            self._log.write(data)
            self._log.flush()

        if data.endswith("\n"):
            data = data[:-1]

    def addWaitingFile(self, path):
        self.waitingfiles[os.path.basename(path)] = path

    def abort(self):
        if self.builderstatus == BuilderStatus.ABORTING:
            self.log("Slave already ABORTING when asked to abort")
            return
        if self.builderstatus != BuilderStatus.BUILDING: 
            raise ValueError("Slave is not BUILDING when asked to abort")

        self.manager.abort()
        self.builderstatus = BuilderStatus.ABORTING

    def clean(self):
        if self.builderstatus != BuilderStatus.WAITING and self.builderstatus != BuilderStatus.ABORTING:
            raise ValueError("Slave is not WAITING or ABORTING when asked to clean %s" % self.builderstatus)
        for f in set(self.waitingfiles.values()):
            os.remove(self.cachePath(f))

        self.builderstatus = BuilderStatus.IDLE
        if self._log is not None:
            self._log.close()
            os.remove(self.cachePath("buildlog"))
            self._log = None

        self.waitingfiles = {}
        self.manager = None
        self.builddependencies = ""
        self.buildstatus = BuildStatus.OK

    def getLogTail(self):
        if self._log is None:
            return ""

        rlog = None
        try:
            try:
                rlog = open(self.cachePath("buildlog"), "rb")
            except IOError:
                rlog = None
                ret = ""
            else:
                rlog.seek(0, os.SEEK_END)
                count = rlog.tell()
                if count > 2048:
                    count = 2048
                rlog.seek(-count, os.SEEK_END)
                ret = rlog.read(count)
        finally:
            if rlog is not None:
                rlog.close()
        return ret

    def startBuild(self, manager):
        if self.builderstatus != BuilderStatus.IDLE:
            raise ValueError("Slave is not IDLE when asked to start building")
        self.manager = manager
        self.builderstatus = BuilderStatus.BUILDING
        self.emptycache()
        self.emptylog()
    
    def emptycache(self):
        if self._log is not None:
            self._log.close()
        filelist = os.listdir(self._cachepath)
        for f in filelist:
            filepath = self.cachePath(f)
            if os.path.isfile(filepath):
                os.remove(filepath)

    def emptylog(self):
        self._log = open(self.cachePath("buildlog"), "w")

    def buildFail(self, info=None):
        if self.builderstatus not in (BuilderStatus.BUILDING, BuilderStatus.ABORTING):
            raise ValueError("Slave is not BUILDING|ABORTING when set to BUILDERFAIL")
        if info:
           self._log.write("Build Failed - %s \n" % info)
           self._log.flush()

        self.buildstatus = BuildStatus.BUILDFAIL

    def buildAborted(self):
        self._log.write("Build Abort.\n") 
        if self.builderstatus != BuilderStatus.ABORTING:
            raise ValueError("Slave is not ABORTING when set to ABORTED")
        if self.buildstatus != BuildStatus.BUILDFAIL:
            self.buildstatus = BuildStatus.ABORTED

    def buildComplete(self):
        if self.builderstatus == BuilderStatus.BUILDING:
            self.builderstatus = BuilderStatus.WAITING
        elif self.builderstatus == BuilderStatus.ABORTING:
            self.buildAborted()
            self.builderstatus == BuilderStatus.WAITING
        else:
            raise ValueError("Slave is not BUILDING|ABORTING when told build is complete")

    def buildOK(self):
        if self.builderstatus != BuilderStatus.BUILDING:
            raise ValueError("Slave is not BUILDING when set to OK")
        self.buildstatus = BuildStatus.OK
        
class RunCapture(protocol.ProcessProtocol):
    """Run a command and capture its output to a slave's log"""

    def __init__(self, slave, callback):
        self.slave = slave
        self.notify = callback
        self.builderFailCall = None
        self.ignore = False

    def outReceived(self, data):
        """Pass on stdout data to the log."""
        self.slave.log(data)

    def errReceived(self, data):
        """Pass on stderr data to the log.

        With a bit of luck we won't interleave horribly."""
        self.slave.log(data)

    def processEnded(self, statusobject):
        """This method is called when a child process got terminated.

        Two actions are required at this point: eliminate pending calls to
        "builderFail", and invoke the programmed notification callback.  The
        notification callback must be invoked last.
        """
        if self.ignore:
            # The build manager no longer cares about this process.
            return

        # Since the process terminated, we don't need to fail the builder.
        if self.builderFailCall and self.builderFailCall.active():
            self.builderFailCall.cancel()

        # notify the slave, it'll perform the required actions
        if self.notify is not None:
            self.notify(statusobject.value.exitCode)


class BuildManager:
    """Build Daemon slave build manager abstract parent"""

    def __init__(self, slave, buildid, reactor=None):
        """Create a BuildManager.

        :param slave: A `BuildDSlave`.
        :param buildid: Identifying string for this build.
        """
        self._buildid = buildid
        self._slave = slave
        if reactor is None:
            reactor = default_reactor
        self._reactor = reactor
        self._subprocess = None
        self._reaped_states = set()
        self.home = os.environ['HOME']
        self.abort_timeout = 30

    def runSubProcess(self, command, args, iterate=None, env=None, path=None):
        """Run a sub process capturing the results in the log."""
        if iterate is None:
            iterate = self.iterate
        if path is None:
            path = self.home
        self._subprocess = RunCapture(self._slave, iterate)
        self._slave.log("Run: %s %s\n" % (command, " ".join(args))
        childfds = {0: devnull.fileno(), 1: "r", 2: "r"}
        self._reactor.spawnProcess(
            self._subprocess, command, args, env=env,
            path=path, childFDs=childfds)

    def initiate(self, files, extra_args):
        raise NotImplementedError("BuildManager should be subclassed to be used")

    def iterate(self, success):
        raise NotImplementedError("BuildManager should be subclassed to be used")

    def iterateReap(self, state, success):
        raise NotImplementedError("BuildManager should be subclassed to be used")

    def abortReap(self):
        raise NotImplementedError("BuildManager should be subclassed to be used")

    def abort(self):
        """Abort the build by killing the subprocess."""
        if self.alreadyfailed or self._subprocess is None:
            return
        else:
            self.alreadyfailed = True
        primary_subprocess = self._subprocess
        self.abortReap()
        self._subprocess.builderFailCall = self._reactor.callLater(
            self.abort_timeout, self.builderFail,
            "Failed to kill all processes.", primary_subprocess)

    def builderFail(self, reason, primary_subprocess):
        """Mark the builder as failed."""
        self._slave.log("ABORTING: %s\n" % reason)
        self._subprocess.builderFailCall = None
        self._slave.builderFail()
        self.alreadyfailed = True
        try:
            primary_subprocess.transport.signalProcess('KILL')
        except process.ProcessExitedAlready:
            self._slave.log("ABORTING: Process Exited Already\n")
        primary_subprocess.transport.loseConnection()
        # Leave the reaper running, but disconnect it from our state
        # machine.  Perhaps an admin can make something of it, and in any
        # case scan-for-processes elevates itself to root so it's awkward to
        # kill it.
        self._subprocess.ignore = True
        self._subprocess.transport.loseConnection()

class XMLRPCBuildDSlave(xmlrpc.XMLRPC):
    def __init__(self, config):
        xmlrpc.XMLRPC.__init__(self, allowNone=True)
        self.protocolversion = '1.0'
        self.slave = BuildDSlave(config)
        self._builders = {}
        #TODO: add version detect
        self._version = "unreleased"

        log.msg("Initialized")

    def registerBuilder(self, builderclass, buildertag):
        self._builders[buildertag] = builderclass

    def xmlrpc_echo(self, *args):
        return args

    def xmlrpc_info(self):
        return {"arches": self.slave.getArches(), "dists": self.slave.getDists(), "builders": list(self._builders.keys())}

    def xmlrpc_status(self):
        status = self.slave.builderstatus
        statusname = status.split('.')[-1]
        func = getattr(self, "status_" + statusname, None)
        if func is None:
            raise ValueError("Unknow status: '%s'" % status)
        ret = {"builder_status": status}
        if self._version is not None:
            ret["builder_version"] = self._version
        ret.update(func())
        return ret

    def status_IDLE(self):
        return {}

    def status_BUILDING(self):
        tail = self.slave.getLogTail()
        return {"build_id": self.buildid, "logtail": xmlrpclib.Binary(tail)}

    def status_WAITING(self):
        ret = {"build_status": self.slave.buildstatus, "build_id": self.buildid }
        if self.slave.buildstatus == BuildStatus.OK:
            ret["filemap"] = self.slave.waitingfiles
        return ret

    def status_ABORTING(self):
        return {"build_id": self.buildid, "filemap": self.slave.waitingfiles}

    def xmlrpc_abort(self):
        self.slave.abort()
        return BuilderStatus.ABORTING

    def xmlrpc_clean(self):
        self.slave.clean()
        return BuilderStatus.IDLE

    def xmlrpc_build(self, buildid, builder, files, extra_args):
        if not builder in self._builders:
            extra_info = "%s not in %r" % (builder, self._builders.keys())
            return (BuilderStatus.UNKNOWNBUILDER, extra_info)

        self.buildid = buildid
        self.slave.startBuild(self._builders[builder](self.slave, buildid))
        self.slave.manager.initiate(files, extra_args)
        return (BuilderStatus.BUILDING, buildid) 
