# coding: utf-8
import re
import decimal
import datetime

from ..common import const


class FieldError(Exception):
    pass


class OutOfRange(FieldError):
    pass


class FormatError(FieldError):
    pass


class FieldTypeError(FieldError):
    pass


class Field():
    def check(self, val):
        raise Exception('cannot be called')

    def to_str(self, val):
        return str(val)


class NumberField(Field):
    def __init__(self, minval=None, maxval=None):
        self._minval = minval
        self._maxval = maxval

    def check_range(self, val):
        if self._minval and val < self._minval:
            raise OutOfRange()
        if self._maxval and val > self._maxval:
            raise OutOfRange()
        return True


class IntField(NumberField):
    def check(self, val):
        if not isinstance(val, (int, long)):
            raise FieldTypeError(str(val) + ' is not number')
        return self.check_range(val)


class FloatField(NumberField):
    def check(self, val):
        if not isinstance(val, float):
            raise FieldTypeError()
        return self.check_range(val)


class MoneyField(Field):
    def __init__(self, minval, maxval, intn, deci):
        self._intn = intn
        self._deci = deci
        self._minval = decimal.Decimal(str(minval))
        self._maxval = decimal.Decimal(str(maxval))

    def check(self, val):
        if isinstance(val, decimal.Decimal):
            if (val < self._minval) or (val > self._maxval):
                raise OutOfRange()
            valstr = str(val)
            pat = const.fieldfmt['money'] % (self._intn, self._deci)
            if not re.match(pat, valstr):
                raise FormatError()
            return True
        elif isinstance(val, (str, unicode)):
            pat = const.fieldfmt['money'] % (self._intn, self._deci)
            if not re.match(pat, val):
                raise FormatError()
        else:
            raise FieldTypeError()


class CharField(Field):
    def __init__(self, minlen=None, maxlen=None, pat=None):
        self._minlen = minlen
        self._maxlen = maxlen
        self._pat = pat

    def check(self, val):
        if not isinstance(val, (str, unicode)):
            raise FieldTypeError()
        if self._minlen and len(val) < self._minlen:
            raise OutOfRange()
        if self._maxlen and len(val) > self._maxlen:
            raise OutOfRange()
        if self._pat and not re.match(self._pat, val):
            raise FormatError(str(val) + '|' + self._pat)
        return True

    def to_str(self, val):
        if not isinstance(val, (str, unicode)):
            raise FieldTypeError()
        return val


class DateTimeField(Field):
    def check(self, val):
        if isinstance(val, datetime.datetime):
            return True
        elif isinstance(val, (str, unicode)):
            if not re.match(const.fieldfmt['datetime'], val):
                raise FormatError()
        else:
            raise FieldTypeError()

    def to_str(self, val):
        if isinstance(val, (str, unicode)):
            return val
        elif isinstance(val, datetime.datetime):
            return val.strftime('%Y-%m-%d %H:%M:%S')
        else:
            raise FieldTypeError()


class DateField(Field):
    def check(self, val):
        if isinstance(val, datetime.date):
            return True
        elif isinstance(val, (str, unicode)):
            if not re.match(const.fieldfmt['date'], val):
                raise FormatError()
        else:
            raise FieldTypeError()
