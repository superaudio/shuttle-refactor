import urllib2

from config import config
import importlib
import json


class Notify(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance
    
    def init(self, *args, **kwargs):
        self.notify_method = {}
    
    def add_method(self, name, cls, *args, **kwargs):
        if name in self.notify_method:
            return
        self.notify_method[name] = cls(*args, **kwargs)
    
    def remove_method(self, name, cls):
        if name not in self.notify_method:
            return
        self.notify_method.pop(name)

    def notify(self, method, *args, **kwargs):
        if method == "all":
            for method in self.notify_method.keys():
                self.notify_method[method].notify(*args, **kwargs)
        else:
            notify_method = self.notify_method.get(method, None)
            if notify_method:
                notify_method.notify(*args, **kwargs)

class Deepinwnb(object):
    def __init__(self, *args, **kwargs):
        self.name = "deepinworknoticebot"
        self.header = {'Content-Type': 'application/json; charset=UTF-8'}
        self.url = "{}/{}".format(kwargs["dwnb_url"],kwargs["dwnb_key"])
        if kwargs.get('mail2users'):
            self.usermapper = json.loads(open(kwargs['mail2users']).read())
        else:
            self.usermapper = None

    def notify(self, message_text, author_email=None, message_channel=[], timeout=15,
            message_attachments=None):

        srcdata = {}
        if author_email and self.usermapper:
            author_name  = self.usermapper.get(author_email, author_email)
            message_text = "@%s " % author_name + message_text

        srcdata['text'] = message_text
        srcdata['markdown'] = "true"
        if message_channel:
            srcdata["channel"] = ",".join(message_channel)
        if message_attachments:
            srcdata["attachments"] = message_attachments

        data = json.dumps(srcdata)
        request = urllib2.Request(self.url, data, self.header)
        opener = urllib2.build_opener()
        return opener.open(request, None, timeout).read()

class BearyChat():
    def __init__(self, *args, **kwargs):
        self.name = "bearychat"
        self.header = {'Content-Type': 'application/json; charset=UTF-8'}
        self.url = kwargs['bearychat_url']
        if kwargs.get('bearychat_users'):
            self.usermapper = json.loads(open(kwargs['bearychat_users']).read())
        else:
            self.usermapper = None
    
    def notify(self, message_text, author_email=None, message_channel=[], timeout=15,
            message_attachments=None):
        
        srcdata = dict()
        if author_email and self.usermapper:
            author_name  = self.usermapper.get(author_email, author_email)
            message_text = "@%s " % author_name + message_text

        srcdata['text'] = message_text
        srcdata['markdown'] = "true"
        if message_channel:
            srcdata["channel"] = ",".join(message_channel)
        if message_attachments:
            srcdata["attachments"] = message_attachments
        
        data = json.dumps(srcdata)
        request = urllib2.Request(self.url, data, self.header)
        opener = urllib2.build_opener()
        return opener.open(request, None, timeout).read()

notify_methods = {
    "bearychat": BearyChat,
    "deepinworknoticebot": Deepinwnb
}
# dynamically import notify methods
for notify in config['notify'].keys():
    if config['notify'][notify].get('enable', False):
        method = notify_methods.get(notify)
        if method:
            Notify().add_method(notify, method, **config['notify'][notify])
