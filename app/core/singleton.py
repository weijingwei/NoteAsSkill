"""单例模式基类模块

提供线程安全的单例实现，确保全局只有一个实例。
使用元类方式实现，比装饰器更清晰，比 __new__ 方法更符合 Python 风格。

设计模式：单例模式 (Singleton Pattern)
- 确保一个类只有一个实例
- 提供全局访问点
- 线程安全实现

使用方式：
    class MyClass(metaclass=SingletonMeta):
        def __init__(self):
            self.value = 0
    
    # 获取实例（自动创建或返回已存在的实例）
    instance = MyClass()
    
    # 清除实例（用于测试）
    SingletonMeta.clear_instance(MyClass)
"""
from threading import Lock
from typing import TypeVar, Generic

T = TypeVar('T')


class SingletonMeta(type):
    """线程安全的单例元类
    
    使用双重检查锁定（Double-Checked Locking）模式确保：
    1. 线程安全：多线程环境下只创建一个实例
    2. 性能优化：只在首次创建时加锁
    
    元类方式的优势：
    - 比 __new__ 方法更清晰，不需要在每个类中重复实现
    - 比装饰器更直观，类定义时即可看出是单例
    - 支持继承，子类也可以是单例
    
    Attributes:
        _instances: 存储所有单例实例的字典，键为类，值为实例
        _lock: 线程锁，确保线程安全
    """
    
    _instances: dict[type, object] = {}
    _lock: Lock = Lock()
    
    def __call__(cls, *args, **kwargs):
        """创建或返回单例实例
        
        使用双重检查锁定：
        1. 首先检查实例是否存在（无锁）
        2. 如果不存在，加锁后再次检查
        3. 确认不存在后创建实例
        
        Args:
            *args: 传递给类构造函数的位置参数
            **kwargs: 传递给类构造函数的关键字参数
            
        Returns:
            类的单例实例
        """
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]
    
    @classmethod
    def get_instance(cls, target_cls: type[T]) -> T | None:
        """获取指定类的单例实例（不自动创建）
        
        Args:
            target_cls: 目标类
            
        Returns:
            单例实例，如果不存在则返回 None
        """
        return cls._instances.get(target_cls)
    
    @classmethod
    def clear_instance(cls, target_cls: type) -> None:
        """清除指定类的单例实例
        
        主要用于测试场景，允许重置单例状态。
        
        Args:
            target_cls: 要清除实例的目标类
        """
        with cls._lock:
            if target_cls in cls._instances:
                del cls._instances[target_cls]
    
    @classmethod
    def has_instance(cls, target_cls: type) -> bool:
        """检查指定类是否已有实例
        
        Args:
            target_cls: 目标类
            
        Returns:
            是否存在实例
        """
        return target_cls in cls._instances


class SingletonMixin:
    """单例混入类
    
    提供另一种单例实现方式，通过继承使用。
    适用于需要继承其他类的情况。
    
    使用方式：
        class MyClass(SomeBaseClass, SingletonMixin):
            def __init__(self):
                super().__init__()
    
    注意：SingletonMixin 必须放在继承列表的最后。
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """获取实例"""
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """清除实例"""
        with cls._lock:
            cls._instance = None
