import pickle
import redis
import time

import kata.config

l0 = None
l1 = None

class L0Cache(object):
    def __init__(self):
        self._data = {}

    def delete(self, key):
        del self._data[key]

    def delete_multi(self, keys):
        for key in keys:
            del self._data[key]

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

class L1Cache(object):
    def __init__(self):
        self.store = redis.StrictRedis(
            db=kata.config.redis.db,
            host=kata.config.redis.host,
            port=kata.config.redis.port
        )

    def _key(self, key):
        return kata.config.redis.prefix + str(key)

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

def initialize():
    global l0
    global l1

    l0 = L0Cache()
    l1 = L1Cache()
