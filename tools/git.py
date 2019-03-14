#!/usr/bin/env python2

import os
import subprocess
import tempfile
import time
import json
from threading import Timer
import json
import sys

def get_builder_name(default="shuttle"):
    return os.environ.get("DEBFULLNAME", default)

def get_builder_email(default="shuttle@deepin.com"):
    return os.environ.get("DEBEMAIL", default)

def get_changelog_time():
    return time.strftime("%a, %d %b %Y %T %z", time.localtime())

class ShuttleGitException(Exception):
    """
    return defined ShuttleGitException
    """

class Dch():
    def __init__(self, debian_repo):
        self.debian_repo = debian_repo

    def mangle_changelog(self, cp, revision, contents):
        try:
            with open(os.path.join(self.debian_repo, 'debian', 'changelog.dch'), 'w') as cw:
                cw.write("%(Source)s (%(Version)s) %(Distribution)s; urgency=%(Urgency)s\n" % cp)
                cw.write("\n")
                cw.write("  ** Build revesion: %s **\n\n" % revision)

                if isinstance(contents, str):
                    cw.write("  * %s\n" % content)
                    cw.write("\n")
                if isinstance(contents, list):
                    cw.write("  * detail lastest %d commit logs below: \n" % (len(contents)))
                    for i in contents:
                        cw.write("   - %s\n" % i)
                    cw.write("\n")
                if isinstance(contents, dict):
                    for key in content:
                        cw.write("  [%s]\n" % key)
                        for value in contents.get(key):
                            cw.write("  * %s\n" % value)
                        cw.write("\n")
                    cw.write("\n")
                cw.write(" -- %s <%s>  %s\n" % (get_builder_name(), get_builder_email(), get_changelog_time()))
            os.rename(os.path.join(self.debian_repo, 'debian', 'changelog.dch'), 
                    os.path.join(self.debian_repo,  'debian', 'changelog'))
        except Exception as err:
            print(err)
            return False
        return True


class GitBuilder():
    def __init__(self, pkgname, reponame, config, cache_dir):
        '''Config is a dict, like as
        {
            "source": "https://cr.deepin.io/dde/dde-daemon#branch=master",
            "debian": "https://cr.deepin.io/dde/dde-daemon#branch=debian"
        }
        '''
        self.pkgname = pkgname
        self.reponame = reponame
        self.config  = config
        self._cache = cache_dir
    
    def get_author(self, revison):
        try:
            author = self.execute(['git', 'show', '-s', '--format="%aN <%aE>"', revision])
        except Exception as e:
            author = None
        return author

    def check_call(self, commands, cwd=None):
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call(commands, shell=True, cwd=cwd, stdout=devnull, stderr=devnull)

    def execute(self, commands, cwd=None, extended_output=False, timeout=30):
        if cwd is None:
            cwd = self.source_cache

        env = os.environ.copy()
        env["LC_MESSAGE"] = "C"

        proc = subprocess.Popen(commands, shell=True, env=env, cwd=cwd, 
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=None)
        kill_proc = lambda p: p.kill()
        timeout = 300
        timer = Timer(timeout, kill_proc, [proc])
        timer.start()
        while proc.poll() is None:
            time.sleep(0.1)
        timer.cancel()

        status = proc.returncode

        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        if stdout.endswith('\n'):
            stdout = stdout[:-1]
        if stderr.endswith('\n'):
            stderr = stderr[:-1]

        if status != 0:
            raise ShuttleGitException("Subprocess  \"%s\" Error: %d \n %s\n"  % (commands, status, stderr))

        if extended_output:
            return (status, stdout, stderr)
        else:
            return stdout

    def update_cache(self):
        """
        update or clone source and debian source
        """
        if os.path.exists(self.source_cache):
            self.execute('git fetch origin +refs/heads/*:refs/heads/* --prune --tags', 
                cwd=self.source_cache)
        else:
            self.execute('git clone --bare %s %s' % (self.source_url, self.pkgname), 
                cwd=self._cache)

        if os.path.exists(self.debian_cache):
            self.execute('git fetch origin +refs/heads/*:refs/heads/* --prune', 
                cwd=self.debian_cache)
        else:
            self.execute('git clone --bare %s %s' % (self.debian_url, self.pkgname), 
                cwd=os.path.join(self._cache, 'debian'))

    @staticmethod
    def parser_url(url):
        """
        parser the ref from url
        """
        if '#branch=' in url:
            url, ref = url.split("#branch=")
        elif '#commit=' in url: 
            url, ref = url.split("#commit=")
        elif '#tag=' in url:
            url, ref = url.split("#tag=")
        else:
            url = url
            ref = 'HEAD'
        return (url, ref)

    def initial(self):
        try:
            self.source = self.config['source']
            if self.config.get('debian'):
                self.debian = self.config['debian']
            else:
                self.debian = self.source
        except Exception as e:
            raise OSError("config error: %s not exists" % e)

        if not os.path.exists(self._cache):
            os.makedirs(self._cache)

        self.source_url, self.source_ref = self.parser_url(self.source)
        self.debian_url, self.debian_ref = self.parser_url(self.debian)
        self.source_cache = os.path.join(self._cache, self.pkgname)
        if self.source_url == self.debian_url:
            self.debian_cache = self.source_cache
        else:
            self.debian_cache = os.path.join(self._cache, 'debian', self.pkgname)

        self.update_cache()

    def get_release_version(self, command, ref, cwd):
        command = command % {'ref': ref}
        try:
            stdout = self.execute(command, cwd=cwd)
            if stdout == "":
                raise

        except Exception as e:
            ver = "0.0"
            rev = self.execute('git rev-list --count master', cwd=cwd)
            sha = self.execute(['git rev-parse --short master'], cwd=cwd)
            stdout = '%(ver)s+r%(rev)s+g%(sha)s' % {'ver': '0.0', 'rev':rev, 'sha': sha}

        return stdout

    def log(self, sha, maxline=1):
        logs = self.execute("git log --pretty='%%s' %s -%d" % (sha, maxline))
        result = []
        for log in logs.split('\n'):
            if log.startswith("'") and log.endswith("'"):
                log = log[1:-1]
            result.append(log)
        return result
    
    def _merge_debian(self, temp_dir):
        #TODO: fix debian cache
        if not os.path.exists(os.path.join(temp_dir, self.pkgname, 'debian')) or self.debian_url != self.source_url:
            _revision = self.execute('git rev-parse %s' % self.debian_ref, cwd=self.debian_cache)
            self.check_call("git archive --format=tar --prefix=debian/ %s | (cd %s && tar xvf -)" % 
                (_revision, temp_dir), cwd=self.debian_cache)

            _debian_dir = os.path.join(temp_dir, 'debian', 'debian')
            if not os.path.exists(_debian_dir):
                raise ShuttleGitException("the debian dir is not exist in debian source with %s" % _revision)

            self.check_call("rm -rf %s" % (os.path.join(temp_dir, self.pkgname, 'debian')))
            self.check_call("cp -r %s %s" % (_debian_dir, os.path.join(temp_dir, self.pkgname)))

    def _adjust_source(self, work_dir, kwargs):
        """
        {'action': xxx, 'revision': xxx, 'dist': xxx, 'urgency': xxx, 'version': xxxx }
        """
        if not os.path.exists(os.path.join(work_dir, 'debian', 'source')):
            os.makedirs(os.path.join(work_dir, 'debian', 'source'))

        dist = kwargs.get('dist', 'unrelease')
        urgency = kwargs.get('urgency', 'low')
        version = kwargs['version']
        revision = kwargs['revision']

        if kwargs.get('quilt', False):
            contents = ['Autobuild %s: %s' % (kwargs['action'], revision)]
            with open(os.path.join(work_dir, 'debian', 'source', 'format'), 'w') as fp:
                fp.write("3.0 (quilt)\n")
        else:
            contents = self.log(revision)
            with open(os.path.join(work_dir, 'debian', 'source', 'format'), 'w') as fp:
                fp.write("3.0 (native)\n")
        
        dch =  Dch(os.path.join(work_dir))
        cp = {'Source': self.pkgname, 'Version': version, 'Distribution': dist, 'Urgency': urgency }
        dch.mangle_changelog(cp=cp, revision=revision, contents=contents)

        with open(os.path.join(work_dir, 'debian', 'changelog.dch'), 'w') as cw:
            cp = {'Source': self.pkgname, 'Version': version, 'Distribution': dist, 'Urgency': urgency}
            cw.write("%(Source)s (%(Version)s) %(Distribution)s; urgency=%(Urgency)s\n" % cp)
            cw.write("\n")
            cw.write("  * %s\n" % contents)
            cw.write("\n")
            cw.write(" -- %s <%s>  %s\n" % (get_builder_name(), get_builder_email(), get_changelog_time()))
        
        os.rename(os.path.join(work_dir, 'debian', 'changelog.dch'), 
                    os.path.join(work_dir,  'debian', 'changelog'))

    def _archive(self, temp_dir, action, ref=None, reponame=None, version=None):
        if ref is None:
            ref = self.source_ref
        
        # we just get the commit hash and not the git rev-paser 
        revision = self.execute("git log %s | head -1 | sed s/'commit '//" % ref, cwd=self.source_cache)
    
        with open(os.devnull, 'w') as devnull:
            self.check_call("git archive --format=tar --prefix=%s/ %s | (cd %s && tar xvf -)" % 
                (self.pkgname, revision, temp_dir), cwd = self.source_cache)

        json_config = os.path.join(temp_dir, self.pkgname, '.release.json')

        if not os.path.exists(json_config):
            #TODO: fix default release json file found
            json_config = os.path.join("../config", "default.release.json")
        
        with open(json_config, "r") as fp:
            config = json.load(fp)
        
        command = config[action].get('pkgver')
        if version is not None:
            _pkgver = version
        else:
            _pkgver = self.get_release_version(ref=revision, command=command, cwd=self.source_cache)

        if config[action].get('quilt', False):
            #TODO: get pkgver with '-%d'
            command = "git archive --format=tar" 
            command += " --prefix=%(source)s-%(pkgver)s/ %(revision)s | xz > %(tempdir)s/%(source)s_%(pkgver)s.orig.tar.xz" % \
                {'source': self.pkgname, 'pkgver': _pkgver, 'tempdir': temp_dir, 'revision': revision}
            self.check_call(command, cwd=self.source_cache)

        self._merge_debian(temp_dir)
        # rename the source directory which dpkg-source need it
        orig_name = "%s-%s" % (self.pkgname, _pkgver)
        self.check_call("mv %s %s" % (self.pkgname, orig_name), cwd=temp_dir)

        work_dir = os.path.join(temp_dir, orig_name)
        if config[action].get('quilt', False) and 'stable' in self.reponame and 'community' in self.reponame:
            #TODO: fix pkgver with binnmu
            pkgver = _pkgver + '-1'+'+comsta'
        elif config[action].get('quilt', False) and 'community' in self.reponame:
            #TODO: fix pkgver with binnmu
            pkgver = _pkgver + '-1'
        elif config[action].get('quilt', False) and 'stable' in self.reponame:
            #TODO: fix pkgver with binnmu
            pkgver = _pkgver + '-1'+'+stable'
        else:
            pkgver = _pkgver

        kwargs = {
            "action": action,
            "revision": revision,
            "dist": config[action].get("dist", "unrelease"),
            "urgency": config[action].get("urgency", "low"),
            "version": pkgver,
            "build_args": config.get('build_args', []),
            "quilt": config[action].get('quilt', False)
        }

        self._adjust_source(work_dir, kwargs)
        self.execute('dpkg-source -b %s' % orig_name, cwd=temp_dir)
        files = []
        for d in os.listdir(temp_dir):
            if os.path.isfile(os.path.join(temp_dir, d)):
                files.append(d)

        return (temp_dir, files, kwargs)

    def archive(self, action, ref=None, version=None):
        self.initial()
        temp_prefix = os.path.join("/tmp", "git-archive-temp")
        if not os.path.exists(temp_prefix):
            os.makedirs(temp_prefix)
        
        temp_dir = tempfile.mkdtemp(dir=temp_prefix)
        try:
            _dir, _files, _kwargs = self._archive(temp_dir, action=action, ref=ref, version=version)
        except Exception as e:
            print(e)
            os.system("rm -rf %s" % temp_dir)
            sys.exit(1)

        result = {"path": _dir, "files": _files}
        result.update(_kwargs)
        return json.dumps(result)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkgname", required=True)
    parser.add_argument("--source", required=True, help="Set the source reference.")
    parser.add_argument("--debian", help="Set the debian reference.")
    parser.add_argument("--cachedir", default="/tmp/cache")
    parser.add_argument("--action", required=True, help="[release, commit, release-candidate] is support")
    parser.add_argument("--version", help="set the fake version.")
    parser.add_argument("--reponame", required=True)

    args = parser.parse_args()
    config = {
        "source": args.source,
        "debian": args.debian
    }

    g = GitBuilder(pkgname=args.pkgname, reponame=args.reponame, config=config, cache_dir=args.cachedir)
    result = g.archive(action=args.action, version=args.version)
    print(result)
