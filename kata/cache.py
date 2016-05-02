import pickle
import redis
import time

class _Cache:
    def delete(self, key):
        raise NotImplementedError()

    def delete_multi(self, keys):
        raise NotImplementedError()

    def get(self, key):
        raise NotImplementedError()

    def get_multi(self, keys):
        raise NotImplementedError()

    def set(self, key, value, expire=None):
        raise NotImplementedError()

    def set_multi(self, value_map, expire=None):
        raise NotImplementedError()

class MemoryCache(_Cache):
    def __init__(self):
        self._data = {}

    def delete(self, key):
        self._data.pop(key, None)

    def delete_multi(self, keys):
        for key in keys:
            self._data.pop(key, None)

    def get(self, key):
        value, expire = self._data.get(key, (None, None))
        if expire and time.time() > expire:
            self.delete(key)
            return None

        return value

    def get_multi(self, keys):
        return [self.get(key) for key in keys]

    def set(self, key, value, expire=None):
        self._data[key] = (value, time.time() + expire) if expire else (value, None)

    def set_multi(self, value_map, expire=None):
        for k, v in value_map.items():
            self.set(k, v, expire)

class RedisCache(_Cache):
    def __init__(self, db=0, host='localhost', port=6379, prefix=''):
        self.prefix = prefix
        self.store = redis.StrictRedis(
            db=db,
            host=host,
            port=port
        )

    def _key(self, key):
        return self.prefix + str(key)

    def delete(self, key):
        self.store.delete(self._key(key))

    def delete_multi(self, keys):
        pipe = self.store.pipeline()
        for key in keys:
            pipe.delete(self._key(key))

        pipe.execute()

    def get(self, key):
        data = self.store.get(self._key(key))
        if data is None:
            return data

        return pickle.loads(data)

    def get_multi(self, keys):
        pipe = self.store.pipeline()
        for key in keys:
            pipe.get(self._key(key))

        return [pickle.loads(e) if e is not None else None for e in pipe.execute()]

    def set(self, key, value, expire=None):
        k = self._key(key)
        self.store.set(k, pickle.dumps(value))

        if expire is not None:
            self.store.expire(k, expire)

    def set_multi(self, value_map, expire=None):
        pipe = self.store.pipeline()
        for key, value in value_map.items():
            k = self._key(key)
            pipe.set(k, pickle.dumps(value))

            if expire is not None:
                pipe.expire(k, expire)

        return pipe.execute()

def initialize(config):
    for name, data in config.items():
        if data['type'] == 'memory':
            globals()[name] = MemoryCache()
        elif data['type'] == 'redis':
            globals()[name] = RedisCache(
                db=data.get('db', 0),
                host=data.get('host', 'localhost'),
                port=data.get('port', 6379),
                prefix=data.get('prefix', '')
            )
