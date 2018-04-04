from config import config
import functions

import os
import json
import datetime

from twisted.internet import defer, threads
from twisted.web import resource, server
from txrestapi.resource import APIResource
from txrestapi.methods import GET, POST, PUT, ALL
from models import Log

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
            status, _message = functions.getstatusoutput(command, env=env)
            if status == 0:
                message = "repo %s create succeed." % repo_uri
                Log(section='repository', message=message)
            else:
                message = "repo create failed. %s " % _message
            
            return {'status': status, 'message': message}

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET
    
    @GET('/(?P<reponame>[^/]+)/update')
    def get_update(self, request, reponame):
        def get_result():
            repo_base = config['cache']['repos']
            repo_json = os.path.join(repo_base, reponame, 'update.json')
            if os.path.exists(repo_json):
                result = json.loads(open(repo_json, 'r').read())
            else:              
                result = {
                    "basetgz": [{"i386": {"url": "url", "md5sum": "md5sum"}},
                                {"amd64": {"url": "url", "md5sum": "md5sum"}}],
                    "archives": ["deb http://pools.corp.deepin.com/deepin unstable main contrib"]
                    }
                result['timestamp'] = datetime.datetime.now().strftime('%s')
            
            return {'status': 0, 'config': result}

        d = threads.deferToThread(get_result)
        d.addCallback(self.callback, request)
        d.addErrback(self.failure, request)
        return server.NOT_DONE_YET

    @POST('/update')
    def post_update(self, request):
        def get_result():
            headers = request.getAllHeaders()
            content = cgi.FieldStorage(
                fp = request.content,
                headers = headers,
                environ = {'REQUEST_METHOD':'POST',
                        'CONTENT_TYPE': headers['content-type'],}
                )
            repo_base = config['cache']['repos']
            reponame = content['reponame'].value
           
            try:
                update_config = json.loads(eval(content['config'].value))
                repo_json = os.path.join(repo_base, reponame, '.update.json')
                with open(repo_json, 'w') as fp:
                    fp.write(json.dumps(update_config, indent=4))
                os.rename(repo_json, os.path.join(repo_base, reponame, 'update.json'))
                Log(section='repository', message='update %s json config' % reponame)
                return {'status': 0, 'message': 'update done'}

            except:
                return {'status': 1, 'message': 'update failed'}

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
            Log(section='repository', message='create division reponame %s/%s' % (repo_uri, division_name))
            return dict(zip(['status', 'message'], functions.getstatusoutput(command, env=env)))


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
                Log(section='repository', message='destroy repository %s' % repo_uri)
                return dict(zip(['status', 'message'], 
                    functions.getstatusoutput("rm -r %s" % repo_path, env=env)
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