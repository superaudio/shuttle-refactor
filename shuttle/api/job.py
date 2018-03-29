from twisted.web import resource, server
from twisted.internet import defer, threads

import json
import os
import subprocess
import traceback
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL

from models import Package, Job
from models import JobStatus
from config import config

from slaves import ShuttleBuilders, BuilderSlave

class JobResource(APIResource):
    isLeaf = False

    @GET('/(?P<id>[^/]+)/info')
    def get_jobinfo(self, request, id):
        '''
        GET /api/job/<id>/info

        {
            "state": "SUCCESS",
            "id": "xxxxx"
        }
        '''
        def get_result():
            job = Job.selectBy(id=id)[0]
            result = job.dict()
            result.update(job.package.dict())
            return result

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET
    
    @GET('/(?P<id>[^/]+)/log')
    def get_logtail(self, request, id):
        def get_result():
            job = Job.selectBy(id=id)[0]
            log = "Loading buildlog ... "
            if job.status == JobStatus.BUILDING:
                autorefresh = True
                for slave in ShuttleBuilders().slaves:
                    if job.build_host == slave.name:
                        status = slave.proxy.status()
                        log = status.get('logtail', 'Waiting buildlog downloading...')
                        break
            else:
                autorefresh = False
                log_path = os.path.join(config['cache']['tasks'], str(job.package.id), 
                    '%s-%s' % (job.dist, job.arch), 'buildlog')
                if os.path.exists(log_path):
                    with open(log_path, 'rb') as fp:
                        fp.seek(0, os.SEEK_END)
                        count = fp.tell()
                        fp.seek(-count, os.SEEK_END)
                        log = fp.read(count)
            
            result = {
                "autorefresh": autorefresh,
                "log": bytes(log)
            }
            return result
        
        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    def callback(self, result, request):
        request.setResponseCode(200)
        request.write(json.dumps(result))
        request.finish()

    def failure(self, result, request):
        request.setResponseCode(400)
        _result = {"state": "FAILED",
            "message": result.getErrorMessage()
        }
        request.write(json.dumps(_result))
        request.finish()