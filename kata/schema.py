import os
import natsort
import subprocess
import re

_cache = None
_database = None

def _dump(flags='', tables=None, exclude_tables=None, path=None):
    tables = tables or []
    exclude_tables = exclude_tables or []

    flags += ' '
    flags += ' '.join(['-t %s' % e for e in tables])
    flags += ' '.join(['-T %s' % e for e in exclude_tables])
    command = 'pg_dump -U %s %s %s' % (_database['user'], flags, _database['name'])

    if path:
        command += ' > %s' % path
        return subprocess.check_call(command, shell=True)

    return subprocess.check_output(command, shell=True)

def initialize(database):
    global _database
    _database = database

def apply(schema, start=0):
    global _database
    if not _database:
        return

    for file in natsort.natsorted(os.listdir(schema)):
        m = re.match('(\d+)', file)
        if not m:
            print('Error applying %s: Migration must start with a number.' % file)
            return

        index = m.group(1)
        if int(index) < start:
            continue

        print('Applying %s' % file)
        os.system(
            'psql -U %s %s < %s > /dev/null' % (_database['user'], _database['name'], schema + '/' + file)
        )

def create_database():
    os.system('createdb -U %s %s' % (_database['user'], _database['name']))

def drop_entire_database_and_lose_all_data():
    os.system('dropdb -U %s %s' % (_database['user'], _database['name']))

def export_data(tables=None, exclude_tables=None, path=None):
    return _dump('--column-inserts --data-only', tables, exclude_tables, path)

def export_schema(path=None):
    return _dump('-s', path=path)

def export_tables(tables=None, exclude_tables=None, path=None):
    return _dump('', tables, exclude_tables, path)

def reset(schema):
    global _database
    if not _database:
        return

    drop_entire_database_and_lose_all_data()
    create_database()
    apply(schema)
