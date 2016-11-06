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

    def css_tag(self, path):
        return '<link rel="stylesheet" type="text/css" href="%s" />' % path

    def external_css(self):
        return []

    def external_js(self):
        return [
            'https://cdnjs.cloudflare.com/ajax/libs/react/15.3.2/react.js',
            'https://cdnjs.cloudflare.com/ajax/libs/react/15.3.2/react-dom.js',
            'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.1.1/jquery.min.js',
        ]

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
        %s
    </body>
</html>
        ''' % (
            self.title(),
            json.dumps(self.js_data(request, *args, **kwargs)),
            ''.join([self.css_tag(e) for e in self.external_css()]),
            self.head(request, *args, **kwargs),
            self.body(request, *args, **kwargs),
            ''.join([self.js_tag(e) for e in self.external_js()]),
            self.js_tag(_asset_path('js', self.js())),
        ))

    def head(self, request, *args, **kwargs):
        return ''

    def js(self):
        return ''

    def js_data(self, request, *args, **kwargs):
        return {}

    def js_tag(self, path):
        return '<script type="text/javascript" src="%s"></script>' % path

    def title(self):
        return ''

def _asset_path(asset_type, asset):
    if not asset:
        return ''

    path_prefix = kata.config.data['assets']['build'][asset_type]
    return '/' + path_prefix + asset + '.min.%s' % asset_type
