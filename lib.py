# coding: utf8

import sys
import pkgutil
import cStringIO
import cgi
import datetime
import time

# override cgi fieldstorage to avoid temp file writing
class MyFieldStorage(cgi.FieldStorage):
    def make_file(self, binary=None):
        return cStringIO.StringIO()
cgi.FieldStorage = MyFieldStorage

import webapp2
import jinja2
import binascii
import uuid
import json
import os

import session
from .. import config
from ..config import redis as redis_conf

##############################
def to_unicode(data, encoding='utf-8'):
    import collections
    _encoding = encoding
    def _convert(data):
        if isinstance(data, unicode):
            return data
        elif isinstance(data, str):
            return unicode(data, _encoding)
        elif isinstance(data, collections.Mapping):
            return dict(map(_convert, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(_convert, data))
        else:
            return data
    return _convert(data)


def to_utf8(data):
    import collections
    def _convert(data):
        if isinstance(data, unicode):
            return data.encode('utf-8')
        elif isinstance(data, str):
            return data
        elif isinstance(data, collections.Mapping):
            return dict(map(_convert, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(_convert, data))
        else:
            return data
    return _convert(data)


def silent_none(value):
    if value is None:
        return ""
    return value


def render(file_path, data={}):
    encoding = 'utf-8'
    data = to_unicode(data, encoding)
    loader = jinja2.PackageLoader(config.render['package_name'],
                                  config.render['template_path'])
    env = jinja2.Environment(loader=loader)
    #env.finalize = silent_none
    template = env.get_template(file_path)

    return template.render(data).encode(encoding)

##############################
def create_session():
    return session.RedisSession(**redis_conf)

def get_session(sid):
    try:
        return session.RedisSession(sid=sid, **redis_conf)
    except:
        return create_session()


##############################
class BaseHandler(webapp2.RequestHandler):
    def respond(self, pat, data={}):
        return render(pat, data)

    def respond_err(self, msg):
        return render('msg.html', {'msg': msg})

    def download(self, name, content):
        self.response.headers.add_header('Content-Type', 'application/octet-stream')
        print name
        self.response.headers.add_header('Content-Disposition',
                                         'attachment; filename="'+name+'"')
        return content

    #csw:add xsrf token for csrf prevention
    def xsrf_token(self):
        if not hasattr(self, "_xsrf_token"):
            token = self.request.cookies.get("_xsrf")
            if not token:
                token = binascii.b2a_hex(uuid.uuid4().bytes)
                self.response.set_cookie("_xsrf", token)
            self._xsrf_token = token
        return self._xsrf_token

    def xsrf_from_html(self):
        return (
            '<input type="hidden" name="_xsrf" value="' +
            self.xsrf_token() + '"/>'
        )

    def check_xsrf_cookie(self):

        token = self.request.get("_xsrf")
        if token == "":
            return False
        if self.xsrf_token() != token:
            return False
        else:
            return True

    def dispatch(self):
        # hack for restful
        method = self.request.get('_method')
        if method:
            self.request.route.handler_method = method.lower()
        rv = super(BaseHandler, self).dispatch()
        self.response.write(rv)

    def get_client_ip(self):
        environ = self.request.environ
        userip = environ['REMOTE_ADDR']
        x_forwarded_for = environ.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            proxy_ips = [ip.strip() for ip in x_forwarded_for.split(',')]
            proxy_ips.reverse()
            if proxy_ips:
                userip = proxy_ips[-1]
                for ip in proxy_ips:
                    if not ip in config.KNOWN_PROXY_IPS:
                        userip = ip
                        break
        return userip


class AuthHandler(BaseHandler):
    def check_perm(self):
        return isinstance(self.perm, (int, long))

    def dispatch(self):
        sid = self.request.cookies.get('_sid')

        if not sid:
            return self.redirect('/login/login')

        self.session = get_session(sid)
        self.perm = self.session.get('perm')
        self.user = self.session.get('user')

        if self.perm is None or self.user is None:
            return self.redirect('/login/login')

        if not self.check_perm():
            return self.response.write(self.respond_err('forbidden'))

        try:
            # Dispatch the request.
            BaseHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session.save()
            pass


class ReleaseHandler(BaseHandler):
    def dispatch(self):
        self.response.content_type = 'text/plain'
        BaseHandler.dispatch(self)
