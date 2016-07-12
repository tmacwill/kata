import os
import natsort
import re

_cache = None
_database = None

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

def export_data(tables=None):
    tables_arg = ''
    if tables:
        tables_arg = ' '.join(['-t %s' % e for e in tables])
    os.system('pg_dump -U %s %s -a %s' % (_database['user'], tables_arg, _database['name']))

def export_schema():
    os.system('pg_dump -U %s -s %s' % (_database['user'], _database['name']))

def export_tables(tables=None):
    tables_arg = ''
    if tables:
        tables_arg = ' '.join(['-t %s' % e for e in tables])
    os.system('pg_dump -U %s %s %s' % (_database['user'], tables_arg, _database['name']))

def reset(schema):
    global _database
    if not _database:
        return

    drop_entire_database_and_lose_all_data()
    create_database()
    apply(schema)
