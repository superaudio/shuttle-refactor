# apply tasks
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"commit","pkgname":"dde-session-ui","reponame":"dde", "source":"https://cr.deepin.io/dde/dde-session-ui#branch=master", "build_args":["use_network"]}' http://127.0.0.1:5000/api/task/apply
# rebuild tasks
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"taskid": 8}' http://127.0.0.1:5000/api/task/rebuild

# initial repo
curl -i -X POST -F "reponame=dde" -F "config=@config/default.repo.json" http://127.0.0.1:5000/api/repo/create

# create release-candidate division repo
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"create","division":"3302","reponame":"dde", "baserepo":"release-candidate"}' http://127.0.0.1:5000/api/repo/division

# destroy repo by uri
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"destroy","repouri":"dde/release-candidate/3302"}' http://127.0.0.1:5000/api/repo/destroy

# register worker
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"name":"debian-builder-01", "url": "http://10.0.10.29:8223/"}' http://127.0.0.1:5000/api/workers/register

# active worker
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"name":"debian-builder-01", "url": "http://10.0.10.29:8223/"}' http://127.0.0.1:5000/api/workers/active

==============
# tools/repo.py
REPOPATH=/tmp/cache/repos NAME=dde ./repo.py include --cache /tmp/cache/tasks/1/ --base release-candidate/3302
