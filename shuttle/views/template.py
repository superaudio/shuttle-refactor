from twisted.internet import defer, reactor
from twisted.web import resource, server
from twisted.python import components

import StringIO
import jinja2
import os

CALL_DELAY = 0.00001
POPULATE_N_STEPS = 10000

from zope import interface

class ITemplateLoader(interface.Interface):
    def load(name):
        """
        Load the template from a unique identifier, usually the file name
        without the path.  The loader itself knows the path to the template.
        """

class ITemplate(interface.Interface):
    def render(**kwargs):
        """
        Return an instance of twisted.internet.defer.Deferred, which will fire
        with the rendered string, or, in the case of an error, an instance of
        TemplateException
        """

def registerIfNotRegistered(adapter, from_, to):
    if not components.getAdapterFactory(from_, to, None):
        components.registerAdapter(adapter, from_, to)

class TemplateException(Exception):
    pass

class Jinja2TemplateAdapter(object):

    interface.implements(ITemplate)

    def __init__(self, template):
        self._buffer = StringIO.StringIO()
        self._stream = None
        self.template = template
        self.delayedCall = None
        self.serialize_method = 'html'

    def _populateBuffer(self, stream, n):
        try:
            for x in xrange(n):
                output = stream.next()
                self._buffer.write(output)
        except StopIteration, e:
            self._deferred.callback(None)
        except Exception, e:
            self._deferred.errback(e)
        else:
            self.delayedCall = reactor.callLater(CALL_DELAY, self._populateBuffer, stream, n)

    def _failed(self, reason):
        if self.delayedCall and self.delayedCall.active():
            self.delayedCall.cancel()
        return "Failed to generate template %s because %s"%(self.template, reason)

    def _rendered(self, ignore):
        result = self._buffer.getvalue()
        self._buffer.close()
        self._buffer = None
        if self.delayedCall and self.delayedCall.active():
            self.delayedCall.cancel()
        return result.encode('UTF-8')

    def render(self, **kwargs):
        iterator = self.template.generate(**kwargs)
        self._stream = self.template.generate(**kwargs)
        self._deferred = defer.Deferred()
        self._deferred.addCallbacks(self._rendered, self._failed)
        self.delayedCall = reactor.callLater(CALL_DELAY, self._populateBuffer,
            iterator, POPULATE_N_STEPS)
        return self._deferred

registerIfNotRegistered(
    Jinja2TemplateAdapter,
    jinja2.Template,
    ITemplate
)

class Jinja2TemplateLoader(object):
    
    interface.implements(ITemplateLoader)
    
    def __init__(self, paths, **options):
        if not paths:
            self.paths = [os.curdir]
        elif isinstance(paths, basestring):
            self.paths = [paths]
        else:
            self.paths = paths

        #TODO: set auto_reload to false when release
        self.options = {"auto_reload": True}
        self.options.update(options)

        self.loader = jinja2.FileSystemLoader(
            [os.path.abspath(p) for p in self.paths],
            encoding="utf-8"
        )

        self.environment = jinja2.Environment(loader=self.loader, **self.options)

    def load(self, name):
        try:
            template = self.environment.get_template(name)
        except jinja2.exceptions.TemplateNotFound:
            raise TemplateException("Template %s not found!"%(name))  
        else:
            return ITemplate(template)

registerIfNotRegistered(
    Jinja2TemplateLoader,
    jinja2.FileSystemLoader,
    ITemplateLoader)

