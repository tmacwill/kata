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
            if not isinstance(unique_columns, tuple) and not isinstance(unique_columns, list):
                unique_columns = [unique_columns]

            update_columns = data[0].keys()
            if isinstance(unique, dict):
                unique_columns = unique['columns']
                update_columns = unique.get('update', [])

            unique_string = ' on conflict (%s) do update set %s' % (
                ','.join(unique_columns),
                ', '.join(['%s = excluded.%s' % (column, column) for column in update_columns])
            )

        sql = 'insert into "' + cls.__table__ + '"' + fields + values + unique_string + returning
        row_ids = query(sql, args, debug)

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
    def delete(cls, where=None, where_in=None, debug=False):
        # construct where clause
        where_string = ' where '
        args = []

        if where:
            where_string += ' and '.join([e + ' = %s' for e in where.keys()])
            args = [e[1] for e in where.items()]

        if where_in:
            if not isinstance(where_in, list):
                where_in = [where_in]

            if where and len(where) == 1:
                where_string += ' and '

            for where_in_row in where_in:
                column, values = where_in_row
                where_string += column + ' in (' + ','.join(["'%s'" % e if isinstance(e, str) else str(e) for e in values]) + ')'

        sql = 'delete from "' + cls.__table__ + '"' + where_string
        execute(sql, args, debug)

    @classmethod
    def execute(cls, sql, args=None, placeholder='__table__', debug=False):
        return execute(sql.replace(placeholder, cls.__table__), args, debug)

    def fields(self):
        return self.__dict__

    @classmethod
    def get(cls, where=None, where_in=None, fields=None, one=False, order_by=None, limit=None, offset=None, debug=False):
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
        where_string = ''
        args = []

        if where or where_in:
            where_string += ' where '

        if where:
            where_string += ' and '.join([e + ' = %s' for e in where.keys()])
            args = [e[1] for e in where.items()]

        if where_in:
            if not isinstance(where_in, list):
                where_in = [where_in]

            if where and len(where) >= 1:
                where_string += ' and '

            where_string += ' and '.join([
                column + ' in (' + ','.join(["'%s'" % e if isinstance(e, str) else str(e) for e in values]) + ')'
                for (column, values) in where_in
            ])

        # execute query
        sql = 'select ' + columns + ' from ' + cls.__table__ + where_string + order
        rows = query(sql, args, debug)

        if rows is None:
            return None

        # return a single item rather than the entire list
        if one:
            if len(rows) == 0:
                return None
            return cls(**rows[0])

        return [cls(**row) for row in rows]

    @classmethod
    def get_one(cls, where=None, where_in=None, fields=None, order_by=None, limit=None, offset=None, debug=False):
        return cls.get(
            one=True,
            where=where,
            where_in=where_in,
            fields=fields,
            order_by=order_by,
            limit=limit,
            offset=offset,
            debug=debug
        )

    @classmethod
    def query(cls, sql, args=None, placeholder='__table__', debug=False):
        return query(sql.replace(placeholder, cls.__table__), args, debug)

    @classmethod
    def truncate(cls, restart_identity=True):
        sql = 'truncate ' + cls.__table__
        if restart_identity:
            sql += ' restart identity'

        return execute(sql)

    @classmethod
    def update(cls, data, where=None, debug=False):
        one = False
        if not isinstance(data, list):
            data = [data]
            one = True

        if len(data) == 0:
            return

        if not where:
            where = {}

        where_string = ''
        if where:
            where_string += ' where '

        returning = ' returning id'
        update = ','.join([e + ' = %s' for e in data[0].keys()])
        where_string += ' and '.join([e + ' = %s' for e in where.keys()])
        args = list(data[0].values()) + list(where.values())

        sql = 'update "' + cls.__table__ + '"' + ' set ' + update + where_string + returning
        row_ids = query(sql, args, debug)

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
        elif isinstance(obj, datetime.datetime):
            return obj.timestamp()
        elif isinstance(obj, datetime.date):
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

def execute(sql, args=None, debug=False):
    with get_cursor() as cursor:
        logging.debug('Running SQL: ' + str((sql, args)))
        if debug:
            print('Running SQL: ' + str((sql, args)))
        cursor.execute(sql, args)

def query(sql, args=None, debug=False):
    with get_cursor() as cursor:
        logging.debug('Running SQL: ' + str((sql, args)))
        if debug:
            print('Running SQL: ' + str((sql, args)))
        cursor.execute(sql, args)
        return cursor.fetchall()
