from twisted.web import resource
import workers
import task
import repo
import job

class ApiResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild("workers", workers.Workers())
        self.putChild("task", task.Task())
        self.putChild("repo", repo.Repo())
        self.putChild("job", job.JobResource())
    
    def getChild(self, name, request):
        return resource.Resource.getChild(self, name, request)