#!/usr/bin/env python
from ConfigParser import ConfigParser
import os

from twisted.application import service, strports
from twisted.web import resource, server, static

from debianpackage import DebianBuildManager
from slave import XMLRPCBuildDSlave

conffile = os.environ.get("SHUTTLE_SLAVE_CONFIG", "shuttle-slave-example.conf")

conf = ConfigParser()
conf.read(conffile)
slave = XMLRPCBuildDSlave(conf)

slave.registerBuilder(DebianBuildManager, "debian")

application = service.Application("BuildSlave")
builddslaveService = service.IServiceCollection(application)

root = resource.Resource()
root.putChild("rpc", slave)
root.putChild("filecache", static.File(conf.get('slave', 'filecache')))

is_twistd = False
if is_twistd:
    slavesite = server.Site(root)
    strports.service(slave.slave._config.get("slave", "bindport"), slavesite).setServiceParent(builddslaveService)
else:
    from twisted.internet import reactor
    from twisted.web.server import Site
    factory = Site(root)
    reactor.listenTCP(slave.slave._config.getint("slave", "bindport"), factory)
    reactor.run()
