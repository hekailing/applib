# coding: utf8
import functools

import MySQLdb
from MySQLdb.cursors import DictCursor

from .. import config


class DbError(Exception):
    pass


class OpenError(DbError):
    pass


class CommitError(DbError):
    pass


class DbConnection():
    def __init__(self):
        self._connection = None
        self._connections = 0
        self._transactions = 0

    def open(self):
        if self._connections == 0:
            try:
                self._connection = MySQLdb.connect(**config.mysqldb)
            except MySQLdb.DatabaseError:
                raise OpenError()
            self._connection.autocommit(True)
        self._connections = self._connections + 1

    def close(self):
        self._connections = self._connections - 1
        if self._connections == 0:
            self._connection.close()

    def open_cursor(self):
        return self._connection.cursor(DictCursor)

    def inc_trans(self):
        if self._transactions == 0:
            self._connection.autocommit(False)
        self._transactions = self._transactions + 1

    def dec_trans(self):
        self._transactions = self._transactions - 1
        if self._transactions == 0:
            self._connection.autocommit(True)

    def commit(self):
        try:
            self._connection.commit()
        except MySQLdb.DatabaseError:
            raise CommitError()

    def rollback(self):
        try:
            self._connection.rollback()
        except MySQLdb.DatabaseError:
            pass

    def insert_id(self):
        return self._connection.insert_id()


_db_conn = DbConnection()


class _Connection(object):
    """_Connection object can open connection in __enter__,
    and close connection in __exit__
    """
    def __enter__(self):
        _db_conn.open()
        return self

    def __exit__(self, exctype, excvalue, exctraceback):
        _db_conn.close()


def with_connection(func):
    """Decorator for _Connection
    """
    @functools.wraps(func)
    def wrapper(*args, **kv):
        with _Connection():
            return func(*args, **kv)
    return wrapper


class _Transaction(object):
    """Decide commit or rollback according to exception.
    DO NOT use break/continue/return which could jump out of the
    content without exception. If they are necessary, use begin()/
    commit()/rollback()
    """
    def __enter__(self):
        """Enter the content, transaction begins.
        """
        _db_conn.inc_trans()
        return self

    def __exit__(self, exctype, excvalue, exctraceback):
        """Exit the content, commit or rollback according to whether
        an exception accurs.
        @return True: no exception
                False: throw exception again
        """
        try:
            if exctype:
                _db_conn.rollback()
            else:
                _db_conn.commit()
        finally:
            _db_conn.dec_trans()


def with_transaction(func):
    """Decorator for _Transaction
    """
    @functools.wraps(func)
    def wrapper(*args, **kv):
        with _Connection():
            with _Transaction():
                return func(*args, **kv)
    return wrapper


@with_connection
def insert(table, **kv):
    cols, args = zip(*kv.iteritems())
    colstr = ','.join(['`'+col+'`' for col in cols])
    argstr = ','.join(['%s'] * len(args))
    sql = 'INSERT INTO `%s`(%s) VALUES (%s)' % (table, colstr, argstr)
    cursor = None
    try:
        cursor = _db_conn.open_cursor()
        cursor.execute(sql, args)
        return True
    finally:
        if cursor:
            cursor.close()


@with_connection
def update(table, where=None, *where_args, **kv):
    cols, args = zip(*kv.iteritems())
    updatestr = ','.join([('`%s`=%%s' % col) for col in cols])
    if where:
        sql = 'UPDATE `%s` SET %s where %s' % (table, updatestr, where)
    else:
        sql = 'UPDATE `%s` SET %s' % (table, updatestr)
    cursor = None
    try:
        cursor = _db_conn.open_cursor()
        cursor.execute(sql, args + where_args)
        return True
    finally:
        if cursor:
            cursor.close()


@with_connection
def delete(sql, args):
    cursor = None
    try:
        cursor = _db_conn.open_cursor()
        return cursor.execute(sql, args)
    finally:
        if cursor:
            cursor.close()


@with_connection
def select(sql, args, envs = None):
    cursor = None
    try:
        cursor = _db_conn.open_cursor()
        if envs:
            for item in envs.items():
                cursor.execute('SET @%s:=%s', item)
        cursor.execute(sql, args)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()


@with_connection
def select_one(sql, args):
    cursor = None
    try:
        cursor = _db_conn.open_cursor()
        cursor.execute(sql, args)
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()


@with_connection
def count(table, where=None, *where_args):
    if where:
        sql = 'SELECT COUNT(*) FROM %s where %s' % (table, where)
    else:
        sql = 'SELECT COUNT(*) FROM %s' % (table)
    cursor = None
    try:
        cursor = _db_conn.open_cursor()
        cursor.execute(sql, where_args)
        return True
    finally:
        if cursor:
            cursor.close()


def insert_id():
    return _db_conn.insert_id()
