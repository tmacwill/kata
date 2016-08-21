import unittest
import kata.cache
import kata.container

from unittest.mock import patch

attribute_cache = kata.cache.Memory()
attribute2_cache = kata.cache.Memory()
simple_cache = kata.cache.Memory()
simple2_cache = kata.cache.Memory()
simple3_cache = kata.cache.Memory()
simple4_cache = kata.cache.Memory()
simple5_cache = kata.cache.Memory()

class SimpleContainer(kata.container.Simple):
    def init(self, foo):
        self.foo = foo

    def cache(self):
        return simple_cache

    def key(self):
        return 'simple:%s' % self.foo

    def pull(self):
        return _simple_pull(self.foo)

class AttributeContainer(kata.container.Attribute):
    def cache(self):
        return attribute_cache

    def key(self, item):
        return 'attribute:%s' % item

    def pull(self, items):
        return _attribute_pull(items)

class SimpleContainerWithDependency(kata.container.Simple):
    def init(self, foo):
        self.foo = foo

    def cache(self):
        return simple_cache

    def dependencies(self):
        return (SimpleContainer, self.foo)

    def key(self):
        return 'simple2:%s' % self.foo

    def pull(self):
        return _simple_pull(self.foo)

class SimpleContainerWithDependency2(kata.container.Simple):
    def init(self, foo):
        self.foo = foo

    def cache(self):
        return simple3_cache

    def dependencies(self):
        return (SimpleContainerWithDependency, self.foo)

    def key(self):
        return 'simple3:%s' % self.foo

    def pull(self):
        return _simple_pull(self.foo)

class SimpleContainerWithCycle1(kata.container.Simple):
    def init(self, foo):
        self.foo = foo

    def cache(self):
        return simple4_cache

    def dependencies(self):
        return (SimpleContainerWithCycle2, self.foo)

    def key(self):
        return 'simple4:%s' % self.foo

    def pull(self):
        return _simple_pull(self.foo)

class SimpleContainerWithCycle2(kata.container.Simple):
    def init(self, foo):
        self.foo = foo

    def cache(self):
        return simple5_cache

    def dependencies(self):
        return (SimpleContainerWithCycle1, self.foo)

    def key(self):
        return 'simple5:%s' % self.foo

    def pull(self):
        return _simple_pull(self.foo)

class AttributeContainerWithDependecy(kata.container.Attribute):
    def cache(self):
        return attribute2_cache

    def dependencies(self):
        return AttributeContainer(self.items)

    def key(self, item):
        return 'attribute2:%s' % item

    def pull(self, items):
        return _attribute_pull(items)

def _attribute_pull(items):
    return {item: item for item in items}

def _simple_pull(item):
    return item

class TestContainer(unittest.TestCase):
    def test_attribute(self):
        first_items = [1, 2, 3]
        second_items = [1, 2, 4]
        third_items = [1, 2, 3, 4]

        for item in third_items:
            attribute_cache.delete('attribute:%s' % item)

        with patch.object(AttributeContainer, 'pull', side_effect=_attribute_pull) as mock_pull:
            # first execution should run pull
            self.assertEqual(AttributeContainer(first_items).get(), _attribute_pull(first_items))
            mock_pull.assert_called_once_with(first_items)

            # second execution should not run pull again
            self.assertEqual(AttributeContainer(first_items).get(), _attribute_pull(first_items))
            mock_pull.assert_called_once_with(first_items)

        with patch.object(AttributeContainer, 'pull', side_effect=_attribute_pull) as mock_pull:
            # running with second items should only call pull on 4
            self.assertEqual(AttributeContainer(second_items).get(), _attribute_pull(second_items))
            mock_pull.assert_called_once_with([4])

            # second execution should not run pull again
            self.assertEqual(AttributeContainer(second_items).get(), _attribute_pull(second_items))
            mock_pull.assert_called_once_with([4])

        with patch.object(AttributeContainer, 'pull', side_effect=_attribute_pull) as mock_pull:
            # running with third items should not call pull
            self.assertEqual(AttributeContainer(third_items).get(), _attribute_pull(third_items))
            self.assertEqual(mock_pull.called, False)

    def test_attribute_dirty(self):
        first_items = [1, 2, 3]
        second_items = [1, 2, 4]
        third_items = [1, 2, 3, 4]

        for item in third_items:
            attribute_cache.delete('attribute:%s' % item)

        with patch.object(AttributeContainer, 'pull', side_effect=_attribute_pull) as mock_pull:
            # first execution should run pull
            self.assertEqual(AttributeContainer(third_items).get(), _attribute_pull(third_items))
            mock_pull.assert_called_once_with(third_items)

            # second execution should not run pull again
            self.assertEqual(AttributeContainer(third_items).get(), _attribute_pull(third_items))
            mock_pull.assert_called_once_with(third_items)

        with patch.object(AttributeContainer, 'pull', side_effect=_attribute_pull) as mock_pull:
            # dirtying the cache means we should call pull again
            AttributeContainer(third_items).dirty()
            self.assertEqual(AttributeContainer(third_items).get(), _attribute_pull(third_items))
            mock_pull.assert_called_once_with(third_items)

            # second execution should not run pull again
            self.assertEqual(AttributeContainer(third_items).get(), _attribute_pull(third_items))
            mock_pull.assert_called_once_with(third_items)

        with patch.object(AttributeContainer, 'pull', side_effect=_attribute_pull) as mock_pull:
            # dirtying subset of items should call pull for dirtied items
            AttributeContainer(first_items).dirty()
            self.assertEqual(AttributeContainer(third_items).get(), _attribute_pull(third_items))
            mock_pull.assert_called_once_with(first_items)

    def test_simple(self):
        item = 123
        simple_cache.delete('simple:%s' % item)

        with patch.object(SimpleContainer, 'pull', return_value=_simple_pull(item)) as mock_pull:
            # first execution should run pull
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()

            # second execution should not run pull again
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()

    def test_simple_dependencies(self):
        item = 123
        simple_cache.delete('simple:%s' % item)
        simple_cache.delete('simple2:%s' % item)
        simple_cache.delete('simple3:%s' % item)
        simple_cache.delete('simple4:%s' % item)
        simple_cache.delete('simple5:%s' % item)

        # warm containers
        self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
        self.assertEqual(SimpleContainerWithDependency(item).get(), _simple_pull(item))
        self.assertEqual(SimpleContainerWithDependency2(item).get(), _simple_pull(item))
        self.assertEqual(SimpleContainerWithCycle1(item).get(), _simple_pull(item))
        self.assertEqual(SimpleContainerWithCycle2(item).get(), _simple_pull(item))

        with patch.object(SimpleContainer, 'pull', return_value=_simple_pull(item)) as mock_pull, \
                patch.object(SimpleContainerWithDependency, 'pull', return_value=_simple_pull(item)) as mock_pull2:
            # dirtying container with dependency should dirty the other container as well
            SimpleContainerWithDependency(item).dirty()
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            self.assertEqual(SimpleContainerWithDependency(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()
            mock_pull2.assert_called_once_with()

        # we need to go deeper
        with patch.object(SimpleContainer, 'pull', return_value=_simple_pull(item)) as mock_pull, \
                patch.object(SimpleContainerWithDependency, 'pull', return_value=_simple_pull(item)) as mock_pull2, \
                patch.object(SimpleContainerWithDependency2, 'pull', return_value=_simple_pull(item)) as mock_pull3:
            # dirties should propagate recursively
            SimpleContainerWithDependency2(item).dirty()
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            self.assertEqual(SimpleContainerWithDependency(item).get(), _simple_pull(item))
            self.assertEqual(SimpleContainerWithDependency2(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()
            mock_pull2.assert_called_once_with()
            mock_pull3.assert_called_once_with()

        with patch.object(SimpleContainerWithCycle1, 'pull', return_value=_simple_pull(item)) as mock_pull, \
                patch.object(SimpleContainerWithCycle2, 'pull', return_value=_simple_pull(item)) as mock_pull2:
            # dirtying a cycle should only dirty each container once
            SimpleContainerWithCycle1(item).dirty()
            self.assertEqual(SimpleContainerWithCycle1(item).get(), _simple_pull(item))
            self.assertEqual(SimpleContainerWithCycle2(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()
            mock_pull2.assert_called_once_with()

    def test_simple_dirty(self):
        item = 123
        simple_cache.delete('simple:%s' % item)

        with patch.object(SimpleContainer, 'pull', return_value=_simple_pull(item)) as mock_pull:
            # first execution should run pull
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()

            # second execution should not run pull again
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()

        with patch.object(SimpleContainer, 'pull', return_value=_simple_pull(item)) as mock_pull:
            # dirtying the cache means we should call pull again
            SimpleContainer(item).dirty()
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()

            # second execution should not run pull again
            self.assertEqual(SimpleContainer(item).get(), _simple_pull(item))
            mock_pull.assert_called_once_with()

if __name__ == '__main__':
    unittest.main()
