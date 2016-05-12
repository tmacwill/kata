def _deserialize(data):
    import pickle
    return pickle.loads(data)

def _memcache_deserialize(key, value, flags):
    return _deserialize(value)

def _memcache_serialize(key, value):
    return _serialize(value), 0

def _serialize(data):
    import pickle
    return pickle.dumps(data)

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

class Memcached(_Cache):
    def __init__(self, hosts, prefix):
        host_tuples = []
        for host in hosts:
            host_parts = host.split(':')
            host_tuples.append((host_parts[0], int(host_parts[1])))

        import pymemcache.client.hash
        self.store = pymemcache.client.hash.HashClient(
            host_tuples,
            deserializer=_memcache_deserialize,
            serializer=_memcache_serialize
        )

    def delete(self, key):
        self.store.delete(key)

    def delete_multi(self, keys):
        self.store.delete_multi(keys)

    def get(self, key):
        return self.store.get(key)

    def get_multi(self, keys):
        return self.store.get_multi(keys)

    def set(self, key, value, expire=0):
        self.store.set(key, value, expire=expire)

    def set_multi(self, value_map, expire=0):
        self.store.set_multi(value_map, expire=expire)

class Memory(_Cache):
    def __init__(self):
        self._data = {}

    def delete(self, key):
        self._data.pop(key, None)

    def delete_multi(self, keys):
        for key in keys:
            self._data.pop(key, None)

    def get(self, key):
        import time
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

class Redis(_Cache):
    def __init__(self, db, host, prefix):
        host_parts = host.split(':')
        self.prefix = prefix

        import redis
        self.store = redis.StrictRedis(
            db=db,
            host=host_parts[0],
            port=host_parts[1]
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

        return _deserialize(data)

    def get_multi(self, keys):
        pipe = self.store.pipeline()
        for key in keys:
            pipe.get(self._key(key))

        return [_deserialize(e) if e is not None else None for e in pipe.execute()]

    def set(self, key, value, expire=None):
        k = self._key(key)
        self.store.set(k, _serialize(value))

        if expire is not None:
            self.store.expire(k, expire)

    def set_multi(self, value_map, expire=None):
        pipe = self.store.pipeline()
        for key, value in value_map.items():
            k = self._key(key)
            pipe.set(k, _serialize(value))

            if expire is not None:
                pipe.expire(k, expire)

        return pipe.execute()

def initialize(config):
    for name, data in config.items():
        if data['type'] == 'memcache' or data['type'] == 'memcached':
            globals()[name] = Memcached(
                hosts=data.get('hosts', ['localhost:11211']),
                prefix=data.get('prefix', '')
            )
        elif data['type'] == 'memory':
            globals()[name] = Memory()
        elif data['type'] == 'redis':
            globals()[name] = Redis(
                db=data.get('db', 0),
                host=data.get('host', 'localhost:6379'),
                prefix=data.get('prefix', '')
            )
