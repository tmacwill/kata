import configparser
import falcon

_app = None

class database:
    __use__ = False
    database = ''
    host = 'localhost'
    pool_size = 10
    password = ''
    port = 5432
    user = ''

class redis:
    __use__ = False
    db = 0
    host = 'localhost'
    port = 6379
    prefix = ''

def app():
    global _app
    if _app is None:
        _app = falcon.API()

    return _app

def initialize(config):
    parser = configparser.ConfigParser()
    parser.read(config)

    if 'database' in parser:
        database.__use__ = True
        for k, v in parser['database'].items():
            setattr(database, k, v)

    if 'redis' in parser:
        redis.__use__ = True
        for k, v in parser['redis'].items():
            setattr(redis, k, v)
