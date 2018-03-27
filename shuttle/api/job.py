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