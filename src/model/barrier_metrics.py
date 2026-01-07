"""
栅栏性能指标收集器 (Barrier Metrics Collector)

用于收集和统计栅栏同步算法的性能指标，支持不同算法之间的性能对比。
"""

import time
from typing import Dict, List, Any
from collections import defaultdict


class BarrierMetrics:
    """
    栅栏性能指标收集器
    
    核心指标：
    - 同步延迟 (Sync Latency): 从第一个Block到达到最后一个Block释放的时间
    - 平均等待时间 (Avg Wait Time): 所有Block在栅栏处等待的平均时长
    - 最大等待时间 (Max Wait Time): 单个Block最长等待时间
    - 竞争次数 (Contention Count): 对共享变量的访问次数
    - 通信轮数 (Communication Rounds): 算法需要的同步阶段数
    - 吞吐量 (Throughput): 单位时间内完成的栅栏同步次数
    """
    
    def __init__(self, barrier_name: str):
        """
        初始化性能指标收集器
        
        :param barrier_name: 栅栏算法名称
        """
        self.barrier_name = barrier_name
        
        # 同步计数器
        self.sync_count = 0  # 总同步次数
        self.total_sync_time = 0.0  # 累计同步总时长（所有Block等待时间之和）
        
        # 延迟相关
        self.total_latency = 0.0  # 累计同步延迟（从第一个到达到最后释放）
        self.latency_samples = []  # 每次同步的延迟记录
        
        # 等待时间相关
        self.wait_times = []  # 每个Block每次等待的时间列表
        self.max_wait_time = 0.0  # 历史最大等待时间
        
        # 竞争次数
        self.contention_count = 0  # 原子操作/共享变量访问次数
        
        # 算法特定指标
        self.communication_rounds = 0  # 通信轮数（累计）
        self.tree_depth = 0  # 树深度（仅适用于树形算法）
        
        # 当前同步周期的临时数据
        self.current_sync_data = {
            "first_arrival_tick": None,  # 第一个Block到达的Tick
            "last_release_tick": None,   # 最后释放的Tick
            "arrival_ticks": {},         # {block_id: arrival_tick}
            "release_tick": None         # 释放时的Tick
        }
        
        # 吞吐量计算
        self.start_time = time.time()  # 开始时间（秒）
        
    def record_arrival(self, block_id: int, tick: int):
        """
        记录某个Block到达栅栏的时刻
        
        :param block_id: Block ID
        :param tick: 到达时的时钟Tick
        """
        # 记录第一个到达的Block
        if self.current_sync_data["first_arrival_tick"] is None:
            self.current_sync_data["first_arrival_tick"] = tick
        
        # 记录该Block的到达时刻
        self.current_sync_data["arrival_ticks"][block_id] = tick
        
    def record_contention(self, count: int = 1):
        """
        记录竞争事件（原子操作、共享变量访问等）
        
        :param count: 竞争次数（默认1次）
        """
        self.contention_count += count
        
    def record_communication_round(self, rounds: int = 1):
        """
        记录通信轮数（适用于多阶段算法如Butterfly、Dissemination）
        
        :param rounds: 轮数
        """
        self.communication_rounds += rounds
        
    def record_release(self, release_tick: int):
        """
        记录栅栏释放时刻
        
        :param release_tick: 释放时的Tick
        """
        self.current_sync_data["release_tick"] = release_tick
        self.current_sync_data["last_release_tick"] = release_tick
        
        # 计算本次同步的延迟
        if self.current_sync_data["first_arrival_tick"] is not None:
            latency = release_tick - self.current_sync_data["first_arrival_tick"]
            self.total_latency += latency
            self.latency_samples.append(latency)
        
        # 计算每个Block的等待时间
        release_tick_val = self.current_sync_data["release_tick"]
        for block_id, arrival_tick in self.current_sync_data["arrival_ticks"].items():
            wait_time = release_tick_val - arrival_tick
            self.wait_times.append(wait_time)
            self.max_wait_time = max(self.max_wait_time, wait_time)
            self.total_sync_time += wait_time
        
        # 增加同步计数
        self.sync_count += 1
        
        # 重置临时数据
        self.current_sync_data = {
            "first_arrival_tick": None,
            "last_release_tick": None,
            "arrival_ticks": {},
            "release_tick": None
        }
        
    def set_tree_depth(self, depth: int):
        """
        设置树深度（仅适用于树形算法）
        
        :param depth: 树的深度
        """
        self.tree_depth = depth
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取性能统计摘要
        
        :return: 包含各项性能指标的字典
        """
        elapsed_time = time.time() - self.start_time  # 运行时长（秒）
        
        # 避免除零错误
        sync_count_safe = max(1, self.sync_count)
        wait_count_safe = max(1, len(self.wait_times))
        
        stats = {
            # 基本信息
            "barrier_type": self.barrier_name,
            "sync_count": self.sync_count,
            "elapsed_time": round(elapsed_time, 2),
            
            # 延迟指标
            "avg_latency": round(self.total_latency / sync_count_safe, 2),
            "min_latency": round(min(self.latency_samples), 2) if self.latency_samples else 0,
            "max_latency": round(max(self.latency_samples), 2) if self.latency_samples else 0,
            
            # 等待时间指标
            "avg_wait_time": round(sum(self.wait_times) / wait_count_safe, 2) if self.wait_times else 0,
            "max_wait_time": round(self.max_wait_time, 2),
            "total_wait_time": round(self.total_sync_time, 2),
            
            # 竞争与通信
            "contention_count": self.contention_count,
            "avg_contention_per_sync": round(self.contention_count / sync_count_safe, 2),
            "communication_rounds": self.communication_rounds,
            "avg_rounds_per_sync": round(self.communication_rounds / sync_count_safe, 2) if self.sync_count > 0 else 0,
            
            # 吞吐量
            "throughput": round(self.sync_count / max(0.001, elapsed_time), 2),  # 次/秒
            
            # 算法特定
            "tree_depth": self.tree_depth if self.tree_depth > 0 else None,
        }
        
        return stats
    
    def reset(self):
        """
        重置所有指标（用于重新开始测试）
        """
        self.__init__(self.barrier_name)
        
    def get_detailed_report(self) -> str:
        """
        生成详细的性能报告（可读文本格式）
        
        :return: 格式化的性能报告字符串
        """
        stats = self.get_statistics()
        
        report = f"""
========== {stats['barrier_type']} 性能报告 ==========
【基本信息】
  - 同步次数: {stats['sync_count']} 次
  - 运行时长: {stats['elapsed_time']} 秒
  - 吞吐量: {stats['throughput']} 次/秒

【延迟指标】
  - 平均同步延迟: {stats['avg_latency']} Ticks
  - 最小延迟: {stats['min_latency']} Ticks
  - 最大延迟: {stats['max_latency']} Ticks

【等待时间】
  - 平均等待时间: {stats['avg_wait_time']} Ticks
  - 最大等待时间: {stats['max_wait_time']} Ticks
  - 总等待时间: {stats['total_wait_time']} Ticks

【竞争与通信】
  - 总竞争次数: {stats['contention_count']} 次
  - 平均每次同步竞争: {stats['avg_contention_per_sync']} 次
  - 总通信轮数: {stats['communication_rounds']} 轮
  - 平均每次同步轮数: {stats['avg_rounds_per_sync']} 轮
"""
        
        if stats['tree_depth'] is not None:
            report += f"\n【树形结构】\n  - 树深度: {stats['tree_depth']} 层\n"
        
        report += "=" * 50 + "\n"
        
        return report
