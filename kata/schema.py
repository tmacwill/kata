import os
import natsort
import redis

_cache = None
_database = None

def initialize(database, cache):
    global _cache
    global _database

    _cache = cache
    _database = database

def reset(schema):
    global _cache
    global _database

    if _database:
        os.system('dropdb -U %s %s' % (_database['user'], _database['name']))
        os.system('createdb -U %s %s' % (_database['user'], _database['name']))

        for file in natsort.natsorted(os.listdir(schema)):
            print('Applying %s' % file)
            os.system(
                'psql -U %s %s < %s > /dev/null' % (_database['user'], _database['name'], schema + '/' + file)
            )

    if _cache:
        for name, data in _cache.items():
            if data['type'] == 'redis':
                os.system(
                    'redis-cli -h %s -p %s KEYS "%s*" | xargs redis-cli DEL > /dev/null' %
                    (data.get('host', 'localhost'), data.get('port', 6379), data.get('prefix', ''))
                )
