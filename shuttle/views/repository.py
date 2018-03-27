from twisted.web import resource
from twisted.web import server
from template import Jinja2TemplateLoader

import json
import functions

class RepoView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')

    def render_GET(self, request):
        context = {"repos": functions.list_repo()}
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
        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        template = self.loader.load("tasks.html")

        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render()
        d.addCallback(cb)
        return server.NOT_DONE_YET