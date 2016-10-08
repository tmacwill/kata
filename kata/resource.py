import falcon
import json
import msgpack
import kata.db
import kata.stats

class Result(object):
    def __init__(self, status_code, data, headers=None):
        self.status_code = status_code
        self.data = data
        self.headers = headers or []

class Resource(object):
    format = 'json'
    log = ''
    __type__ = 'resource'

    def __init__(self, format=None):
        self._format = self.__class__.format
        if format:
            self._format = format

    def _handle(self, request_type, request, response, *args, **kwargs):
        resource_log = self.__class__.log
        if not resource_log:
            resource_log = self.__class__.__name__.lower()

        result = self.not_found()
        if hasattr(self, request_type):
            resource_timer = kata.stats.start_timer(
                'speed.%s.%s.%s' % (self.__class__.__type__, request_type, resource_log)
            )
            overall_timer = kata.stats.start_timer(
                'speed.%s.%s.all' % (self.__class__.__type__, request_type)
            )
            result = getattr(self, request_type)(request, response, *args, **kwargs)

            # log resource timing
            kata.stats.stop_timer(resource_timer)
            kata.stats.stop_timer(overall_timer)

            # log http response code
            if result and hasattr(result, 'status_code') and len(result.status_code.split(' ')) > 0:
                status = result.status_code.split(' ')[0]
                kata.stats.increment(
                    'response.%s.%s.%s.%s' % (self.__class__.__type__, request_type, resource_log, status)
                )
                kata.stats.increment(
                    'response.%s.%s.all.%s' % (self.__class__.__type__, request_type, status)
                )

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

        if result:
            for header in result.headers:
                response.set_header(header[0], header[1])

    def _serialize(self, data):
        if self._format == 'json':
            return kata.db.serialize(data, 'json')
        elif self._format == 'msgpack':
            return kata.db.serialize(data, 'msgpack')

        return data

    def bad_request(self, data=''):
        return Result(falcon.HTTP_400, data)

    def forbidden(self, data=''):
        return Result(falcon.HTTP_403, data)

    def not_found(self, data=''):
        return Result(falcon.HTTP_404, data)

    def on_get(self, request, response, *args, **kwargs):
        self._handle('get', request, response, *args, **kwargs)

    def on_post(self, request, response, *args, **kwargs):
        self._handle('post', request, response, *args, **kwargs)

    def ok(self, data=''):
        return Result(falcon.HTTP_200, data)

    def redirect(self, url):
        return Result(falcon.HTTP_301, '', [('Location', url)])

    def request_body(self, request):
        content_type = request.headers.get('CONTENT-TYPE', 'application/json')
        data = request.stream.read().decode('utf-8')
        if 'application/x-msgpack' in content_type or 'application/msgpack' in content_type:
            return msgpack.unpackb(data)

        return json.loads(data)

    def success(self, data=''):
        return self.ok(data=data)

    def unauthorized(self, data=''):
        return Result(falcon.HTTP_401, data)
