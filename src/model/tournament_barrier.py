"""
锦标赛栅栏 (Tournament Barrier)

原理：类似淘汰赛，成对竞争直至胜者到达根节点
优势：树深度为 log₂(N)，平衡性好
通信轮数：log₂(N) 轮
适用场景：中等规模同步
"""

from typing import Dict, Any, Tuple, List
import math
from .barrier_metrics import BarrierMetrics


class TournamentBarrier:
    """
    锦标赛栅栏 (Tournament Barrier)
    
    类似锦标赛淘汰赛：
    - Round 1: pairs (0,1), (2,3), (4,5), (6,7) compete
    - Round 2: pairs (0,2), (4,6) compete  
    - Round 3: pair (0,4) compete
    - Winner reaches root, then signals propagate back down
    """
    
    class Player:
        """锦标赛中的参与者"""
        def __init__(self):
            self.arrived = False
            self.winner = False
            self.sense = False
    
    def __init__(self, limit: int, logger=None):
        self.limit = limit
        self.logger = logger
        self.released = False
        
        # 计算锦标赛轮数
        self.num_rounds = math.ceil(math.log2(limit)) if limit > 1 else 1
        
        # 为每个Block创建Player
        self.players = {i: self.Player() for i in range(limit)}
        
        # 记录各轮的胜者
        self.round_winners = {r: set() for r in range(self.num_rounds + 1)}
        
        # Global sense
        self.global_sense = False
        
        # 性能指标
        self.metrics = BarrierMetrics("TournamentBarrier")
        tree_depth = self.num_rounds
        self.metrics.set_tree_depth(tree_depth)
        self.metrics.communication_rounds = self.num_rounds
    
    def arrive(self, block_id: int) -> bool:
        """Block到达栅栏"""
        # 记录竞争（每个Block需要经过log₂(N)轮竞争）
        self.metrics.record_contention(self.num_rounds)
        
        self.players[block_id].arrived = True
        
        # 检查所有Player是否都到达
        all_arrived = all(p.arrived for p in self.players.values())
        
        if all_arrived:
            self.release_all()
            return True
        
        if self.logger:
            self.logger.log_event("BARRIER_ARRIVE", {
                "type": "TOURNAMENT",
                "block_id": block_id
            })
        
        return False
    
    def release_all(self):
        """释放所有Block"""
        self.global_sense = not self.global_sense
        
        # 重置所有Player状态
        for player in self.players.values():
            player.arrived = False
            player.winner = False
            player.sense = self.global_sense
        
        self.released = True
        
        if self.logger:
            self.logger.log_event("BARRIER_RELEASE", {
                "type": "TOURNAMENT",
                "rounds": self.num_rounds
            })
    
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        """检查是否被释放"""
        player = self.players[block_id]
        if local_sense != player.sense:
            return True, player.sense
        return False, local_sense
    
    def is_full(self) -> bool:
        """检查栅栏是否已满"""
        return self.released
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        arrived_count = sum(1 for p in self.players.values() if p.arrived)
        return {
            "type": "TOURNAMENT",
            "arrived_count": arrived_count,
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
