from twisted.web import resource, server
from twisted.internet import defer, threads

import json
import os
import subprocess
import traceback
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL

from models import Log
from config import config

class LogResource(APIResource):
    isLeaf = False

    @GET('/monitor')
    def get_moitory(self, request):
        def get_result():
            logs = Log.selectBy().orderBy("-id")[:20]
            result = []
            for log in logs:
                result.append(log.dict())
            
            if request.args.get('reverse'):
                result.reverse()

            return {'result': result}
        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET
    
    @GET('/task/(?P<id>[^/]+)')
    def get_uploadlog(self, request, id):
        def get_result():
            uploadlog = os.path.join(config['cache']['tasks'], str(id), 'uploadlog')
            if os.path.exists(uploadlog):
                with open(uploadlog, 'rb') as fp:
                    log = fp.read()
            else:
                log = "no uploadlog found."
            
            return {'log': bytes(log)}
        
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