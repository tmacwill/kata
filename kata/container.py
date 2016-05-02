class Attribute(object):
    def __init__(self, *args, **kwargs):
        self._cache = self.cache()
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        pass

    def cache(self):
        raise NotImplementedError()

    def dirty(self, keys):
        if not isinstance(keys, set) and not isinstance(keys, list):
            keys = [keys]
        if not isinstance(keys, set):
            keys = set(keys)

        self._cache.delete_multi([self.key(key) for key in keys])

    def expire(self):
        return 3600

    def get(self, items, one=None):
        if not isinstance(items, set) and not isinstance(items, list):
            items = [items]
            if one is None:
                one = True
        if not isinstance(items, set):
            items = set(items)

        # perform a bulk get on all of the given keys
        items = list(items)
        bulk_keys = [self.key(item) for item in items]
        cached_result = self._cache.get_multi(bulk_keys)
        # if a value returns None, that means the key was missing
        missed_items = [items[i] for i, value in enumerate(cached_result) if value is None]
        if len(missed_items) == 0:
            result = {item: result for item, result in zip(items, cached_result)}
            if one:
                return list(result.values())[0]
            return result

        # pull all of the missing items from ground truth
        result = self.pull(missed_items)
        self._cache.set_multi({self.key(k): v for k, v in result.items()}, expire=self.expire())

        # merge together cached and uncached results
        for i, value in enumerate(cached_result):
            if value is not None:
                result[items[i]] = value

        if one:
            return list(result.values())[0]

        return result

    def key(self, item):
        raise NotImplementedError()

    def pull(self, items):
        model, column = self.attribute()
        return {getattr(e, column): e for e in model.get_in(column, items)}

    def attribute(self):
        raise NotImplementedError()

class Simple(object):
    def __init__(self, *args, **kwargs):
        self._cache = self.cache()
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        pass

    def cache(self):
        raise NotImplementedError()

    def dirty(self):
        self._cache.delete(self.key())

    def expire(self):
        return 3600

    def get(self):
        key = self.key()
        result = self._cache.get(key)
        if result is not None:
            return result

        result = self.pull()
        if result is not None:
            self._cache.set(key, result, expire=self.expire())

        return result

    def key(self):
        raise NotImplementedError()

    def pull(self):
        raise NotImplementedError()

    def refresh(self):
        self.dirty()
        self.get()
