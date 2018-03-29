from config import config

import json
import os
import subprocess

def list_repo():
    result = {}
    repo_base = config['cache']['repos']
    if not os.path.exists(repo_base):
        return {}
    for dir_name in os.listdir(repo_base):
        json_file = os.path.join(repo_base, dir_name, '%s.json' % dir_name )
        if os.path.exists(json_file):
            content = json.loads(file(json_file).read())
            for key in content:
                content[key]['sources'] = 'deb %(repo_url)s/%(repo_name)s/%(action)s %(dist)s main' % {
                    'repo_url': config['runtime']['repo_url'],
                    'repo_name': dir_name,
                    'action': key,
                    'dist': content[key]['dist']
                    }
            result[dir_name] = content
    return result


def getstatusoutput(commands, cwd=None, env=None):
    p = subprocess.Popen(commands, shell=True, stdin=None, 
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
        cwd=cwd, env=env)
    stdout = p.communicate()[0]
    if stdout.endswith('\n'):
        stdout = stdout[:-1]
    return (p.returncode, stdout)