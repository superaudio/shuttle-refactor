from twisted.web import resource
from twisted.web import server
from template import Jinja2TemplateLoader

import json

class DashboardView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')

    def render_GET(self, request):
        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        template = self.loader.load("dashboard.html")

        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render()
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