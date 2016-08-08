import contextlib
import datetime
import decimal
import json
import logging
import msgpack
import psycopg2
import psycopg2.extras
import psycopg2.pool

import kata.cache

_pool = None

def initialize(config):
    global _pool
    if _pool:
        return

    _pool = psycopg2.pool.ThreadedConnectionPool(
        database=config.get('name', ''),
        minconn=1,
        maxconn=config.get('pool_size', 10),
        host=config.get('host', 'localhost'),
        password=config.get('password', ''),
        port=config.get('port', 5432),
        user=config.get('user', '')
    )

    execute('create extension if not exists "uuid-ossp"')

class Object(object):
    __table__ = ''

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, data, unique=None, debug=False):
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

        # handle unique indexes
        unique_string = ''
        if unique:
            # if no columns are given, then update all columns
            unique_columns = unique
            update_columns = data[0].keys()
            if isinstance(unique, dict):
                unique_columns = unique['columns']
                update_columns = unique.get('update', [])

            unique_string = ' on conflict (%s) do update set %s' % (
                ','.join(unique_columns),
                ', '.join(['%s = excluded.%s' % (column, column) for column in update_columns])
            )

        sql = 'insert into "' + cls.__table__ + '"' + fields + values + unique_string + returning
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
        where = column + ' in (' + ','.join(["'%s'" % e if isinstance(e, str) else str(e) for e in values]) + ')'

        # execute query
        rows = query('select ' + columns + ' from ' + cls.__table__ + ' where ' + where + order)

        if rows is None:
            return None

        return [cls(**row) for row in rows]

    @classmethod
    def get_one(cls, data=None, fields=None, order_by=None, limit=None, offset=None):
        return cls.get(one=True, data=data, fields=fields, order_by=order_by, limit=limit, offset=offset)

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
    def update(cls, data, where, debug=False):
        one = False
        if not isinstance(data, list):
            data = [data]
            one = True

        if len(data) == 0:
            return

        returning = ' returning id'
        update = ','.join([e + ' = %s' for e in data[0].keys()])
        where_string = ' where ' + ' and '.join([e + ' = %s' for e in where.keys()])
        args = list(data[0].values()) + list(where.values())

        sql = 'update "' + cls.__table__ + '"' + ' set ' + update + where_string + returning
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

@contextlib.contextmanager
def get_cursor():
    connection = _pool.getconn()
    try:
        yield connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        connection.commit()
    finally:
        _pool.putconn(connection)

def serialize(data, format='json', pretty=False):
    def encode(obj):
        if isinstance(obj, kata.db.Object):
            return obj.fields()
        elif isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)

        return obj

    if format == 'json':
        if pretty:
            return json.dumps(data, default=encode, indent=4).encode('utf-8')
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
