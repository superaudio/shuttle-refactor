from twisted.web import resource
from twisted.web import server
from template import Jinja2TemplateLoader

import json

class RepoView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')

    def render_GET(self, request):
        task = {
            'id': '0001',
            'pkgname': 'dde-daemon',
            'pkgver': '1.0+git20181206',
            'action': 'commit', 'reponame': 'dde',
            'hashsum': 'abcdefetkkd', 'triggered': 3,
            'dist': 'unstable', 'arch': 'i386',
            'args': ['use-network', 'binnmu=yes'],
            'build_host': 'builder02@localhost',
            'state': 'STARTED',
            'build_start': '2018-03-02',
            'build_end': '2018-03-03'
        }

        context = {'task': task}
        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        template = self.loader.load("repo.html")

        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render(**context)
        d.addCallback(cb)
        return server.NOT_DONE_YET

class ReposView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')

    def render_GET(self, request):
        task = {
            '0001' : {
            'id': '0001',
            'pkgname': 'dde-daemon',
            'pkgver': '1.0+git20181206',
            'action': 'commit', 'reponame': 'dde',
            'hashsum': 'abcdefetkkd', 'triggered': 3,
            'tasks': [{'id': '4', 'task':'unstable/i386'}],
            'args': ['use-network', 'binnmu=yes'],
            'build_host': 'builder02@localhost',
            'state': 'STARTED',
            'build_start': '2018-03-02',
            'build_end': '2018-03-03'
            },
            '0002' : {
            'id': '0002',
            'pkgname': 'dde-dock',
            'pkgver': '1.0+git20181206',
            'action': 'commit', 'reponame': 'default',
            'hashsum': 'abcdefetkkd', 'triggered': 3,
            'tasks': [{'id': '1', 'task': 'unstable/i386'}, 
                {'id': '2', 'task': 'unstable/amd64'}],
            'args': ['use-network', 'binnmu=yes'],
            'build_host': 'builder02@localhost',
            'state': 'STARTED',
            'build_start': '2018-03-02',
            'build_end': '2018-03-03'
            }
        }

        context = {'task': task}
        if request.args.get('format') and request.args.get('format')[0] == 'json':
            request.args[b'format'] = b'json'
            request.setHeader('Content-Type', 'text/json; charset=utf-8')
            return json.dumps(dict(data=list(task.values())))
        else:
            request.setHeader('Content-Type', 'text/html; charset=utf-8')
            template = self.loader.load("tasks.html")

        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render(**context)
        d.addCallback(cb)
        return server.NOT_DONE_YET