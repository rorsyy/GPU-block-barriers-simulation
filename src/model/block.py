import random
from enum import Enum, auto

class BlockState(Enum):
    """
    线程块 (Block) 的状态枚举
    """
    RUNNING = auto()            # 正在执行指令
    WAITING_AT_BARRIER = auto() # 已到达栅栏，正在等待其他 Block
    FINISHED = auto()           # 全部任务完成
    FAILED = auto()             # 发生故障/超时

class Block:
    """
    线程块 (Block) 类
    
    代表 GPU 中的一个基本执行单元。
    Refactored:
    - 解耦：不再直接持有 Barrier 引用，只负责自身状态和进度。
    - 随机化：支持每 Tick 随机工作量波动。
    - 故障模拟：支持进入 FAILED 状态。
    """
    def __init__(self, block_id: int, total_work_ticks: int, logger=None, workload_variance: float = 0.0):
        """
        :param block_id: Block 的唯一标识 ID
        :param total_work_ticks: 总工作量（模拟时钟周期数）
        :param logger: 日志记录器
        :param workload_variance: 工作负载波动方差 (0.0 - 1.0)
        """
        self.id = block_id
        self.total_work_ticks = total_work_ticks
        self.current_work_ticks = 0
        self.remaining_work = total_work_ticks  # 剩余工作量
        self.state = BlockState.RUNNING
        self.logger = logger
        
        # 随机化参数
        self.workload_variance = workload_variance
        
        # 故障监测
        self.wait_start_tick = 0
        
        # 本地 sense (用于 release check simulation，逻辑上 block 还是持有 sense)
        self.local_sense = False
        
        # 同步阶段相关参数
        self.previous_phases_work = 0
        self.phase_start_tick = 0
        self.phase_target_tick = 0
        self.phase_work_amount = 0

    def set_phase_target(self, current_tick: int, target_tick: int, phase_work_amount: int):
        """设定当前同步阶段的起始、目标tick和工作量"""
        self.previous_phases_work = self.current_work_ticks
        self.phase_start_tick = current_tick
        self.phase_target_tick = target_tick
        self.phase_work_amount = phase_work_amount

    def run_step(self, current_tick: int) -> bool:
        """
        更新到达同步点的进度。
        """
        if self.state in (BlockState.FINISHED, BlockState.FAILED):
            return False

        if self.state == BlockState.RUNNING:
            if self.phase_target_tick > self.phase_start_tick:
                progress_ratio = (current_tick - self.phase_start_tick) / (self.phase_target_tick - self.phase_start_tick)
                progress_ratio = min(1.0, max(0.0, progress_ratio))
                
                self.current_work_ticks = self.previous_phases_work + progress_ratio * self.phase_work_amount
                self.remaining_work = max(0, self.total_work_ticks - self.current_work_ticks)
                
                if self.remaining_work <= 0 and progress_ratio >= 1.0:
                    self.state = BlockState.FINISHED
                    if self.logger:
                        self.logger.log_event("BLOCK_FINISH", {"block_id": self.id})
                    return False
            return True
        return False

    def set_waiting(self, current_tick: int):
        """进入等待状态"""
        if self.state == BlockState.RUNNING:
            self.state = BlockState.WAITING_AT_BARRIER
            self.wait_start_tick = current_tick
            if self.logger:
                self.logger.log_event("BLOCK_WAIT", {"block_id": self.id, "progress": f"{self.current_work_ticks:.2f}"})

    def resume(self, new_sense: bool = None):
        """从栅栏恢复运行"""
        if self.state == BlockState.WAITING_AT_BARRIER:
            self.state = BlockState.RUNNING
            if new_sense is not None:
                self.local_sense = new_sense
            if self.logger:
                self.logger.log_event("BLOCK_RESUME", {"block_id": self.id})

    def fail(self, reason: str):
        """强制 Failure"""
        self.state = BlockState.FAILED
        if self.logger:
            self.logger.log_event("BLOCK_FAIL", {"block_id": self.id, "reason": reason})

    def get_progress(self) -> float:
        if self.total_work_ticks <= 0: return 100.0
        return min(100.0, (self.current_work_ticks / self.total_work_ticks) * 100.0)

    def get_status(self) -> dict:
        return {
            "id": self.id,
            "state": self.state.name,
            "progress": self.get_progress(),
            "work_done": round(self.current_work_ticks, 1),
            "at_barrier": self.state == BlockState.WAITING_AT_BARRIER
        }
