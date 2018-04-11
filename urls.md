## 任务
### 添加任务
> 其中`build_args`中带`=`的值会当做环境变量导入至编译环境

```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"commit","pkgname":"dde-session-ui","reponame":"dde", "source":"https://cr.deepin.io/dde/dde-session-ui#branch=master", "build_args":["use_network"]}' http://127.0.0.1:5000/api/task/apply
```

```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"release-candidate","pkgname":"dde-session-ui","reponame":"dde", "version":"2.0.0", "source":"https://cr.deepin.io/dde/dde-session-ui#commit=xxxxxx", "build_args":["use_network"]}' http://127.0.0.1:5000/api/task/apply
```
Result:
```
{"triggered": 12, "reponame": "dde", "build_args": ["use_network", "buildtype=dde"], "status_changed": "18-04-08 04:50:44 PM", "expired": "18-04-08 07:32:29 AM", "id": 1, "pkgver": "4.3.7+3+g2509fcd", "pkgname": "dde-session-ui", "hashsum": "2509fcd25c60e3017f00f401ef1c2bebf4e76850", "priority": null, "upload_status": "UNKNOWN", "action": "commit"}
```

### 获取任务信息
```
curl http://10.0.13.190:5000/api/task/2/info
```
Result:
```
{"tasks": [{"status": "BUILDING", "task": "experimental/amd64", "dist": "experimental", "build_start": "18-04-08 04:34:57 PM", "build_host": "debian-builder-01", "status_changed": "18-04-08 04:34:57 PM", "build_end": "waiting", "arch": "amd64", "id": 2, "creation_date": "18-04-08 04:34:54 PM"}], "triggered": 1, "reponame": "dde", "build_args": ["_PKG_TYPE=Professional", "use_network"], "status_changed": "18-04-08 03:49:07 PM", "expired": "18-04-08 03:49:07 PM", "id": 2, "pkgver": "4.3.2+4+g5024810", "pkgname": "dde-launcher", "hashsum": "502481015c150d63e8d5250db07e97526a5c9290", "priority": null, "upload_status": "UNKNOWN", "action": "commit"}
```

### 重新触发任务
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"taskid": 8}' http://127.0.0.1:5000/api/task/rebuild
```

### 重新触发编译
此处`id`为`jobid`, 每个任务可能会多个编译job, 这种触发方式可以避免triggered增加
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"id": 2}' http://127.0.0.1:5000/api/job/rebuild
```
## 仓库管理
### 初始化仓库
```
curl -i -X POST -F "reponame=dde" -F "config=@config/default.repo.json" http://127.0.0.1:5000/api/repo/create
```
> 添加任务需创建仓库, 仓库创建后需要在前端配置仓库信息, 否则编译任务缺失编译环境等必须文件



### 创建`release-candidate` 预发布仓库
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"create","division":"3302","reponame":"dde", "baserepo":"release-candidate"}' http://127.0.0.1:5000/api/repo/division
```

### 删除预发布仓库
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"action":"destroy","repouri":"dde/release-candidate/3302"}' http://127.0.0.1:5000/api/repo/destroy
```

## 编译端控制
### 注册编译服务器
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"name":"debian-builder-01", "url": "http://10.0.10.29:8223/"}' http://127.0.0.1:5000/api/workers/register
```

### 激活编译服务器
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"name":"debian-builder-01", "url": "http://10.0.10.29:8223/"}' http://127.0.0.1:5000/api/workers/active
```
### 移除编译服务器
```
curl -i -H 'Content-Type: application/json' -X POST --data-binary '{"name":"debian-builder-01"}' http://127.0.0.1:5000/api/workers/remove
```

### 显示已添加编译服务器
```
curl -X GET http://127.0.0.1:5000/api/works/list
```
------------
# tools/repo.py
REPOPATH=/tmp/cache/repos NAME=dde ./repo.py include --cache /tmp/cache/tasks/1/ --base release-candidate/3302
