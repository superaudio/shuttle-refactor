from twisted.web import resource, server

import dashboard
import tasks
import repository

from template import Jinja2TemplateLoader

class ViewsResource(resource.Resource):
    
    loader = Jinja2TemplateLoader('templates')
    
    def __init__(self):
        resource.Resource.__init__(self)
        
        self.putChild("dashboard", dashboard.DashboardView())
        self.putChild("monitor", dashboard.MonitorView())
        self.putChild("task", tasks.TaskView())
        self.putChild("tasks", tasks.TasksView())
        self.putChild("repository", repository.RepoView())

    def getChild(self, name, request):
        instance = resource.Resource.getChild(self, name, request)
        if isinstance(instance, resource.NoResource):
            error = {'status_code': 404, 'message': 'No such resource'}
            return ErrorResource(error)
            
        return instance

class ErrorResource(resource.Resource):
    
    isLeaf = True
    loader = Jinja2TemplateLoader('templates')

    def __init__(self, error):
        resource.Resource.__init__(self)
        self.error = error

    def render_GET(self, request):
        
        template = self.loader.load("error.html")
        
        def cb(content):
            request.write(content)
            request.setResponseCode(self.error.get('status_code'))
            request.finish()

        d = template.render(**self.error)
        d.addCallback(cb)
        return server.NOT_DONE_YET