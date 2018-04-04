#!/usr/bin/env python

import os
import shutil
import sys
import uuid
import fcntl
import subprocess
import argparse
import json
import datetime
import glob

distribution_snippet = """Origin: Deepin
Label: %(uuid)s
Codename: %(dist)s
Suite: %(dist)s
Architectures: %(arches)s
Components: main
"""

class LockContext:
    def __init__(self, lockfilename):
        self.lockfilename = lockfilename

    def __enter__(self):
        self.lfp = open(self.lockfilename, 'w')
        try:
            fcntl.lockf(self.lfp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError as err:
            raise IOError("Could lock file %s: %s" % (self.lockfilename, err))

        return self

    def __exit__(self, exception_type, exception_val, trace):
        self.lfp.close()
        return False

class RepositoryException(Exception):
    """
    add RepositoryException
    """

class Repository():
    def __init__(self, repo_path, name):
        self.repo_path = repo_path
        self.name = name
        _name = name.split('/')[0]
        config = os.path.join(repo_path, _name, "%s.json" % _name)

        if not os.path.exists(config):
            raise Repository("Repository config file: %s has not exists, Please create it first." % config)
        
        self.config = json.load(open(config, "r"))
            
    def _reprepro(self, basepath, args):
        _lock = os.path.join(basepath, 'conf', '.repository.lock')
        with LockContext(_lock):
            p = subprocess.Popen('reprepro -Vb. '+ args, shell=True, stdin=None, 
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=basepath)
            stdout = p.communicate()[0]
            return (p.returncode, stdout)
        
    def _create(self, basepath, dist, arches):
        if not os.path.exists(os.path.join(basepath, "conf")):
            os.makedirs(os.path.join(basepath, "conf"))
        config = os.path.join(basepath, "conf/distributions")
        result = distribution_snippet % { "dist": dist, "arches": " ".join(arches), 
                "uuid": uuid.uuid1()}
        
        with open(config, 'w') as fp:
            fp.write(result)      

        self._reprepro(basepath=basepath, args="export")

    def create(self):
        for key in self.config:
            basepath = os.path.join(self.repo_path, self.name, key)
            if not self.config[key].get('division'):
                dist   = self.config[key].get('dist')
                arches = self.config[key].get('arches')
                self._create(basepath=basepath, dist=dist, arches=arches)
            else:
                if not os.path.exists(basepath):
                    os.makedirs(basepath)
    
    def division(self, base, name):
        if not base in self.config:
            raise RepositoryException("%s is not exists" % base)
        if not self.config[base].get('division'):
            raise RepositoryException("%s is not support division" % base)
        
        basepath = os.path.join(self.repo_path, self.name, base, name)
        if os.path.exists(basepath):
            raise RepositoryException("%s/%s is created." % (base, name))

        dist   = self.config[base].get('dist')
        arches = self.config[base].get('arches')
        self._create(basepath=basepath, dist=dist, arches=arches)
    
    def destroy(self, base):
        repo_path = os.path.join(self.repo_path, self.name, base)
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
    
    def remove_packages(self, base, sources):
        args = "removesrc %s %s" % (self.dist, " ".join(sources))
        basepath = os.path.join(self.repo_path, self.name, base)
        return self._reprepro(basepath=basepath, args=args)

    def include_packages(self, cache_dir, base, skip_source=False):
        action = base.split('/')[0]
        if not os.path.exists(cache_dir):
            raise RepositoryException("cache %s is not exists, failed to include packages" % cache_dir)

        logfile = os.path.join(cache_dir, "uploadlog")
        if os.path.exists(logfile):
            os.remove(logfile)
        
        config = self.config.get(action)
        dist = self.config[action]['dist']
        arches = self.config[action]['arches']

        if config.get('division'):
            reponame = self.name.split('/')[0]
            division = self.name.split('/')[1]
            basepath = os.path.join(self.repo_path, reponame, base, division)
        else:
            basepath = os.path.join(self.repo_path, self.name, base)

        with open(logfile, "w") as log:
            log.write("Start at %s\n" % datetime.datetime.now().strftime("%A %d. %B %Y"))
            arches = self.config[action].get('arches')
            if 'source' in arches and not skip_source:
                source_dir = os.path.join(cache_dir, "source")
                dsc_files = glob.glob(os.path.join(source_dir, "*.dsc"))
                for dsc_file in dsc_files:
                    args = "includedsc %(dist)s %(dsc)s" % \
                    {
                        "dist": dist,
                        "dsc": os.path.join(source_dir, "*.dsc")
                    }

                    _, stdout = self._reprepro(basepath=basepath, args=args)
                    log.write(stdout.decode())

            if os.path.exists(os.path.join(cache_dir, "%s-%s" % (dist, arches[0]))):
                all_debs = os.path.join(cache_dir, "%s-%s" % (dist, arches[0]), "*all.deb")
                if len(glob.glob(all_debs)) > 0:
                    args = "includedeb %(dist)s %(deb)s" % \
                        {
                            "dist": dist,
                            "deb": all_debs
                        }
                    _, stdout = self._reprepro(basepath=basepath, args=args)
                    log.write(stdout.decode())
                
            for arch in arches:
                arch_debs = os.path.join(cache_dir, "%s-%s" % (dist, arch), "*" + arch + ".deb")
                if len(glob.glob(arch_debs)) > 0:
                    args = "includedeb %(dist)s %(deb)s" % \
                        {
                            "dist": dist,
                            "deb": arch_debs
                        }
                    _, stdout = self._reprepro(basepath=basepath, args=args)
                    log.write(stdout.decode())

            log.write("Finished at %s\n" % datetime.datetime.now().strftime("%A %d. %B %Y"))


class FakeRepository():
    def __init__(self):
        """
        repo_path, base, name
        """
        repo_path = os.environ.get('REPOPATH')
        name = os.environ.get('NAME')

        if repo_path is None or name is None:
            print("<REPOPATH> <NAME> <CONFIG> should exists")
            sys.exit(1)

        parser = argparse.ArgumentParser(
            description = 'Pretends to be repository',
            usage='''%(prog)s <command> [<args>]'''
            )

        parser.add_argument('command', help='Subcommand to run')
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            sys.exit(1)
        
        self.repo = Repository(repo_path, name)
        
        getattr(self, args.command)()
    
    def division(self):
        parser = argparse.ArgumentParser(
            description='create the repository'
            )
        parser.add_argument('--base', required=True)
        parser.add_argument('--division', required=True)

        args = parser.parse_args(sys.argv[2:])
        try:
            self.repo.division(base=args.base, name=args.division)
        except RepositoryException as e:
            print("Error: %s" % e)
            sys.exit(1)
    
    def create(self):
        parser = argparse.ArgumentParser(
            description='create the repository'
            )
        args = parser.parse_args(sys.argv[2:])
        try:
            self.repo.create()
        except Exception as e:
            print("Error: create error - %s" % e)
    
    def include(self):
        parser = argparse.ArgumentParser(
            description='include packages to the repository'
            )
        parser.add_argument('--cache', required=True)
        parser.add_argument('--base', required=True)
        parser.add_argument('--skip-source', action="store_true")
        args = parser.parse_args(sys.argv[2:])
        self.repo.include_packages(cache_dir=args.cache, base=args.base, skip_source=args.skip_source)


if __name__ == "__main__":
    FakeRepository()
