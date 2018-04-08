#!/usr/bin/env python
"""
curl https://cr.deepin.io/changes/33121/revisions/2/patch | base64 -d

diff --git a/project_list.json b/project_list.json
index 91fdfed..931b2b3 100644
--- a/project_list.json
+++ b/project_list.json
@@ -4,8 +4,8 @@
         "tag": "1.0.2"
     },
     "dbus-factory": {
-        "commit": "65fc1b45ba62ab1d5421278043e267913c70083a",
-        "tag": "3.1.13"
+        "commit": "544ee85a9496f7658b07e45f93635b0e03f5af98",
+        "tag": "3.1.11"
     },
     "dde-api": {
         "commit": "ad475df9879f4c9af6bcefcb1265d574296f6a13",
@@ -20,8 +20,8 @@
         "tag": "4.3.7"
     },
     "dde-daemon": {
-        "commit": "8cdb2014ed10813ab35345ce23f88b59e2ed259a",
-        "tag": "3.2.8"
+        "commit": "e9d755dac5ce28f91d9a9bae8cb9255b76964a71",
+        "tag": "3.2.8.1"
     },
     "dde-dock": {
         "commit": "570230afaf939c8e715d19cc34be63ef6bec38a9",
@@ -228,8 +228,8 @@
         "tag": "0.1.7"
     },
     "dtkwidget": {
-        "commit": "03999114f5906e2e6aa7c15506a4909f3a4a585d",
-        "tag": "2.0.7.1"
+        "commit": "dfdc35a9d6eee970031cca69b38393e73472a7c2",
+        "tag": "2.0.7.2"
     },
"""
import re
import subprocess
from copy import deepcopy

def parser_block(patch_block):
    remove = 0
    added = 0
    for line in patch_block:
        if line.startswith('-'):
            remove += 1
        if line.startswith('+'):
            added  += 1

    if remove != added:
        result = _parser_method_one(patch_block)
    else:
        result = _parser_method_two(patch_block)
    
    return result

def _parser_method_one(patch_block):
    result = {}
    for linenum, line in enumerate(patch_block):
        if line.startswith('-') or line.startswith('+'):
            if '{' in line:
                packagename = re.search('\"(.*?)\"', line).group(1)
                result[packagename] = {'orig': {}, 'dest': {}}
            elif '}' in line:
                packagename = None
            else:
                group = re.findall('\"(.*?)\"', line)
                if len(group) == 2:
                    if line.startswith('-'):
                        result[packagename]['orig'].update({group[0]: group[1]})
                    elif line.startswith('+'):
                        result[packagename]['dest'].update({group[0]: group[1]})
    return result

def _parser_method_two(patch_block):
    result = {}
    marked = 0
    for linenum, line in enumerate(patch_block):
        if line.startswith('-') or line.startswith('+'):
            if marked == 0:
                unchanged = {}
                while not '{' in patch_block[linenum - 1]:
                    linenum -= 1
                    group = re.findall('\"(.*?)\"', patch_block[linenum])
                    if len(group) == 2:
                        unchanged.update({group[0]: group[1]})
                    if linenum == 0:
                        raise OSError('patch set has some problem')

                _line = patch_block[linenum - 1]
                packagename = re.search('\"(.*?)\"', _line).group(1)
                result[packagename] = {'orig': deepcopy(unchanged), 'dest': deepcopy(unchanged)}

            group = re.findall('\"(.*?)\"', line)
            if len(group) == 2:
                if line.startswith('-'):
                    marked -= 1
                    result[packagename]['orig'].update({group[0]: group[1]})
                elif line.startswith('+'):
                    marked += 1
                    result[packagename]['dest'].update({group[0]: group[1]})
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cr', default='https://cr.deepin.io/changes')
    parser.add_argument('--changeid', required=True, type=int)
    parser.add_argument('--patchset', default=1,type=int)
    parser.add_argument('--parserjson', default='project_list.json')

    args = parser.parse_args()
    urlpath = '%(cr)s/%(changeid)d/revisions/%(patchset)s/patch' % {
        "cr": args.cr, "changeid": args.changeid, "patchset": args.patchset
    }

    status, output = subprocess.getstatusoutput('curl %s | base64 -d' % urlpath)
    if status != 0:
        raise subprocess.CalledProcessError('get output error')

    start = False
    lines = []
    for line in output.split('\n'):
        if line.startswith('+++ b/%s' % args.parserjson):
            start = True
            continue
        if start:
            if line.startswith('diff --git'):
                start = False

        if start:
            lines.append(line)  

    blocks = []
    block_lines = []
    for line in lines:
        if line.startswith('@@'):
            if len(block_lines) > 0:
                blocks.append(block_lines)
            block_lines = []
            continue
        block_lines.append(line)
    if len(block_lines) > 0:
        blocks.append(block_lines)

    for block in blocks:
        print(parser_block(block))