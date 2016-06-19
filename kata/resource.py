import falcon
import json
import msgpack
import kata.db
import kata.stats

class Result(object):
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

class Resource(object):
    log = ''

    def __init__(self, format='json'):
        self._format = format

    def _handle(self, request_type, request, response, *args, **kwargs):
        resource_log = self.__class__.log
        if not resource_log:
            resource_log = self.__class__.__name__.lower()

        result = self.not_found()
        if hasattr(self, request_type):
            with kata.stats.timer(request_type + '.' + resource_log):
                result = getattr(self, request_type)(request, response, *args, **kwargs)

            self._respond(response, result)

    def _respond(self, response, result):
        # use json by default
        response.content_type = 'application/json'
        if self._format == 'msgpack':
            response.content_type = 'application/x-msgpack'
        elif self._format == 'html':
            response.content_type = 'text/html'

        data = ''
        if result:
            response.status = result.status_code
            data = self._serialize(result.data)
        else:
            response.status = falcon.HTTP_200

        if isinstance(data, str):
            response.body = data
        else:
            response.data = data

    def _serialize(self, data):
        if self._format == 'json':
            return kata.db.serialize(data, 'json')
        elif self._format == 'msgpack':
            return kata.db.serialize(data, 'msgpack')

        return data

    def body(self, request):
        content_type = request.headers.get('CONTENT-TYPE', 'application/json')
        data = request.stream.read().decode('utf-8')
        if 'application/x-msgpack' in content_type or 'application/msgpack' in content_type:
            return msgpack.unpackb(data)

        return json.loads(data)

    def forbidden(self, data=''):
        return Result(falcon.HTTP_403, data)

    def not_found(self, data=''):
        return Result(falcon.HTTP_404, data)

    def on_get(self, request, response, *args, **kwargs):
        self._handle('get', request, response, *args, **kwargs)

    def on_post(self, request, response, *args, **kwargs):
        self._handle('post', request, response, *args, **kwargs)

    def success(self, data=''):
        return Result(falcon.HTTP_200, data)

    def unauthorized(self, data=''):
        return Result(falcon.HTTP_401, data)
