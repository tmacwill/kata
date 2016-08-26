import falcon.testing
import json
import kata.config

class TestCase(falcon.testing.TestCase):
    def setUp(self):
        super().setUp()
        self.api = kata.config.app()

    def get(self, *args, **kwargs):
        return self.request('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('POST', *args, **kwargs)

    def request(self, method, path, data=None, headers=None, decode=True, decode_json=True):
        kwargs = {'path': path, 'method': method}
        if data:
            kwargs['body'] = json.dumps(data)
        if headers:
            kwargs['headers'] = headers

        result = self.simulate_request(**kwargs)

        if not decode:
            return result

        if not decode_json:
            return result.content.decode('utf-8')

        return json.loads(result.content.decode('utf-8'))
