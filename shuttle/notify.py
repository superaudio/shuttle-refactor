import urllib2

from . import config
import importlib

notify_methods = {
    "bearychat": "BearyChat"
}

# dynamically import notify methods
for notify in config['notify'].keys():
    if config['notify'][notify].get('enable', False):
        method = notify_methods.get(key)
        if method:
            Notify().add_method(key, method)

class Notify(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            cls._instance.init(*args, **kwargs)
        return cls._instance
    
    def init(self, *args, **kwargs):
        self.notify_method = {}
    
    def add_method(self, name, cls):
        if name in self.notify_method:
            return
        self.notify_method[name] = cls
    
    def remove_method(self, name, cls):
        if name not in self.notify_method:
            return
        self.notify_method.pop(name)

    def notify(self, method, *args, **kwargs):
        notify_method = self.notify_method.get(method, None)
        if notify_method:
            notify_method.notify(*args, **kwargs)

class BearyChat():
    def __init__(self, url):
        self.name = "bearychat"
        self.header = {'Content-Type': 'application/json; charset=UTF-8'}
        self.url = url
    
    def notify(self, message_text, message_channel=[], timeout=15, 
            message_attachments=None):
        
        srcdata = dict()
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