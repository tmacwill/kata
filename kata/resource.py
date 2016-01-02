import falcon
import json
import msgpack
import kata.db

class Result(object):
    def __init__(self, status_code, data):
        self.status_code = status_code
        self.data = data

class Resource(object):
    def __init__(self, format='msgpack'):
        self._format = format

    def _respond(self, response, result):
        # use msgpack by default
        response.content_type = 'application/x-msgpack'
        if self._format == 'json':
            response.content_type = 'application/json'
        elif self._format == 'html':
            response.content_type = 'text/html'

        response.status = result.status_code
        data = self._serialize(result.data)
        if isinstance(data, str):
            response.body = data
        else:
            response.data = data

    def _serialize(self, data):
        def encode(obj):
            if isinstance(obj, kata.db.Object):
                return obj.fields()
            elif isinstance(obj, datetime.datetime):
                return obj.isoformat()
            elif isinstance(obj, decimal.Decimal):
                return float(obj)

            return obj

        if self._format == 'json':
            return json.dumps(data, default=encode).encode('utf-8')
        elif self._format == 'html':
            return data

        return msgpack.packb(data, default=encode)

    def body(self, request):
        content_type = request.headers.get('CONTENT-TYPE', 'application/x-msgpack')
        data = request.stream.read().decode('utf-8')
        if 'application/json' in content_type:
            return json.loads(data)

        return msgpack.unpackb(data)

    def not_found(self, data=''):
        return Result(falcon.HTTP_404, data)

    def on_get(self, request, response, *args, **kwargs):
        result = self.get(request, response, *args, **kwargs)
        self._respond(response, result)

    def on_post(self, request, response, *args, **kwargs):
        result = self.post(request, response, *args, **kwargs)
        self._respond(response, result)

    def success(self, data=''):
        return Result(falcon.HTTP_200, data)

    def unauthorized(self, data=''):
        return Result(falcon.HTTP_403, data)
