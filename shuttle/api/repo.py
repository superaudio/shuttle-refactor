from config import config
import functions

import os
import json

from twisted.internet import defer, threads
from twisted.web import resource, server
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL

import cgi

class Repo(APIResource):
    isLeaf = False  

    @POST('/create')
    def post_create(self, request):
        def get_result():
            headers = request.getAllHeaders()
            content = cgi.FieldStorage(
                fp = request.content,
                headers = headers,
                environ = {'REQUEST_METHOD':'POST',
                        'CONTENT_TYPE': headers['content-type'],}
                )

            repo_uri = content['reponame'].value
            repo_base = config['cache']['repos']
            repo_json = os.path.join(repo_base, repo_uri, '%s.json' % repo_uri)
            if os.path.exists(repo_json):
                raise OSError("repo has already created.")

            if not os.path.exists(os.path.join(repo_base, repo_uri)):
                os.makedirs(os.path.join(repo_base, repo_uri))

            with open(repo_json, 'w') as fp:
                fp.write(content['config'].value)
            
            env = os.environ.copy()
            env['REPOPATH'] = repo_base
            env['NAME'] = repo_uri
            command = "../tools/repo.py create"
            return dict(zip(['status', 'message'], functions.getstatusoutput(command, env=env)))

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @POST('/division')
    def post_subcreate(self, request):
        def get_result():
            content = json.loads(request.content.read())
            repo_uri = content['reponame']
            division_name = content['division']
            base_repo = content['baserepo']

            repo_base = config['cache']['repos']
            repo_json = os.path.join(repo_base, repo_uri, '%s.json' % repo_uri)

            if not os.path.exists(repo_json):
                raise OSError("repo is not created.")
            repo_config = json.loads(open(repo_json, 'r').read())
            if not repo_config.get(base_repo):
                raise OSError("division repo is not supported.")
            
            env = os.environ.copy()
            env['REPOPATH'] = repo_base
            env['NAME'] = repo_uri

            command = "../tools/repo.py division --base %(base)s --division %(division)s" % {
                    "base": base_repo,
                    "division": division_name
            }
            return dict(zip(['status', 'message'], getstatusoutput(command, env=env)))


        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET
    
    @POST('/destroy')
    def post_destory(self, request):
        def get_result():
            content = json.loads(request.content.read())
            repo_uri = content['repouri']
            if repo_uri is None:
                raise OSError("reponame should not be none")

            repo_base = config['cache']['repos']
            
                
            repo_path = os.path.join(repo_base, repo_uri)

            if os.path.exists(repo_path):
                return dict(zip(['status', 'message'], 
                    getstatusoutput("rm -r %s" % repo_path, env=env)
                ))
            else:
                return dict(zip(['status', 'message'], [1, "%s is not exists" % repo_uri]))
        
        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @ALL('/list')
    def list_repo(self, request):
        def get_result():
            return functions.list_repo()
        
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