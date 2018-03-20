#!/usr/bin/env python

import os
import json
import subprocess

def load_config():
    SHUTTLE_CONFIG = os.environ.get("SHUTTLE_CONFIG", 
        "../config/shuttle.json")
    with open(SHUTTLE_CONFIG) as fp:
        config = json.loads(fp.read())
    
    return config

config = load_config()

def getstatusoutput(commands, cwd=None, env=None):
    p = subprocess.Popen(commands, shell=True, stdin=None, 
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
        cwd=cwd, env=env)
    stdout = p.communicate()[0]
    if stdout.endswith('\n'):
        stdout = stdout[:-1]
    return (p.returncode, stdout)