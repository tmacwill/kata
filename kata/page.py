import hashlib
import kata.config
import kata.resource
import kata.stats
import json

class Page(kata.resource.Resource):
    format = 'html'
    __type__ = 'page'

    def body(self, request, *args, **kwargs):
        return ''

    def css(self):
        return []

    def css_tag(self, path):
        return _css_tag(path)

    def get(self, request, response, *args, **kwargs):
        return self.ok('''
<!doctype html>
<html>
    <head>
        <title>%s</title>
        <script type="text/javascript">window.__data__ = %s;</script>
        %s
        %s
    </head>
    <body>
        %s
        %s
    </body>
</html>
        ''' % (
            self.title(),
            json.dumps(self.js_data(request, *args, **kwargs)),
            ''.join([self.css_tag(e) for e in _asset_tags('css', self.css())]),
            self.head(request, *args, **kwargs),
            self.body(request, *args, **kwargs),
            ''.join([self.js_tag(e) for e in _asset_tags('js', self.js())])
        ))

    def head(self, request, *args, **kwargs):
        return ''

    def js(self):
        return []

    def js_data(self, request, *args, **kwargs):
        return {}

    def js_tag(self, path):
        return _js_tag(path)

    def title(self):
        return ''

def _asset_tags(asset_type, assets):
    if not assets:
        return ''

    debug = kata.config.data.get('debug', False)
    prefix = kata.config.data['assets']['prefix']
    path_prefix = kata.config.data['assets']['src' if debug else 'build'][asset_type]
    result = []
    paths = []
    for asset in assets:
        if ':' in asset:
            result.append(asset)
        else:
            if debug:
                result.append(prefix + asset)
            else:
                paths.append(path_prefix + asset)

    if paths:
        result.append(prefix + _hash_assets(asset_type, paths))

    return result

def _css_tag(path):
    rel = 'stylesheet'
    if path.endswith('.less'):
        rel = 'stylesheet/less'

    return '<link rel="%s" type="text/css" href="%s" />' % (rel, path)

def _hash_assets(asset_type, assets):
    return hashlib.md5(''.join(assets).encode('utf-8')).hexdigest() + '.%s' % asset_type

def _js_tag(path):
    return '<script type="text/javascript" src="%s"></script>' % path

def _register_assets(asset_type, assets):
    global _asset_registry
    _asset_registry[_hash_assets(asset_type, assets)] = assets
