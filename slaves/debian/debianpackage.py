__metaclass__ = type

import os
import re
import json
import signal
from functools import partial

from twisted.python import log
from slave import BuildManager

class BuildExitCodes:
    OK           =  0
    FAILED       =  1
    ATTEMPTED    =  2
    GIVENBACK    =  3
    BUILDERFAIL  =  4

class DpkgArchitectureCache:
    def __init__(self):
        self._matches = {}

    def match(self, arch, wildcard):
        if (arch,  wildcard) not in self._matches:
            command = ['dpkg-architecture', '-i%s' % wildcard]
            env = dict(os.environ)
            env["DEB_HOST_ARCH"] = arch
            ret = (subprocess.call(command, env=env) == 0)
            self._matches[(arch, wildcard)] = ret
        return self._matches[(arch, wildcard)]

class DebianBuildState:
    INIT      = "INIT"
    PREPARE   = "PREPARE"
    PREBUILD  = "PREBUILD"
    UPDATE    = "UPDATE"
    BUILD     = "BUILD"
    POSTBUILD = "POSTBUILD"
    CLEANUP   = "CLEANUP"

class DebianBuildManager(BuildManager):

    extra_info = "debian build with pbuilder"

    def __init__(self, slave, buildid, **kwargs):
        BuildManager.__init__(self, slave, buildid, **kwargs)
        self.buildid = str(buildid)

        self._cachepath = slave._cachepath
        self._binpath = slave._binpath

        self._state = DebianBuildState.INIT
        self._reaped_states = set()
        self.abort_timeout = 3600
        slave.emptylog()

        self.alreadyfailed = False

    def initiate(self, files, extra_args):

        self.dist = extra_args.get("dist")
        self.arch = extra_args.get("arch")
        if self.dist not in self._slave.getDists() or self.arch not in self._slave.getArches():
            raise ValueError("%s-%s is not support by this slave" % (self.dist, self.arch))
        with open(os.path.join(self._cachepath, 'extra_args.json'), 'w') as fp:
            extra_args.update({'files': files})
            fp.write(json.dumps(extra_args, indent=4))
        
        command = os.path.join(self._binpath, 'get-sources')
        env = os.environ.copy()
        self.runSubProcess(command=command, args=['get-sources', self.buildid], env=env)

    def gatherResult(self):
        for fn in os.listdir(self._cachepath):
            if fn != 'buildlog' and os.path.isfile(os.path.join(self._cachepath, fn)):
                self._slave.addWaitingFile(fn)

    def iterate(self, success):
        if self.alreadyfailed and success == 0:
            success = 128 + signal.SIGKILL

        log.msg("Iterating with success flag %s against stage %s" % (success, self._state))
        func = getattr(self, "iterate_" + self._state, None)
        if func is None:
            raise ValueError("Unknow internal state " + self._state)
        func(success)
        
    def doPreBuild(self):
        command = os.path.join(self._binpath, 'prepare-chroot')
        self.runSubProcess(command=command, args=['prepare-chroot', self.buildid])

    def doBuild(self):
        os.environ["DIST"] = self.dist
        os.environ["ARCH"] = self.arch
        command = os.path.join(self._binpath, 'build-package')
        self.runSubProcess(command=command, args=['build-package', self.buildid], env=dict(os.environ))

    def doPostBuild(self):
        command = os.path.join(self._binpath, 'scan-processes')
        self.runSubProcess(command=command, args=['scan-processes', self.buildid])

    def doCleanup(self):
        command = os.path.join(self._binpath, 'remove-chroot')
        self.runSubProcess(command=command, args=['remove-chroot', self.buildid])
        self._slave.log("clean up build environment")

    def abortReap(self):
        self._slave.log("Reap build from %s.\n" % self._state)
        self._state = DebianBuildState.POSTBUILD
        command = os.path.join(self._binpath, 'scan-processes')
        self.runSubProcess(command=command, args=['scan-processes', self.buildid])

    def iterate_INIT(self, success):
        if success != 0:
            if not self.alreadyfailed:
                self.alreadyfailed = True
                self._slave.buildFail()
            self._state = DebianBuildState.CLEANUP
            self.doCleanup()
        else:
            self._state = DebianBuildState.PREBUILD
            self.doPreBuild()

    def iterate_PREBUILD(self, success):
        if success != 0:
            if not self.alreadyfailed:
                self.alreadyfailed = True
                self._slave.buildFail()
            self._state = DebianBuildState.CLEANUP
            self.doCleanup()
        else:
            self._state = DebianBuildState.BUILD
            self.doBuild()

    def iterate_BUILD(self, success):
        if success != 0:
            if not self.alreadyfailed:
                self.alreadyfailed = True
                self._slave.buildFail()
            self._state = DebianBuildState.CLEANUP
            self.doCleanup()
        else:
            self.gatherResult()
            self._state = DebianBuildState.POSTBUILD
            self.doPostBuild()

    def iterate_POSTBUILD(self, success):
        if success != 0:
            if not self.alreadyfailed:
                self.alreadyfailed = True
                self._slave.buildFail()
            self._state = DebianBuildState.CLEANUP
        self._state = DebianBuildState.CLEANUP
        self.doCleanup()

    def iterate_CLEANUP(self, success):
        if success != 0:
            if not self.alreadyfailed:
                self.alreadyfailed = True
                self._slave.buildFail()
            self._state = DebianBuildState.CLEANUP
        else:
            if not self.alreadyfailed:
                self._slave.buildOK()

        self._slave.buildComplete()
