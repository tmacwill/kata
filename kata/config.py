import falcon
import logging
import yaml
import kata.errors

_app = None
data = None

def app():
    global _app
    if _app is None:
        _app = falcon.API()
        _app.add_error_handler(Exception, kata.errors.handler)

    return _app

def initialize(config_file, bare=False):
    global data

    with open(config_file, 'r') as f:
        data = yaml.load(f.read())
        if not data:
            return

        if data.get('debug', False):
            logging.getLogger().setLevel(logging.DEBUG)

        if 'cache' in data:
            import kata.cache
            kata.cache.initialize(data['cache'])

        if 'database' in data:
            import kata.db
            kata.db.initialize(data['database'])

        if 'statsd' in data:
            import kata.stats
            kata.stats.initialize(data['statsd'])

        if 'errors' in data:
            import kata.errors
            kata.errors.initialize(data['errors'])
