from twisted.web import resource, server
from twisted.internet import defer, reactor
import sqlobject
from config import config

from api import ApiResource
from models import Job, JobStatus, Package

class RootResource(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild("api", ApiResource())

if __name__ == "__main__":
    sqlconnection = sqlobject.connectionForURI(config['runtime'].get('database_uri'))
    sqlobject.sqlhub.processConnection = sqlconnection
    Package.createTable(ifNotExists=True)
    Job.createTable(ifNotExists=True)
    site = server.Site(RootResource())
    reactor.listenTCP(5000, site)
    reactor.run()
