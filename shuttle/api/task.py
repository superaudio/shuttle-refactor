from twisted.web import resource, server
from twisted.internet import defer, threads

import json
import os
import subprocess
import traceback
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL

from models import Package
from config import config

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
                """result will like blow
                {'files': 
                    ['dde-session-ui_4.3.1+2+gc1ab148.dsc', 
                    'dde-session-ui_4.3.1+2+gc1ab148.tar.xz'], 
                'path': '/tmp/git-archive-temp/tmp3HoN4D',
                'version': '4.3.1+2+gc1ab148', 
                'hashsum': 'c1ab1484818011ab76bbe383101b25d33e923ef4'
                }
                """
                result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
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
            
                #save the source to cache
                tasks_cache = config['cache'].get('tasks')
                if not os.path.exists(tasks_cache):
                    os.makedirs(tasks_cache)
                source_cache = os.path.join(tasks_cache, str(package.id), 'source')
                for file in result['files']:
                    os.system("install -Dm644 %(source)s %(dest)s" % {
                        'source': os.path.join(result['path'], file),
                        'dest': os.path.join(source_cache, file)
                        })
                    
            os.system("rm -rf %s" % result['path'])
            return package.dict()
        
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
            package = Package.selectBy(id=id)[0]
            return package.dict()
        
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