import yaml
import falcon

_app = None

def app():
    global _app
    if _app is None:
        _app = falcon.API()

    return _app

def initialize(config_file):
    with open(config_file, 'r') as f:
        data = yaml.load(f.read())

        if 'database' in data:
            import kata.db
            kata.db.initialize(data['database'])

        if 'cache' in data:
            import kata.cache
            kata.cache.initialize(data['cache'])
