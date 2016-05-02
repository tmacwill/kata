import contextlib
import datetime
import decimal
import json
import logging
import msgpack
import psycopg2
import psycopg2.extras
import psycopg2.pool

import kata.config
import kata.cache

_pool = None

def initialize():
    global _pool

    _pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=kata.config.database.pool_size,
        database=kata.config.database.database,
        host=kata.config.database.host,
        password=kata.config.database.password,
        port=kata.config.database.port,
        user=kata.config.database.user
    )

class Object(object):
    __table__ = ''

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, data, constraint=None, debug=False):
        one = False
        if not isinstance(data, list):
            data = [data]
            one = True

        if len(data) == 0:
            return

        fields = ' (%s)' % ','.join(sorted(data[0].keys()))
        values = ' values ' + ','.join([
            '(%s)' % ','.join(['%s'] * len(data[0]))
        ] * len(data))
        returning = ' returning id'
        args = [i[1] for j in data for i in sorted(j.items())]

        # handle upsert constraints
        constraint_string = ''
        if constraint:
            # if no columns are given, then update all columns
            constraint_name = constraint
            columns = data[0].keys()
            if isinstance(constraint, tuple):
                constraint_name, columns = constraint

            constraint_string = ' on conflict on constraint %s do update set %s' % (
                constraint_name,
                ','.join(['%s = excluded.%s' % (column, column) for column in columns])
            )

        sql = 'insert into "' + cls.__table__ + '"' + fields + values + constraint_string + returning
        if debug:
            logging.debug((sql, args))

        row_ids = query(sql, args)

        # add the last insert ID so the returned object has an ID
        if one:
            data = data[0]
            data['id'] = row_ids[0][0]
            return cls(**data)
        else:
            result = []
            for row, row_id in zip(data, row_ids):
                row['id'] = row_id[0]
                result.append(cls(**row))
            return result

    @classmethod
    def execute(cls, sql, args=None, placeholder='__table__'):
        return execute(sql.replace(placeholder, cls.__table__), args)

    def fields(self):
        return self.__dict__

    @classmethod
    def get(cls, data=None, fields=None, one=False, order_by=None, limit=None, offset=None):
        columns = '*'
        if fields is not None:
            columns = ','.join(fields)

        # construct order by clause
        order = ' '
        if order_by is not None:
            order += 'order by %s' % order_by
        if limit is not None:
            order += ' limit %s ' % limit
        if offset is not None:
            order += ' offset %s ' % offset

        # construct where clause
        where = ' '
        args = []
        if data:
            where += 'where ' + ' and '.join([e + ' = %s' for e in data.keys()])
            args = [e[1] for e in data.items()]

        # execute query
        rows = query(
            'select ' + columns + ' from ' + cls.__table__ + where + order,
            args
        )

        if rows is None:
            return None

        # return a single item rather than the entire list
        if one:
            if len(rows) == 0:
                return None
            return cls(**rows[0])

        return [cls(**row) for row in rows]

    @classmethod
    def get_in(cls, column, values, fields=None, order_by=None, limit=None, offset=None):
        columns = '*'
        if fields is not None:
            columns = ','.join(fields)

        if len(values) == 0:
            return []

        # construct order by clause
        order = ' '
        if order_by is not None:
            order += 'order by %s' % order_by
        if limit is not None:
            order += ' limit %s ' % limit
        if offset is not None:
            order += ' offset %s ' % offset

        # construct where clause
        where = column + ' in (' + ','.join(map(str, values)) + ')'

        # execute query
        rows = query('select ' + columns + ' from ' + cls.__table__ + ' where ' + where + order)

        if rows is None:
            return None

        return [cls(**row) for row in rows]

    @classmethod
    def query(cls, sql, args=None, placeholder='__table__'):
        return query(sql.replace(placeholder, cls.__table__), args)

    @classmethod
    def truncate(cls, restart_identity=True):
        sql = 'truncate ' + cls.__table__
        if restart_identity:
            sql += ' restart identity'

        return execute(sql)

    @classmethod
    def update(cls, data, where_data, debug=False):
        one = False
        if not isinstance(data, list):
            data = [data]
            one = True

        if len(data) == 0:
            return

        returning = ' returning id'
        update = ','.join([e + ' = %s' for e in data[0].keys()])
        where = ' where ' + ' and '.join([e + ' = %s' for e in where_data.keys()])
        args = list(data[0].values()) + list(where_data.values())

        sql = 'update "' + cls.__table__ + '"' + ' set ' + update + where + returning
        if debug:
            logging.debug((sql, args))

        row_ids = query(sql, args)

        # add the last insert ID so the returned object has an ID
        if one:
            data = data[0]
            data['id'] = row_ids[0][0]
            return cls(**data)
        else:
            result = []
            for row, row_id in zip(data, row_ids):
                row['id'] = row_id[0]
                result.append(cls(**row))
            return result

class SimpleContainer(object):
    def __init__(self, *args, **kwargs):
        self._cache = self.cache()
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        pass

    def cache(self):
        return kata.cache.l1

    def dirty(self):
        self._cache.delete(self.key())

    def expire(self):
        return 3600

    def get(self):
        key = self.key()
        result = self._cache.get(key)
        if result is not None:
            return result

        result = self.pull()
        if result is not None:
            self._cache.set(key, result, expire=self.expire())

        return result

    def key(self):
        raise NotImplementedError()

    def pull(self):
        raise NotImplementedError()

    def refresh(self):
        self.dirty()
        self.get()

class AttributeContainer(object):
    def __init__(self, *args, **kwargs):
        self._cache = self.cache()
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        pass

    def cache(self):
        return kata.cache.l1

    def dirty(self, keys):
        if not isinstance(keys, set) and not isinstance(keys, list):
            keys = [keys]
        if not isinstance(keys, set):
            keys = set(keys)

        self._cache.delete_multi([self.key(key) for key in keys])

    def expire(self):
        return 3600

    def get(self, items, one=None):
        if not isinstance(items, set) and not isinstance(items, list):
            items = [items]
        if not isinstance(items, set):
            items = set(items)

        # perform a bulk get on all of the given keys
        items = list(items)
        bulk_keys = [self.key(item) for item in items]
        cached_result = self._cache.get_multi(bulk_keys)

        # if a value returns None, that means the key was missing
        missed_items = [items[i] for i, value in enumerate(cached_result) if value is None]
        if len(missed_items) == 0:
            result = {item: result for item, result in zip(items, cached_result)}
            if one is True or (len(items) == 1 and one is None):
                return list(result.values())[0]
            return result

        # pull all of the missing items from ground truth
        result = self.pull(missed_items)
        self._cache.set_multi({self.key(k): v for k, v in result.items()}, expire=self.expire())

        # merge together cached and uncached results
        for i, value in enumerate(cached_result):
            if value is not None:
                result[items[i]] = value

        if one is True or (len(items) == 1 and one is None):
            return list(result.values())[0]

        return result

    def key(self, item):
        raise NotImplementedError()

    def pull(self, items):
        model, column = self.attribute()
        return {getattr(e, column): e for e in model.get_in(column, items)}

    def attribute(self):
        raise NotImplementedError()

@contextlib.contextmanager
def get_cursor():
    connection = _pool.getconn()
    try:
        yield connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        connection.commit()
    finally:
        _pool.putconn(connection)

def serialize(data, format='json'):
    def encode(obj):
        if isinstance(obj, kata.db.Object):
            return obj.fields()
        elif isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)

        return obj

    if format == 'json':
        return json.dumps(data, default=encode).encode('utf-8')
    elif format == 'msgpack':
        return msgpack.packb(data, default=encode)

    return data

def execute(sql, args=None):
    with get_cursor() as cursor:
        cursor.execute(sql, args)

def query(sql, args=None):
    with get_cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()
