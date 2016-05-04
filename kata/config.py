import yaml
import falcon

_app = None

def app():
    global _app
    if _app is None:
        _app = falcon.API()

    return _app

def initialize(config_file, bare=False):
    with open(config_file, 'r') as f:
        data = yaml.load(f.read())

        if 'database' in data or 'cache' in data:
            import kata.schema
            kata.schema.initialize(data['database'], data['cache'])

        if bare:
            return

        if 'cache' in data:
            import kata.cache
            kata.cache.initialize(data['cache'])

        if 'database' in data:
            import kata.db
            kata.db.initialize(data['database'])
