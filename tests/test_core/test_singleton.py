"""SingletonMeta 和 SingletonMixin 测试"""
import pytest
from app.core.singleton import SingletonMeta, SingletonMixin


class TestSingletonMeta:
    def test_same_instance(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 42

        a = MySingleton()
        b = MySingleton()
        assert a is b
        SingletonMeta.clear_instance(MySingleton)

    def test_state_shared(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = 0

        a = MySingleton()
        a.value = 100
        b = MySingleton()
        assert b.value == 100
        SingletonMeta.clear_instance(MySingleton)

    def test_clear_and_recreate(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = "initial"

        first = MySingleton()
        first.value = "modified"

        SingletonMeta.clear_instance(MySingleton)

        second = MySingleton()
        assert second.value == "initial"
        SingletonMeta.clear_instance(MySingleton)

    def test_has_instance(self):
        class MySingleton(metaclass=SingletonMeta):
            pass

        assert not SingletonMeta.has_instance(MySingleton)
        MySingleton()
        assert SingletonMeta.has_instance(MySingleton)
        SingletonMeta.clear_instance(MySingleton)

    def test_get_instance(self):
        class MySingleton(metaclass=SingletonMeta):
            def __init__(self):
                self.value = "test"

        assert SingletonMeta.get_instance(MySingleton) is None
        instance = MySingleton()
        assert SingletonMeta.get_instance(MySingleton) is instance
        SingletonMeta.clear_instance(MySingleton)

    def test_clear_nonexistent_is_noop(self):
        class MySingleton(metaclass=SingletonMeta):
            pass

        # 不应抛出异常
        SingletonMeta.clear_instance(MySingleton)
        SingletonMeta.clear_instance(MySingleton)

    def test_different_classes_get_different_instances(self):
        class A(metaclass=SingletonMeta):
            pass

        class B(metaclass=SingletonMeta):
            pass

        a = A()
        b = B()
        assert a is not b
        SingletonMeta.clear_instance(A)
        SingletonMeta.clear_instance(B)


class TestSingletonMixin:
    def test_same_instance(self):
        class MyMixinClass(SingletonMixin):
            def __init__(self):
                self.value = 42

        a = MyMixinClass()
        b = MyMixinClass()
        assert a is b
        MyMixinClass.clear_instance()

    def test_clear(self):
        class MyMixinClass(SingletonMixin):
            def __init__(self):
                self.value = "initial"

        first = MyMixinClass()
        first.value = "modified"
        MyMixinClass.clear_instance()

        second = MyMixinClass()
        assert second.value == "initial"
        MyMixinClass.clear_instance()

    def test_get_instance(self):
        class MyMixinClass(SingletonMixin):
            pass

        assert MyMixinClass.get_instance() is None
        instance = MyMixinClass()
        assert MyMixinClass.get_instance() is instance
        MyMixinClass.clear_instance()

    def test_clear_nonexistent_is_noop(self):
        class MyMixinClass(SingletonMixin):
            pass

        MyMixinClass.clear_instance()
        MyMixinClass.clear_instance()
