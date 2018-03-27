# apply tasks
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"commit","pkgname":"dde-session-ui","reponame":"dde"}' http://127.0.0.1:5000/api/task/apply

# initial repo
curl -i -X POST -F "reponame=dde" -F "config=@config/default.repo.json" http://127.0.0.1:5000/api/repo/create

# create release-candidate division repo
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"create","division":"3302","reponame":"dde", "baserepo":"release-candidate"}' http://127.0.0.1:5000/api/repo/division

# destroy repo by uri
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"destroy","repouri":"dde/release-candidate/3302"}' http://127.0.0.1:5000/api/repo/destroy

# register worker
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"name":"debian-builder-01", "url": "http://10.0.10.29:8221/"}' http://127.0.0.1:5000/api/workers/register
