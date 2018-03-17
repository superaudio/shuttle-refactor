from ConfigParser import ConfigParser
from twisted.internet import reactor

cf = ConfigParser()
cf.read("shuttle-slave-example.conf")

from slave import BuildDSlave

slave = BuildDSlave(cf)

from debianpackage import DebianBuildManager

#deb = DebianBuildManager(slave, '12345')

#deb.initiate(files=["ttf-deepin-opensymbol_1.0~alpha-1.dsc"], extra_args={'arch': 'i386', 'overlay':'tmpfs','librarian':'http://10.0.0.238:8000/filecache', 'tarball':'726b37342e51059a31906bbbe7516309', 'dist':'unstable', 'archives': ['deb http://pools.corp.deepin.com/deepin unstable main contrib non-free']})

deb = DebianBuildManager(slave, '9999')
slave.startBuild(deb)

deb.initiate(files=["lightdm_1.19.4-5.dsc"], extra_args={'arch': 'amd64', 'overlay':'tmpfs','librarian':'http://10.0.0.238:8000/filecache', 'tarball':'726b37342e51059a31906bbbe7516309', 'dist':'unstable', 'archives': ['deb http://pools.corp.deepin.com/deepin unstable main contrib non-free']})

reactor.run()
