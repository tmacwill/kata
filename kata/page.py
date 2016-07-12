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

    def get(self, request, response, *args, **kwargs):
        return self.success(
            '''
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
                ''.join(['<link rel="stylesheet" type="text/css" href="%s" />' % e for e in self.css()]),
                self.head(request, *args, **kwargs),
                self.body(request, *args, **kwargs),
                ''.join(['<script type="text/javascript" src="%s"></script>' % e for e in self.js()]),
            )
        )

    def head(self, request, *args, **kwargs):
        return ''

    def js(self):
        return []

    def js_data(self, request, *args, **kwargs):
        return {}

    def title(self):
        return ''
