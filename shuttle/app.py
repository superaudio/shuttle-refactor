from twisted.web import resource, server
from twisted.internet import defer, reactor
from twisted.web.static import File
from twisted.internet.task import LoopingCall

import sqlobject
from config import config

from api import ApiResource
from views import ViewsResource

from models import Job, JobStatus, Package
from slaves import ShuttleBuilders

class RootResource(ViewsResource):
    def __init__(self):
        ViewsResource.__init__(self)
        self.putChild("api", ApiResource())
        self.putChild("static", File('static'))

if __name__ == "__main__":
    import signal
    def handle_sigterm(signum, stack):
        print("Interrupted!. Exiting.")
        builders.do_quit.set()
        for slave in ShuttleBuilders().slaves:
            slave.inactive()
        reactor.stop()

    sqlconnection = sqlobject.connectionForURI(config['runtime'].get('database_uri'))
    sqlobject.sqlhub.processConnection = sqlconnection
    Package.createTable(ifNotExists=True)
    Job.createTable(ifNotExists=True)
    site = server.Site(RootResource())
    builders = ShuttleBuilders()
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    loop_builders = LoopingCall(builders.loop)
    loop_builders.start(10)
    
    reactor.listenTCP(config['runtime']['port'], site)
    reactor.run()
