"""
栅栏性能指标收集器 (Barrier Metrics Collector) - 简化版

只保留两个核心指标：
1. 同步延迟 (Sync Latency): 最后一个线程块到达栅栏到所有线程块被释放的时间
2. 通信开销 (Communication Overhead): 同步过程中的通信次数（线程块间或与全局内存）
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class SyncMetrics:
    """单次同步的指标数据"""
    sync_latency: int = 0           # 同步延迟（ticks）
    communication_count: int = 0     # 通信次数


class BarrierMetrics:
    """
    栅栏性能指标收集器（简化版）
    
    核心指标：
    - 同步延迟 (Sync Latency): 最后一个线程块到达到所有线程块释放的时间
    - 通信开销 (Communication Overhead): 同步过程中的通信次数
    """
    
    def __init__(self, barrier_name: str):
        """
        初始化性能指标收集器
        
        :param barrier_name: 栅栏算法名称
        """
        self.barrier_name = barrier_name
        
        # 同步计数
        self.sync_count = 0
        
        # 延迟相关
        self.total_latency = 0
        self.latency_samples: List[int] = []
        
        # 通信开销
        self.total_communication = 0
        self.communication_samples: List[int] = []
        
        # 当前同步周期的临时数据
        self._current_first_arrival_tick: int = None
        self._current_last_arrival_tick: int = None
        self._current_communication: int = 0
        self._arrived_blocks: set = set()
        
    def record_arrival(self, block_id: int, tick: int):
        """
        记录某个Block到达栅栏的时刻
        
        :param block_id: Block ID
        :param tick: 到达时的时钟Tick
        """
        # 验证输入
        if tick is None or tick < 0:
            return
        
        # 记录第一个到达的Block
        if self._current_first_arrival_tick is None:
            self._current_first_arrival_tick = tick
        
        # 始终更新最后到达时间
        self._current_last_arrival_tick = tick
        self._arrived_blocks.add(block_id)
        
    def record_communication(self, count: int = 1):
        """
        记录一次通信（原子操作、全局内存访问等）
        
        :param count: 通信次数（默认1次）
        """
        self._current_communication += count
        
    def record_release(self, release_tick: int):
        """
        记录栅栏释放时刻，完成本次同步周期的指标计算
        
        :param release_tick: 释放时的Tick
        """
        # 验证输入
        if release_tick is None or release_tick < 0:
            return
        
        # 计算同步延迟：从最后一个到达到释放的时间
        if self._current_last_arrival_tick is not None:
            latency = max(0, release_tick - self._current_last_arrival_tick)
            self.total_latency += latency
            self.latency_samples.append(latency)
        
        # 记录通信开销
        self.total_communication += self._current_communication
        self.communication_samples.append(self._current_communication)
        
        # 增加同步计数
        self.sync_count += 1
        
        # 重置当前周期数据
        self._reset_current_cycle()
        
    def _reset_current_cycle(self):
        """重置当前同步周期的临时数据"""
        self._current_first_arrival_tick = None
        self._current_last_arrival_tick = None
        self._current_communication = 0
        self._arrived_blocks.clear()
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取性能统计摘要
        
        :return: 包含两个核心指标的字典
        """
        # 防止除零错误
        sync_count_safe = max(1, self.sync_count) if self.sync_count is not None else 1
        
        try:
            avg_communication = round(self.total_communication / sync_count_safe, 2)
        except (ZeroDivisionError, TypeError):
            avg_communication = 0.0
        
        try:
            avg_communication = round(self.total_communication / sync_count_safe, 2)
        except (ZeroDivisionError, TypeError):
            avg_communication = 0.0
        
        return {
            "barrier_type": self.barrier_name,
            "sync_count": self.sync_count if self.sync_count is not None else 0,
            
            # 通信开销指标
            "avg_communication": avg_communication,
            "total_communication": self.total_communication if self.total_communication is not None else 0,
        }
    
    def reset(self):
        """重置所有指标"""
        self.__init__(self.barrier_name)
        
    def get_current_state(self) -> Dict[str, Any]:
        """
        获取当前同步周期的状态（用于实时UI显示）
        
        :return: 当前状态字典
        """
        return {
            "arrived_count": len(self._arrived_blocks),
            "current_communication": self._current_communication,
            "first_arrival_tick": self._current_first_arrival_tick,
            "last_arrival_tick": self._current_last_arrival_tick
        }
