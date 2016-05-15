class Attribute(object):
    def __init__(self, items, *args, **kwargs):
        self._one = False
        if not isinstance(items, set) and not isinstance(items, list):
            items = [items]
            self._one = True
        if not isinstance(items, set):
            items = set(items)

        self._cache = self.cache()
        self._items = items
        self.init(*args, **kwargs)

    def init(self, *args, **kwargs):
        pass

    def cache(self):
        raise NotImplementedError()

    def dirty(self):
        self._cache.delete_multi([self.key(item) for item in self._items])

    def expire(self):
        return 3600

    def get(self, one=None):
        if one is None and self._one:
            one = True

        # perform a bulk get on all of the given keys
        items = list(self._items)
        bulk_keys = [self.key(item) for item in items]
        cached_result = self._cache.get_multi(bulk_keys)

        # determine which items are missing from the bulk cache get
        missed_items = []
        for i, item in enumerate(items):
            if cached_result.get(bulk_keys[i], None) is None:
                missed_items.append(item)

        # if there are no missing items, then we're done
        if len(missed_items) == 0:
            result = {items[i]: cached_result[bulk_keys[i]] for i, _ in enumerate(items)}
            if one:
                return list(result.values())[0]
            return result

        # pull all of the missing items from ground truth
        pull_result = self.pull(missed_items)
        self._cache.set_multi({self.key(k): v for k, v in pull_result.items()}, expire=self.expire())

        # merge together cached and uncached results
        result = {}
        for i, item in enumerate(items):
            if cached_result.get(bulk_keys[i], None) is not None:
                result[item] = cached_result[bulk_keys[i]]
            elif item in pull_result.keys():
                result[item] = pull_result[item]

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
