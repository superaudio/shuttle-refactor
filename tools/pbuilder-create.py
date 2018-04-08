#!/usr/bin/env python
# Create pbuilder build environment

import json
import subprocess
import uuid
import os
import shutil
import sys
import hashlib
from datetime import datetime

class PBuilder():
    def  __init__(self, json_file, dist, arch, cachepath):
        self._json  =  json_file
        self.config  =  json.load(open(self._json, "r"))
        self.config.update({'arch': arch, 'dist': dist})
        self.basetgz = os.path.join(cachepath, "base.tgz")

    def save(self): 
        if not os.path.exists(self.basetgz):
            return False
        f = open(self.basetgz)
        try:
            md5 = hashlib.md5()
            for chunk in iter(lambda: f.read(256*1024), ''):
                md5.update(chunk)
            md5sum = md5.hexdigest()
        finally:
            f.close()
        
        self.config['build'] = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.config['md5sum'] = md5sum
        with open(os.path.join(cachepath, "result.json"), "w") as fp:
            fp.write(json.dumps(self.config, indent=4))


    def create(self):
        cmd = "pbuilder --create --debootstrapopts --no-check-gpg "
        cmd += "--mirror %(mirror)s --distribution %(dist)s --architecture %(arch)s --allow-untrusted " % self.config
        cmd += "--basetgz %s " % (self.basetgz)
        if self.config.get('components'):
            cmd += "--components \"%s\" " % (" ".join(self.config['components']))

        if self.config.get('extra_packages'):
            cmd += "--extrapackages \"%s\" " % ("  ".join(self.config['extra_packages']))

        if self.config.get('other_mirrors'):
            cmd += "--othermirror \"%s\" " % (" | ".join(self.config['other_mirrors']))

        state = None
        print(cmd)

        try:
            proc = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdin=None)
        except Exception as err:
            state = 1

        while state == None:
            state = proc.poll()
        
        if state == 0:
            return True
        else:
            return False

    def _reload(self):
        self.config  =  json.load(open(self._json, "r"))

    def dump(self):
        _contents = """
        Dist:     %(dist)s
        Arch:     %(arch)s
        Hash:     %(md5sum)s
        """ % self.config
        return _contents


if  __name__  == "__main__":
    import argparse
    parser = argparse.ArgumentParser
    parser.add_argument('--json', required=True)
    parser.add_argument('--dist', default='unstable')
    parser.add_argument('--arch', default='amd64')
    parser.add_argument('--cache', required=True)

    args = parser.parse_args()

    p = PBuilder(json_file=args.json, arch=args.arch, dist=args.dist, cachepath=args.cache)
    if p.create() is True:
        p.save()
    else:
        sys.exit(1)