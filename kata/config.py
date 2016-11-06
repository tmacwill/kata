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

def initialize(config_file):
    global data

    with open(config_file, 'r') as f:
        data = yaml.load(f.read())
        if not data:
            return

        data.setdefault('debug', False)
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

        if 'assets' in data:
            assets = data.get('assets', {})
            assets.setdefault('prefix', '/assets')
            assets_src = assets.get('src', {})
            assets_src.setdefault('css', 'assets/src/css')
            assets_src.setdefault('js', 'assets/src/js')
            assets['src'] = assets_src
            assets_build = assets.get('build', {})
            assets_build.setdefault('css', 'assets/build/css')
            assets_build.setdefault('js', 'assets/build/js')
            assets['build'] = assets_build
            data['assets'] = assets

            import kata.assets
            kata.assets.initialize(data['assets'])
