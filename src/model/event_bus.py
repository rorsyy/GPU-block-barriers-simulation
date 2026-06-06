"""
事件总线 (Event Bus)

用于解耦调度器、栅栏和线程块之间的通信。
通过事件驱动模式，各组件无需直接引用即可通信。
"""

from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass


class EventType(Enum):
    """事件类型枚举"""
    BARRIER_ARRIVAL = auto()     # 线程块到达栅栏
    BARRIER_RELEASE = auto()     # 栅栏释放线程块
    BLOCK_FAILURE = auto()       # 线程块失败/超时
    BLOCK_RECOVERY = auto()      # 线程块恢复
    TICK_UPDATE = auto()         # 时钟更新


@dataclass
class Event:
    """事件基类"""
    event_type: EventType
    tick: int  # 事件发生的时钟周期
    data: Dict[str, Any]  # 事件附加数据


class EventBus:
    """
    事件总线
    
    负责事件的订阅和分发。
    组件可以订阅感兴趣的事件类型，当事件发生时会收到通知。
    """
    
    def __init__(self, logger=None):
        """
        初始化事件总线
        
        :param logger: 日志记录器
        """
        self.logger = logger
        # 事件订阅者字典: {EventType: [callback_functions]}
        self._subscribers: Dict[EventType, List[Callable]] = {}
        # 事件历史记录（用于调试）
        self._event_history: List[Event] = []
        
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        订阅事件
        
        :param event_type: 要订阅的事件类型
        :param callback: 回调函数，签名为 callback(event: Event) -> None
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        
        if self.logger:
            self.logger.log_event("EVENT_SUBSCRIBE", {
                "event_type": event_type.name,
                "callback": callback.__name__ if hasattr(callback, '__name__') else str(callback)
            })
    
    def unsubscribe(self, event_type: EventType, callback: Callable):
        """
        取消订阅事件
        
        :param event_type: 事件类型
        :param callback: 要移除的回调函数
        """
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    def publish(self, event: Event):
        """
        发布事件
        
        :param event: 要发布的事件对象
        """
        # 记录事件历史
        self._event_history.append(event)
        
        # 限制历史记录大小，避免内存泄漏
        if len(self._event_history) > 1000:
            self._event_history.pop(0)
        
        if self.logger:
            self.logger.log_event("EVENT_PUBLISH", {
                "event_type": event.event_type.name,
                "tick": event.tick,
                "data": event.data
            })
        
        # 通知所有订阅者
        if event.event_type in self._subscribers:
            # 复制一份订阅者列表，避免在回调中修改订阅导致的问题
            subscribers = self._subscribers[event.event_type][:]
            for callback in subscribers:
                try:
                    callback(event)
                except Exception as e:
                    if self.logger:
                        self.logger.log_event("EVENT_ERROR", {
                            "event_type": event.event_type.name,
                            "error": str(e),
                            "callback": callback.__name__ if hasattr(callback, '__name__') else str(callback)
                        })
    
    def get_event_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """
        获取事件历史
        
        :param event_type: 可选，筛选特定类型的事件
        :param limit: 返回的最大事件数量
        :return: 事件列表
        """
        if event_type is None:
            return self._event_history[-limit:]
        else:
            filtered = [e for e in self._event_history if e.event_type == event_type]
            return filtered[-limit:]
    
    def clear_history(self):
        """清空事件历史"""
        self._event_history.clear()


# 辅助函数：创建特定类型的事件

def create_barrier_arrival_event(tick: int, block_id: int, barrier_id: str = "global") -> Event:
    """
    创建栅栏到达事件
    """
    return Event(
        event_type=EventType.BARRIER_ARRIVAL,
        tick=tick,
        data={
            "block_id": block_id,
            "barrier_id": barrier_id
        }
    )


def create_barrier_release_event(tick: int, block_ids: List[int], barrier_id: str = "global") -> Event:
    """
    创建栅栏释放事件
    """
    return Event(
        event_type=EventType.BARRIER_RELEASE,
        tick=tick,
        data={
            "block_ids": block_ids,
            "barrier_id": barrier_id
        }
    )


def create_block_failure_event(tick: int, block_id: int, reason: str) -> Event:
    """
    创建线程块失败事件
    """
    return Event(
        event_type=EventType.BLOCK_FAILURE,
        tick=tick,
        data={
            "block_id": block_id,
            "reason": reason
        }
    )


def create_tick_update_event(tick: int) -> Event:
    """
    创建时钟更新事件
    """
    return Event(
        event_type=EventType.TICK_UPDATE,
        tick=tick,
        data={}
    )
