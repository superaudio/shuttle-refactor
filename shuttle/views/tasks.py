from twisted.web import resource
from twisted.web import server
from template import Jinja2TemplateLoader
from models import Job 

import json

class JobView(resource.Resource):
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')

    def render_GET(self, request):
        id = request.path.split('/')[-1]
        #FIXME: should render by client
        job = Job.selectBy(id=id)[0]
        result = job.dict()
        result.update(job.package.dict())
        context = {'jobid': id, 'job': result}
        request.setHeader('Content-Type', 'text/html; charset=utf-8')
        template = self.loader.load("job.html")

        def cb(content):
            request.write(content)
            request.setResponseCode(200)
            request.finish()

        d = template.render(**context)
        d.addCallback(cb)
        return server.NOT_DONE_YET

class TasksView(resource.Resource):
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