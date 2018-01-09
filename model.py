# coding: utf-8
from ..common import db


class ModelError(Exception):
    pass


class DupOrderError(ModelError):
    def __init__(self):
        super(Exception, self).__init__('order by cannot support multi-column')


class DupJoinError(ModelError):
    def __init__(self):
        super(Exception, self).__init__('duplicate join')


class NoFieldError(ModelError):
    pass


class FilterInputError(ModelError):
    pass


class NoResultError(ModelError):
    pass


class UpdateError(ModelError):
    pass


class InsertError(ModelError):
    pass


class ReadError(ModelError):
    pass


class DeleteError(ModelError):
    pass


class ModelData():
    def __init__(self, model):
        self._model = model
        self._orderstr = ''
        self._filts = []
        self._filtargs = []
        self._data = None
        self._joins = []
        self._jointype = ''
        self._limitstr = ''
        self._time_interval = None
        self._time_begin = None
        self._time_end = None

    def _gen_filter_in(self, name, values):
        """
        (name=v1 OR name=v2)
        """
        if not isinstance(values, (tuple, list, dict)):
            raise FilterInputError()
        filtone = '`%s`=%%s' % name
        filtstr = ' OR '.join([filtone] * len(values))
        filtstr = '(%s)' % filtstr
        if not isinstance(values, (tuple, list, dict)):
            raise FilterInputError()
        return filtstr, list(values)

    def _gen_filter(self, col, val):
        """
        name__neq=value: name!=value
        name__lt=value: name<value
        name__le=value: name<=value
        name__gt=value: name>value
        name__ge=value: name>=value
        name__in=(v1,v2): (name=v1 OR name=v2)
        name__like=value: name like value
        """
        argv = col.split('__')
        argc = len(argv)
        if argc == 1:
            if argv[0] not in self._model.fields:
                raise NoFieldError(argv[0])
            filtstr = '`%s`=%%s' % col
        elif argc == 2:
            if argv[0] not in self._model.fields:
                raise NoFieldError(argv[0])
            if argv[1] == 'neq':
                filtstr = '`%s`!=%%s' % argv[0]
            if argv[1] == 'le':
                filtstr = '`%s`<=%%s' % argv[0]
            if argv[1] == 'lt':
                filtstr = '`%s`<%%s' % argv[0]
            if argv[1] == 'gt':
                filtstr = '`%s`>%%s' % argv[0]
            if argv[1] == 'ge':
                filtstr = '`%s`>=%%s' % argv[0]
            if argv[1] == 'like':
                filtstr = '`%s` like %%s' % argv[0]
            if argv[1] == 'in':
                return self._gen_filter_in(argv[0], val)
        else:
            raise FilterInputError()
        if isinstance(val, (tuple, list, dict)):
            raise FilterInputError()
        return filtstr, [val]

    def filter(self, **kv):
        if not kv:
            return self
        for col, val in kv.iteritems():
            filtstr, filtargs = self._gen_filter(col, val)
            self._filts.append(filtstr)
            self._filtargs = self._filtargs + filtargs
        self._data = None
        return self

    def orderby(self, *args):
        if not args:
            self._orderstr = ''
        if len(args) > 1:
            raise DupOrderError()
        name = args[0]
        desc = ''
        if name[0] == '-':
            desc = 'DESC'
            name = name[1:len(name)]
        if name not in self._model.fields:
            raise NoFieldError(name)
        self._orderstr = 'ORDER BY `%s` %s' % (name, desc)
        self._data = None
        return self

    def limit(self, ndata, offset):
        self._limitstr = 'LIMIT %d,%d' % (offset, ndata)
        self._data = None
        return self

    def leftjoin(self, lfield, rmodel, rfield):
        if self._joins:
            raise DupJoinError()
        self._joins.append((lfield, rmodel, rfield))
        self._jointype = 'LEFT JOIN'
        return self

    def update(self, **kv):
        self._model.check(**kv)
        filtstr = ' AND '.join(self._filts)
        try:
            db.update(self._model.table, filtstr, *self._filtargs, **kv)
        except db.DbError:
            raise UpdateError
        self._data = None

    def timesample(self, field, interval, begin=None, end=None):
        self._time_field = field
        self._time_interval = interval
        self._time_begin = begin
        filts = {}
        if begin:
            filts[field + '__ge'] = begin
        if end:
            filts[field + '__le'] = end
        self.filter(**filts)
        self._time_end = end
        return self

    def _read(self, lock=None, count=False, fields=None):
        outcols = '*'
        envs = {}
        sqls = []
        if self._time_interval and self._time_begin:
            envs['cur_time'] = str(self._time_begin)
        sqls.append('SELECT')
        if count:
            sqls.append('COUNT(*)')
        elif self._joins:
            sqls.append(self._model.table + '.*')
        elif fields:
            sqls.append('`' + '`,`'.join(fields) + '`')
        else:
            sqls.append('*')
        sqls.append('FROM')
        sqls.append('`'+self._model.table+'`')
        if self._joins:
            prefix = self._model.table + '.'
            filts = [prefix + filt for filt in self._filts]
            args = self._filtargs
            join = self._joins[0]
            lfield, rmodel, rfield = join
            prefix = rmodel._model.table + '.'
            filts = filts + [prefix + filt for filt in rmodel._filts]
            args = args + rmodel._filtargs
            joins = '%s.%s=%s.%s' % (self._model.table,
                                     lfield,
                                     rmodel._model.table,
                                     rfield)
            sqls.append('LEFT JOIN')
            sqls.append(rmodel._model.table)
            sqls.append('ON')
            sqls.append(joins)
        else:
            filts = self._filts
            args = self._filtargs
        filtstr = ' AND '.join(filts)
        if filtstr:
            sqls.append('WHERE')
            sqls.append(filtstr)
        if self._time_interval:
            sqls.append('AND')
            sqls.append('TIMESTAMPDIFF(SECOND, @cur_time, `%s`)>=%d' % (self._time_field, self._time_interval))
            sqls.append('AND')
            sqls.append('@cur_time:=`%s`' % self._time_field)
        if self._orderstr:
            sqls.append(self._orderstr)
        if self._limitstr:
            sqls.append(self._limitstr)
        if lock:
            sqls.append(lock)
        sql = ' '.join(sqls)
        try:
            self._data = db.select(sql, args, envs)
        except db.DbError:
            raise ReadError()

    def delete(self):
        sqls = []
        sqls.append('DELETE')
        sqls.append('FROM')
        sqls.append('`'+self._model.table+'`')
        filts = self._filts
        args = self._filtargs
        filtstr = ' AND '.join(filts)
        if filtstr:
            sqls.append('WHERE')
            sqls.append(filtstr)
        sql = ' '.join(sqls)
        try:
            return db.delete(sql, args)
        except db.DbError:
            raise DeleteError()

    def count(self):
        self._read(count=True)
        cnt = self._data[0]['COUNT(*)']
        self._data = None
        return cnt

    def output(self, *args):
        if self._data is None:
            self._read(fields=args)
        return self._data

    def get(self, ndata, offset=0):
        self.limit(ndata, offset)
        self._read()
        data, self._data = self._data, None
        return data

    def getall(self, *args):
        return self.output(*args)

    def getone(self):
        self._read()
        data, self._data = self._data, None
        if not data:
            raise NoResultError()
        return data[0]

    def get_to_update(self, ndata, offset=0):
        self.limit(ndata, offset)
        self._read(lock='FOR UPDATE')
        data, self._data = self._data, None
        return data

    def getall_to_update(self):
        self._read(lock='FOR UPDATE')
        return self._data

    def getone_to_update(self):
        self._read(lock='FOR UPDATE')
        data, self._data = self._data, None
        if not data:
            raise NoResultError()
        return data[0]


class Model():
    table = ''
    fields = {}

    @classmethod
    def data(cls):
        return ModelData(cls)

    @classmethod
    def check(cls, **kv):
        for key, val in kv.iteritems():
            if key in cls.fields:
                cls.fields[key].check(val)
            else:
                raise NoFieldError(key)

    @classmethod
    def insert(cls, **kv):
        cls.check(**kv)
        try:
            db.insert(cls.table, **kv)
        except db.DbError:
            raise InsertError()

    @classmethod
    def update(cls, **kv):
        cls.data().update(**kv)

    @classmethod
    def count(cls, **kv):
        cls.data().count(**kv)

    @classmethod
    def delete(cls, **kv):
        cls.data().delete(**kv)
