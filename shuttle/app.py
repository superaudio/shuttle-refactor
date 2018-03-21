from twisted.web import resource, server
from twisted.internet import defer, reactor
from twisted.web.static import File

import sqlobject
from config import config

from api import ApiResource
from views import ViewsResource

from models import Job, JobStatus, Package

class RootResource(ViewsResource):
    def __init__(self):
        ViewsResource.__init__(self)
        self.putChild("api", ApiResource())
        self.putChild("static", File('static'))

if __name__ == "__main__":
    sqlconnection = sqlobject.connectionForURI(config['runtime'].get('database_uri'))
    sqlobject.sqlhub.processConnection = sqlconnection
    Package.createTable(ifNotExists=True)
    Job.createTable(ifNotExists=True)
    site = server.Site(RootResource())
    reactor.listenTCP(config['runtime']['port'], site)
    reactor.run()
