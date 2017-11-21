# coding: utf8
import time
import random
import redis
import cPickle

import util
import const


class SessionError(Exception):
    pass


class OpenError(SessionError):
    pass


class ReadError(SessionError):
    pass


class WriteError(SessionError):
    pass


class NoDatebaseError(SessionError):
    pass


def _create_sid(ipaddr):
    if not ipaddr:
        ipaddr = '.'.join([str(random.randint(0, 256)) for x in range(0, 4)])
    return util.gen_sha256(str(ipaddr) + str(time.time()+random.random()))


class RedisSession(object):
    """Session whose data is stored in Redis.
    """
    def __init__(self, sid=None,
                 ipaddr=None,
                 host='localhost',
                 port=6379,
                 db=0,
                 password=None,
                 socket_timeout=None):
        """Initial redis.  Generate sid if sid is None.
        @param sid: sid
        @param ipaddr: remote addr used to generate sid
        @param host: redis host addr
        @param port: redis port
        @param db: redis db
        @param password: redis password
        @param socket_timeout: redis timeout
        """
        try:
            self._redis = redis.StrictRedis(host=host, port=port, db=db,
                                            password=password,
                                            socket_timeout=socket_timeout)
        except redis.RedisError:
            raise OpenError()
        self._data = None
        if sid:
            self._sid = sid
            try:
                data = self._redis.get(sid)
            except redis.RedisError:
                raise ReadError()
            if data is not None:
                self._data = cPickle.loads(data)
        if self._data is None:
            self._sid = _create_sid(ipaddr)
            self._data = {}

    @property
    def data(self):
        return self._data

    @property
    def sid(self):
        return self._sid

    def save(self):
        try:
            self._redis.set(self._sid, cPickle.dumps(self._data))
        except redis.RedisError:
            raise WriteError()

    def update(self, **data):
        self._data.update(data)
        self.save()

    def clear(self):
        self._data = {}
        self.save()

    def get(self, key):
        return self._data.get(key)

    def __setitem__(self, key, val):
        self._data[key] = val


def create_session(db, **data):
    if db == 'redis':
        session = RedisSession(sid=None, **const.redis)
        session.update(**data)
        return session
    else:
        raise NoDatebase()


def get_session(db, sid):
    if db == 'redis':
        session = RedisSession(sid=sid, **const.redis)
        return session
    else:
        raise NoDatebase()
