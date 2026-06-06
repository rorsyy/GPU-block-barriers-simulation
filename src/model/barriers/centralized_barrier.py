"""
集中式栅栏 (Centralized Barrier)
"""
from typing import Dict, Any, Tuple
from ..barrier_metrics import BarrierMetrics
from ..barrier import Barrier
from ..global_memory import GlobalMemory

class CentralizedBarrier(Barrier):
    """
    集中式栅栏
    """
    def __init__(self, limit: int, logger=None):
        super().__init__(limit, logger)
        self.count = 0
        self.sense = False
        self.metrics = BarrierMetrics("CentralizedBarrier")
        self.mem = GlobalMemory({"counter": 0, "sense": 0})

    def arrive(self, block_id: int, tick: int = 0) -> bool:
        self.metrics.record_arrival(block_id, tick)
        # 使用模拟原子指令: old = atomicAdd(&counter, 1)
        old_count = self.sim_atomic_add("counter", 1)
        self.count = old_count + 1
        
        if self.logger:
            self.logger.log_event("BARRIER_ARRIVE", {
                "type": "CENTRALIZED", 
                "block_id": block_id, 
                "count": self.count
            })

        if self.count >= self.limit:
            self.release_all(tick)
            return True
        return False

    def release_all(self, tick: int = 0):
        old_sense = self.sense
        self.sense = not self.sense
        self.count = 0
        
        # 使用模拟原子指令重置计数器和翻转 sense
        self.sim_atomic_exch("counter", 0)
        self.sim_atomic_exch("sense", int(self.sense))
        
        self.released = True
        self.metrics.record_release(tick) 

        if self.logger:
            self.logger.log_event("BARRIER_RELEASE", {
                "type": "CENTRALIZED",
                "sense_flip": f"{int(old_sense)}->{int(self.sense)}"
            })

    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        self.metrics.record_communication(1)
        if local_sense != self.sense:
            return True, self.sense
        return False, local_sense

    def is_full(self) -> bool:
        return self.count >= self.limit

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "CENTRALIZED",
            "count": self.count,
            "limit": self.limit,
            "sense": int(self.sense),
            "is_released": self.released
        }
