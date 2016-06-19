import falcon
import yaml
import kata.errors

_app = None

def app():
    global _app
    if _app is None:
        _app = falcon.API()
        _app.add_error_handler(Exception, kata.errors.handler)

    return _app

def initialize(config_file, bare=False):
    with open(config_file, 'r') as f:
        data = yaml.load(f.read())

        if 'database' in data or 'cache' in data:
            import kata.schema
            kata.schema.initialize(data['database'])

        if bare:
            return

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
