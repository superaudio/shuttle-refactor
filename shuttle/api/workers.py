from __future__ import absolute_import

from twisted.web import server
from twisted.internet import defer, threads

import json

from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL
from slaves import ShuttleBuilders, BuilderSlave

class Workers(APIResource):
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
        
        def get_result():
            result = []
            for slave in ShuttleBuilders().slaves:
                _result = {
                    'hostname': slave.name, 'url': slave.url, 'enabled': slave.enabled,
                    'builder_status': slave.status.get('builder_status'), 
                    'uploading': slave.uploading, 
                    'builder_info': slave.info
                }
                result.append(_result)
            return {'data': result}
        
        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @POST('/register')
    def register_worker(self, request):
        content = json.loads(request.content.read())
        name = content.get('name')
        url = content.get('url')
        def get_result():
            if name is None or url is None:
                return {'message': 'register slave failed.'}

            slave = BuilderSlave(name, url)
            ShuttleBuilders().register_slave(slave)
            result = {
                'hostname': slave.name, 'url': slave.url, 'enabled': slave.enabled,
                'status': slave.status.get('status'), 'uploading': slave.uploading
                }
            return result

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET
    
    @POST('/active')
    def active_worker(self, request):
        content = json.loads(request.content.read())
        name = content.get('name')
        def get_result():
            for slave in ShuttleBuilders().slaves:
                if slave.name == name:
                    slave.active()
                    return {'message': 'slave %s actived' % name}
            return {'message': 'something smell wrong.'}

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @POST('/remove')
    def remove_worker(self, request):
        content = json.loads(request.content.read())
        name = content.get('name')
        def get_result():
            for slave in ShuttleBuilders().slaves:
                if slave.name == name:
                    ShuttleBuilders().slaves.pop(slave)
                    return {'message': 'slave %s removed' % name}
            
            return {'message': 'something smell wrong.'}

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
        try:
            message = result.getErrorMessage()
        except Exception as e:
            message = str(e)
            
        _result = {"state": "FAILED",
            "message": message
        }
        request.write(json.dumps(_result))
        request.finish()