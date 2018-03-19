from twisted.web import resource, server
from twisted.internet import defer, threads

import json
import subprocess
import traceback
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL

from models import Package

def deunicodify_hook(pairs):
    new_pairs = []
    for key, value in pairs:
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        new_pairs.append((key, value))
    return dict(new_pairs)

def add_task(kwargs):
    if Package.selectBy(**kwargs).count() != 0:
        package = Package.selectBy(**kwargs).orderBy('-id')[0]
        package.triggered = package.triggered + 1
    else:
        package = package(**kwargs)

class Task(APIResource):
    isLeaf = False  

    @POST('/apply')
    def post_apply(self, request):
        '''
        POST /api/task/apply

        {
            "state": "SUCCESS",
            "id": "xxxxx"
        }
        '''
        request.setHeader("content-type", "application/json")
        
        def get_result():
            content = json.loads(request.content.read(), object_pairs_hook=deunicodify_hook)
            command = "../tools/git.py --config ../config/default.packages.json "
            command += " --pkgname %(pkgname)s --action %(action)s" % {
                "pkgname": content['pkgname'],
                "action": content['action']
            }

            try:
                result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
                print(result)
            except:
                raise
            
            result = eval(result)

            kwargs = {
                'pkgname': content['pkgname'], 'pkgver': result['version'], 
                'reponame': content['reponame'], 'action': content['action'],
                'hashsum': result['hashsum']
                }

            if Package.selectBy(**kwargs).count() != 0:
                package = Package.selectBy(**kwargs).orderBy('-id')[0]
                package.triggered = package.triggered + 1
            else:
                package = Package(**kwargs)
            
            return package.id
        
        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @GET('/(?P<id>[^/]+)/info')
    def get_jobinfo(self, request, id):
        '''
        GET /api/task/<id>/info

        {
            "state": "SUCCESS",
            "id": "xxxxx"
        }
        '''
        def get_result():
            return {'id': id}
        
        d = threads.deferToThread(get_result)
        d.addBoth(self.callback, request)
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