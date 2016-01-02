import os
import natsort
import redis

import kata.config

def reset(schema):
    os.system('dropdb -U %s %s' % (kata.config.database.user, kata.config.database.database))
    os.system('createdb -U %s %s' % (kata.config.database.user, kata.config.database.database))

    for file in natsort.natsorted(os.listdir(schema)):
        print('Applying %s' % file)
        os.system(
            'psql -U %s %s < %s > /dev/null' %
            (kata.config.database.user, kata.config.database.database, schema + '/' + file)
        )

    os.system('redis-cli KEYS "%s*" | xargs redis-cli DEL > /dev/null' % kata.config.redis.prefix)
