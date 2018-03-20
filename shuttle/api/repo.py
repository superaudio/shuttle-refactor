from config import config, getstatusoutput
import os
import json
import subprocess

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

            repo_name = content['reponame'].value
            repo_base = config['cache']['repos']
            repo_json = os.path.join(repo_base, repo_name, '%s.json' % repo_name)
            if os.path.exists(repo_json):
                raise OSError("repo has already created.")

            if not os.path.exists(os.path.join(repo_base, repo_name)):
                os.makedirs(os.path.join(repo_base, repo_name))

            with open(repo_json, 'w') as fp:
                fp.write(content['config'].value)
            
            env = os.environ.copy()
            env['REPOPATH'] = repo_base
            env['NAME'] = repo_name

            return dict(zip(['status', 'message'], getstatusoutput(command, env=env)))

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @POST('/division')
    def post_subcreate(self, request):
        def get_result():
            content = json.loads(request.content.read())
            repo_name = content['reponame']
            division_name = content['division']
            base_repo = content['baserepo']

            repo_base = config['cache']['repos']
            repo_json = os.path.join(repo_base, repo_name, '%s.json' % repo_name)

            if not os.path.exists(repo_json):
                raise OSError("repo is not created.")
            repo_config = json.loads(open(repo_json, 'r').read())
            if not repo_config.get(base_repo):
                raise OSError("division repo is not supported.")
            
            env = os.environ.copy()
            env['REPOPATH'] = repo_base
            env['NAME'] = repo_name

            command = "../tools/repo.py division --base %(base)s --division %(division)s" % {
                    "base": base_repo,
                    "division": division_name
            }
            return dict(zip(['status', 'message'], getstatusoutput(command, env=env)))


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