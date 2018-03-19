from __future__ import absolute_import

from twisted.web import server
from twisted.internet import defer, threads

import json

from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL
from slaves import ShuttleBuilders, BuilderSlave

class ListWorkers(APIResource):
    isLeaf = False

    @ALL('/list')
    def list_workers(self, request):
        '''
        GET /api/workers/list

            {
                "debian@worker1": {
                "name": "",
                "url": "",
                "enabled": "",
                "status": "",
                "uploading": ""
                }
            }
        '''
        request.setHeader("content-type", "application/json")
        def callback(result):
            request.setResponseCode(200)
            request.write(json.dumps(result))
            request.finish()

        def failure(result):
            request.setResponseCode(400)
            _result = {"state": "FAILED",
                "message": result.getErrorMessage()
            }
            request.write(json.dumps(_result))
            request.finish()
        
        def get_result():
            result = {}
            for slave in ShuttleBuilders().slaves:
                _result = {
                    'name': slave.name, 'url': slave.url, 'enabled': slave.enabled,
                    'status': slave.status, 'uploading': slave.uploading
                }
                result[slave.name] = _result
            return result
        
        d = threads.deferToThread(get_result)
        d.addCallback(callback)
        d.addErrback(failure)
        return server.NOT_DONE_YET