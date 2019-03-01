from twisted.web import resource, server
from twisted.internet import defer, reactor
from twisted.web.static import File

import sqlobject
from config import config

from api import ApiResource
from views import ViewsResource

from models import Job, JobStatus, Package, Log
from slaves import ShuttleBuilders

class CacheResource(resource.Resource):
    isLeaf = False
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild("repos", File(config['cache']['repos']))
        self.putChild("tasks", File(config['cache']['tasks']))

    def getChild(self, name, request):
        if name == '':
            return self
        return resource.Resource.getChild(self, name, request)

    def render_GET(self, request):
        return "<html>Hello, world!</html>"

class RootResource(ViewsResource):
    def __init__(self):
        ViewsResource.__init__(self)
        self.putChild("api", ApiResource())
        self.putChild("static", File('static'))
        self.putChild("cache", CacheResource())

if __name__ == "__main__":
    import signal
    from twisted.python import log
    import sys

    log.startLogging(sys.stdout)

    def handle_sigterm(signum, stack):
        print("Interrupted!. Exiting.")
        builders.do_quit.set()
        builders.cache_slaves()
        for slave in ShuttleBuilders().slaves:
            slave.inactive()
        reactor.stop()

    sqlconnection = sqlobject.connectionForURI(config['runtime'].get('database_uri'))
    sqlobject.sqlhub.processConnection = sqlconnection
    Package.createTable(ifNotExists=True)
    Job.createTable(ifNotExists=True)
    Log.createTable(ifNotExists=True)
    site = server.Site(RootResource())
    builders = ShuttleBuilders()
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    builders.loop()
    
    reactor.listenTCP(config['runtime']['port'], site)
    reactor.run()
