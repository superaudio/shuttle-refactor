#!/usr/bin/env python

import sqlobject
import threading

from packaging import version


class Enumeration:
    def __init__(self, enumlist):
        self.lookup = {}
        self.reverse_lookup = {}
        val = 0
        for elem in enumlist:
            if isinstance(elem, tuple):
                elem, val = elem
            if not isinstance(elem, str):
                raise ValueError("enum name is not a string: " + elem)
            if not isinstance(val, int):
                raise ValueError("enum name is not unique: " + elem)
            if elem in self.lookup:
                raise ValueError("enum name is not unique: " + elem)
            if val in self.lookup.values():
                raise ValueError("enum value is not unique for " + val)
            self.lookup[elem] = val
            self.reverse_lookup[val] = elem
            val += 1

    def __getattr__(self, attr):
        if attr not in self.lookup:
            raise AttributeError
        return self.lookup[attr]

    def whatis(self, value):
        return self.reverse_lookup[value]

JobStatus = Enumeration([
    ("UNKNOWN", 0), ("WAIT", 100), ("WAIT_LOCKED", 150), ("BUILDING", 200),
    ("SOURCE_FAILED", 250), ("BUILD_FAILED", 300), ("POST_BUILD_FAILED", 350),
    ("CANCELED", 800), ("GIVEUP", 850), ("FAILED", 900), ("BUILD_OK", 1000)
])

UploadStatus = Enumeration([
    ("UNKNOWN", 0), ("WAIT", 100),
    ("UPLOADING", 200), ("UPLOAD_FAILED", 300),
    ("UPLOAD_OK", 400), ("UPLOAD_GIVEUP", 500)
])

JobFailedStatus = (
    JobStatus.SOURCE_FAILED,
    JobStatus.BUILD_FAILED,
    JobStatus.FAILED
)

status_lock = threading.Lock()

class Package(threading.Thread, sqlobject.SQLObject):
    """ 
    check package with pkgname, pkgver, reponame, action, hashsum
    action will be ['commit', 'release', 'candidate', 'rebuild', ...]
    """
    pkgname        = sqlobject.StringCol()
    pkgver         = sqlobject.StringCol()
    reponame       = sqlobject.StringCol(default="default")
    action         = sqlobject.StringCol(default="commit")
    
    hashsum        = sqlobject.StringCol(default=None)
    expired        = sqlobject.StringCol(default=None)

    priority       = sqlobject.StringCol(default=None)
    jobs           = sqlobject.MultipleJoin('Job', joinColumn='package_id')

    triggered      = sqlobject.IntCol(default=1)
    upload_status  = sqlobject.IntCol(default=UploadStatus.UNKNOWN)
    status_changed = sqlobject.DateTimeCol(default=sqlobject.DateTimeCol.now())

    
    deps = sqlobject.RelatedJoin('Package', joinColumn='pkga', otherColumn='pkgb')

    notify = None

    def __init__(self, *args, **kwargs):
        sqlobject.SQLObject.__init__(self, *args, **kwargs)
        threading.Thread.__init__(self)

        self.do_quit = threading.Event()
        self.status_lock = status_lock

    def __setattr__(self, name, value):
        if name == "upload_status":
            self.status_changed = sqlobject.DateTimeCol.now()

        sqlobject.SQLObject.__setattr__(self, name, value)

    @staticmethod
    def version_compare(a, b):
        if version.parse(a.pkgver) >= version.parse(b.pkgver):
            return True

        return False
    
    def giveup(self):
        self.upload_status = UploadStatus.UPLOAD_GIVEUP
        for job in self.jobs:
            if job.status == JobStatus.WAIT:
                job.status = JobStatus.GIVEUP

    def is_allowed_to_build(self):
        for dep in Package.selectBy(id=self)[0].deps:
            if Package.selectBy(id=dep)[0].upload_status != UploadStatus.UPLOAD_OK:
                if self.is_maybe_giveup():
                    self.giveup()
                return False
        return True

    def is_maybe_giveup(self):
        for dep in Package.selectBy(id=self)[0].deps:
            for job in Package.selectBy(id=dep)[0].jobs:
                if Job.selectBy(id=job)[0].status in JobFailedStatus:
                    return True
        return False


    def add_dep(self, dep):
        for exist_dep in self.deps:
            if exist_dep.id == dep.id:
                return
        self.addPackage(dep)

    def add_deps(self, deps):
        for dep in deps:
            self.add_dep(dep)

class Job(sqlobject.SQLObject):

    status = sqlobject.IntCol(default=JobStatus.UNKNOWN)
    package = sqlobject.ForeignKey('Package', cascade=True)

    dist = sqlobject.StringCol(default='unreleased')
    arch = sqlobject.StringCol(default='any')

    creation_date = sqlobject.DateTimeCol(default=sqlobject.DateTimeCol.now)
    build_host = sqlobject.StringCol(default=None)
    status_changed = sqlobject.DateTimeCol(default=None)
    build_start = sqlobject.DateTimeCol(default=None)
    build_end = sqlobject.DateTimeCol(default=None)

    def __init__(self, *args, **kwargs):
        sqlobject.SQLObject.__init__(self, *args, **kwargs)
        self.status_lock = status_lock

    def __setattr__(self, name, value):
        if name == "status":
            self.status_changed = sqlobject.DateTimeCol.now()

        sqlobject.SQLObject.__setattr__(self, name, value)

    def start(self, slave, builder):
        if self.status != JobStatus.WAIT_LOCKED:
            raise ValueError("JobStatus is not WAIT_LOCKED")
        else:
            self.status = JobStatus.BUILDING
            self.build_start = sqlobject.DateTimeCol.now()
            self.build_host = slave.name
            return slave.build(self.id, builder, self.package.pkgname, self.package.pkgver, self.arch)
