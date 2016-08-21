import unittest
import kata.cache

class _Base(object):
    data = {
        'int': 123,
        'string': 'foo',
        'list': [1, 2, 3],
        'dict': {'foo': 'bar', 'baz': 5}
    }

    def _cache(self):
        raise NotImplementedError()

    def test_single(self):
        cache = self._cache()

        for key, value in self.data.items():
            self.assertEqual(cache.get(key), None)
            cache.set(key, value)
            self.assertEqual(cache.get(key), value)
            cache.delete(key)
            self.assertEqual(cache.get(key), None)

    def test_multi(self):
        cache = self._cache()
        keys = self.data.keys()

        for key, value in self.data.items():
            cache.delete(key)

        cache.set_multi(self.data)
        self.assertEqual(cache.get_multi(keys), self.data)

        cache.delete_multi(keys)
        deleted = cache.get_multi(keys)
        for key, value in deleted.items():
            self.assertEqual(value, None)

class TestMemcached(_Base, unittest.TestCase):
    def _cache(self):
        return kata.cache.Memcached(hosts=[('localhost:11211')], prefix='test')

class TestMemory(_Base, unittest.TestCase):
    def _cache(self):
        return kata.cache.Memory()

class TestRedis(_Base, unittest.TestCase):
    def _cache(self):
        return kata.cache.Redis(db=0, host='localhost:6379', prefix='test')

if __name__ == '__main__':
    unittest.main()
