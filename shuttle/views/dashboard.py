from twisted.web import resource
from twisted.web import server
from template import Jinja2TemplateLoader

import json

class DashboardView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')
    htmls = ['html', '']
    def set_defaults(self, request, html=False):
        request.setHeader('Access-Control-Allow-Origin', '*')
        if html:
            request.setHeader('Content-Type', 'text/html; charset=utf-8')
        elif b'format' in request.args and request.args[b'format'][
                0] == b'json':
            request.args[b'format'] = b'json'
            request.setHeader('Content-Type', 'text/json; charset=utf-8')
        else:
            request.setHeader('Content-Type', 'text/html; charset=utf-8')
    
    def render_GET(self, request):
        workers = {
            "dummy-01@localhost": {'hostname': 'dummy-01@localhost', 'status': 1, 'loadavg': ['1,3,4']},
            "dummy-02@localhost": {'hostname': 'dummy-02@localhost', 'status': 0, 'loadavg': ['2']}
        }

        context = {'workers': workers}
        if request.args.get('format') and request.args.get('format')[0] == 'json':
            request.args[b'format'] = b'json'
            request.setHeader('Content-Type', 'text/json; charset=utf-8')
            return json.dumps(dict(data=list(workers.values())))
        else:
            request.setHeader('Content-Type', 'text/html; charset=utf-8')
            template = self.loader.load("dashboard.html")

        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render(**context)
        d.addCallback(cb)
        return server.NOT_DONE_YET

class MonitorView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')
    
    def render_GET(self, request):
        template = self.loader.load("monitor.html")
        workers = {
            "dummy-01@localhost": {},
            "dummy-02@localhost": {}
        }
        context = {"workers": workers}
        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render(**context)
        d.addCallback(cb)
        return server.NOT_DONE_YET