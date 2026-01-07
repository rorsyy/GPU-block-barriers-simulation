"""
传播式栅栏 (Dissemination Barrier)

原理：每轮中，每个线程块向距离为 2^k 的伙伴发送信号
优势：无需中心协调器，对称性好，无单点竞争
通信轮数：log₂(N) 轮
适用场景：大规模同步、分布式系统
"""

from typing import Dict, Any, Tuple
import math
from .barrier_metrics import BarrierMetrics


class DisseminationBarrier:
    """
    传播式栅栏 (Dissemination Barrier)
    
    每个Block在第k轮向距离为2^k的伙伴发送消息。
    经过log₂(N)轮后，所有Block都收到了来自所有其他Block的消息。
    """
    
    def __init__(self, limit: int, logger=None):
        self.limit = limit
        self.logger = logger
        self.released = False
        
        # 计算需要的轮数
        self.num_rounds = math.ceil(math.log2(limit)) if limit > 1 else 1
        
        # 为每个Block维护其在各轮的到达状态
        # rounds_arrived[block_id][round] = True/False
        self.rounds_arrived = {i: [False] * self.num_rounds for i in range(limit)}
        
        # Global sense for release detection
        self.global_sense = False
        
        # 性能指标
        self.metrics = BarrierMetrics("DisseminationBarrier")
        self.metrics.communication_rounds = self.num_rounds
        
    def arrive(self, block_id: int) -> bool:
        """Block到达栅栏"""
        # 记录竞争（Dissemination的竞争非常低，每轮只需与一个伙伴交互）
        self.metrics.record_contention(self.num_rounds)
        
        # 模拟所有轮次的传播
        for round_num in range(self.num_rounds):
            # 计算伙伴ID: (block_id + 2^round_num) % N
            partner = (block_id + (1 << round_num)) % self.limit
            self.rounds_arrived[block_id][round_num] = True
            
        # 检查所有Block是否都完成了所有轮次
        all_done = all(
            all(rounds) for rounds in self.rounds_arrived.values()
        )
        
        if all_done:
            self.release_all()
            return True
            
        if self.logger:
            self.logger.log_event("BARRIER_ARRIVE", {
                "type": "DISSEMINATION",
                "block_id": block_id,
                "rounds": self.num_rounds
            })
            
        return False
    
    def release_all(self):
        """释放所有Block"""
        self.global_sense = not self.global_sense
        # 重置所有轮次状态
        for block_id in range(self.limit):
            self.rounds_arrived[block_id] = [False] * self.num_rounds
        self.released = True
        
        if self.logger:
            self.logger.log_event("BARRIER_RELEASE", {
                "type": "DISSEMINATION",
                "rounds": self.num_rounds
            })
    
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        """检查是否被释放"""
        if local_sense != self.global_sense:
            return True, self.global_sense
        return False, local_sense
    
    def is_full(self) -> bool:
        """检查栅栏是否已满"""
        return self.released
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        completed_count = sum(1 for rounds in self.rounds_arrived.values() if all(rounds))
        return {
            "type": "DISSEMINATION",
            "completed_count": completed_count,
            "total": self.limit,
            "rounds": self.num_rounds,
            "is_released": self.released
        }
    
    def reset_released_flag(self):
        """重置释放标志"""
        self.released = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.get_statistics()
