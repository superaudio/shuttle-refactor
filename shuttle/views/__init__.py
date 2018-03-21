from twisted.web import resource, server

import dashboard


class ViewsResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild("dashboard", dashboard.DashboardView())
        self.putChild("monitor", dashboard.MonitorView())
    
    def getChild(self, name, request):
        return resource.Resource.getChild(self, name, request)