__metaclass__ = type

import os
import re
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

        self.sources_list = extra_args.get("archives")
        self.dscfile = None

        for f in files:
            if f.endswith(".dsc"):
                self.dscfile = f

        self.overlay = extra_args.get("overlay", "tmpfs")
        self.tarball = extra_args.get("basetgz")
        self.librarian = extra_args.get("librarian")

        source_id = extra_args.get("source_id")

        if extra_args.get('binnmu', 'no') == 'yes':
            self.binnmu = True
            self.binnmu_version = int(extra_args.get("binnmu_version", 0))
            self.binnmu_message = extra_args.get("binnmu-message", "Auto build with shuttle.")
        else:
            self.binnmu = False

        self.add_suffix = extra_args.get('add_suffix', None)
        self.builder_args = extra_args.get('builder_args', None)

        if self.tarball is None or self.librarian is None or self.dscfile is None:
            self.alreadyfailed = True
            self._slave.buildFail("Arguments error ...")
            self._slave.buildComplete()
        else:
            command = os.path.join(self._binpath, 'get-sources')
            env = os.environ.copy()
            dscfile = self.dscfile
            if self.add_suffix is not None:
                env['ADD_SUFFIX'] = self.dist
                self.dscfile = dscfile.replace(".dsc", "~%s.dsc" % self.dist)

            self.runSubProcess(command=command, args=['get-sources', self.buildid, self.librarian, self.tarball, source_id, dscfile], env=env) 

    @staticmethod
    def _parseChangesFile(linesIter):
        seenfiles = False
        for line in linesIter:
            if line.endswith("\n"):
                line = line[:-1]
            if not seenfiles and line.startswith("Files:"):
                seenfiles = True
            elif seenfiles:
                if not line.startswith(' '):
                    break
                filename = line.split(' ')[-1]
                yield filename

    def getChangesFilename(self):
        if self.binnmu is False:
            changes = self.dscfile[:-4] + "_" + self.arch + ".changes"
        else:
            changes = self.dscfile[:-4] + "+b%d" % self.binnmu_version + "_" + self.arch + ".changes"
        return changes

    def gatherResult(self):
        path = self.getChangesFilename()
        if not os.path.exists(os.path.join(self._cachepath, path)):
            extra_info="Gather result Failed: %s is not exists" % path
            self.alreadyfailed = True
            self._slave.buildFail(extra_info)
            return
        self._slave.addWaitingFile(path)
        chfile = open(os.path.join(self._cachepath, path), "r")
        try:
            for fn in self._parseChangesFile(chfile):
                if fn.endswith(".deb") or fn.endswith(".udeb"):
                    self._slave.addWaitingFile(fn)
        finally:
            chfile.close()

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
        self.runSubProcess(command=command, args=['prepare-chroot', self.buildid, self.overlay])

    def doUpdate(self):
        command = os.path.join(self._binpath, 'override-sources-list')
	args = ['override-sources-list', self.buildid]
	args.extend(self.sources_list)
        self.runSubProcess(command=command, args=args)

    def doBuild(self):
        args=['build-package', self.buildid, '--buildresult', self._cachepath]

        if self.builder_args is not None:
            if self.builder_args.get("use_network", "0") == "1":
                args.append("--use-network")
                args.append("yes")

        if self.binnmu is True:
            args.extend(['--debbuildopts', '-B', '--bin-nmu', self.binnmu_message, '--bin-nmu-version', str(self.binnmu_version)])

        args.append(self.dscfile)

        os.environ["DIST"] = self.dist
        os.environ["ARCH"] = self.arch

        command = os.path.join(self._binpath, 'build-package')
        self.runSubProcess(command=command, args=args, env=dict(os.environ))

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
            self._state = DebianBuildState.UPDATE
            self.doUpdate()

    def iterate_UPDATE(self, success):
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
