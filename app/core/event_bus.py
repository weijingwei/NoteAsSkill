"""事件总线模块

使用观察者模式实现应用内的事件通信。
解耦组件间的依赖，支持松耦合的事件驱动架构。

设计模式：观察者模式 (Observer Pattern)
- 使用 Qt Signal 实现事件发布/订阅
- 支持跨线程安全的事件传递
- 解耦组件间的直接依赖

优势：
- 松耦合：发布者和订阅者互不直接依赖
- 可扩展：新增事件类型只需添加枚举值
- 线程安全：利用 Qt Signal 的跨线程机制

使用方式：
    # 获取事件总线单例
    bus = get_event_bus()
    
    # 订阅事件
    bus.subscribe(EventType.NOTE_CREATED, self.on_note_created)
    
    # 发布事件
    bus.publish(Event(EventType.NOTE_CREATED, data=note, source="sidebar"))
    
    # 取消订阅
    bus.unsubscribe(EventType.NOTE_CREATED, self.on_note_created)
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal


class EventType(Enum):
    """事件类型枚举
    
    定义应用内所有可能的事件类型。
    新增事件类型只需在此添加新的枚举值。
    """
    NOTE_CREATED = auto()
    NOTE_UPDATED = auto()
    NOTE_DELETED = auto()
    NOTE_MOVED = auto()
    
    FOLDER_CREATED = auto()
    FOLDER_DELETED = auto()
    FOLDER_SKILL_UPDATED = auto()
    FOLDER_SKILL_UPDATE_ERROR = auto()
    
    SKILL_GENERATION_STARTED = auto()
    SKILL_GENERATION_FINISHED = auto()
    SKILL_GENERATION_FAILED = auto()
    
    CONFIG_CHANGED = auto()
    AI_CLIENT_CHANGED = auto()
    AI_PROVIDER_CHANGED = auto()
    
    MCP_SERVER_STARTED = auto()
    MCP_SERVER_STOPPED = auto()
    MCP_SERVER_ERROR = auto()
    MCP_TOOLS_DISCOVERED = auto()
    
    GIT_SYNC_STARTED = auto()
    GIT_SYNC_FINISHED = auto()
    GIT_SYNC_FAILED = auto()


@dataclass
class Event:
    """事件数据类
    
    封装事件的所有信息，包括类型、数据和来源。
    """
    type: EventType
    data: Any = None
    source: str = ""
    timestamp: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        if not self.timestamp:
            from datetime import datetime
            self.timestamp = datetime.now().isoformat()


class EventBus(QObject):
    """事件总线
    
    应用内的事件中心，管理所有事件的发布和订阅。
    使用 Qt Signal 实现跨线程安全的事件传递。
    
    设计模式：观察者模式中的主题 (Subject) 角色
    - 维护订阅者列表
    - 提供订阅/取消订阅接口
    - 负责通知所有订阅者
    
    特点：
    - 单例模式：全局只有一个实例
    - 线程安全：利用 Qt Signal 的线程安全机制
    - 类型安全：使用枚举定义事件类型
    """
    
    _instance: "EventBus | None" = None
    
    event_published = Signal(object)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._subscribers: dict[EventType, list[Callable]] = {}
        self._initialized = True
        
        self.event_published.connect(self._dispatch_event)
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """订阅事件
        
        当指定类型的事件发布时，回调函数将被调用。
        
        Args:
            event_type: 要订阅的事件类型
            callback: 回调函数，接收 Event 参数
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """取消订阅事件
        
        Args:
            event_type: 事件类型
            callback: 要移除的回调函数
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass
    
    def publish(self, event: Event) -> None:
        """发布事件（线程安全）
        
        通过 Qt Signal 发布事件，确保跨线程安全。
        
        Args:
            event: 要发布的事件对象
        """
        self.event_published.emit(event)
    
    def publish_simple(self, event_type: EventType, data: Any = None, source: str = "") -> None:
        """简化的事件发布方法
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
        """
        self.publish(Event(event_type, data, source))
    
    def _dispatch_event(self, event: Event) -> None:
        """分发事件到订阅者
        
        内部方法，由 Signal 触发，负责调用所有订阅者的回调。
        
        Args:
            event: 要分发的事件
        """
        if event.type in self._subscribers:
            for callback in self._subscribers[event.type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Event callback error for {event.type.name}: {e}")
    
    def clear_subscribers(self, event_type: EventType | None = None) -> None:
        """清除订阅者
        
        主要用于测试场景。
        
        Args:
            event_type: 要清除的事件类型，None 表示清除所有
        """
        if event_type is None:
            self._subscribers.clear()
        elif event_type in self._subscribers:
            del self._subscribers[event_type]
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """获取指定事件的订阅者数量
        
        Args:
            event_type: 事件类型
            
        Returns:
            订阅者数量
        """
        return len(self._subscribers.get(event_type, []))


def get_event_bus() -> EventBus:
    """获取事件总线单例
    
    Returns:
        EventBus 实例
    """
    return EventBus()
