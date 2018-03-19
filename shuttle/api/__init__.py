from twisted.web import resource
import workers
import task

class ApiResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild("workers", workers.ListWorkers())
        self.putChild("task", task.Task())
    
    def getChild(self, name, request):
        return resource.Resource.getChild(self, name, request)