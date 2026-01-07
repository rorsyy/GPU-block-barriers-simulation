import random
from enum import Enum, auto

class BlockState(Enum):
    """
    线程块 (Block) 的状态枚举
    """
    RUNNING = auto()            # 正在执行指令
    WAITING_AT_BARRIER = auto() # 已到达栅栏，正在等待其他 Block
    FINISHED = auto()           # 全部任务完成

class Block:
    """
    线程块 (Block) 类
    
    代表 GPU 中的一个基本执行单元。
    每个 Block 有自己的指令执行进度，并在特定时刻尝试进行栅栏同步。
    """
    def __init__(self, block_id: int, total_work_ticks: int, barrier, logger=None, workload_variance: float = 0.0):
        """
        :param block_id: Block 的唯一标识 ID
        :param total_work_ticks: 总工作量（模拟时钟周期数）
        :param barrier: 全局栅栏对象的引用
        :param logger: 日志记录器
        :param workload_variance: 工作负载波动方差 (0.0 - 1.0)
        """
        self.id = block_id
        self.total_work_ticks = total_work_ticks
        self.current_work_ticks = 0
        self.state = BlockState.RUNNING
        self.barrier = barrier
        self.logger = logger
        
        # 每一个 Block 维护一个本地的 sense 副本。
        # 初始时默认为 False (0)。
        # 当 Block 等待时，如果发现本地 sense != 全局 sense，说明全局栅栏发生了翻转（释放）。
        self.local_sense = False

        # 模拟执行速度差异因子 (speed factor)
        # 基准为 1.0，根据 variance 进行波动
        # uniform(1.0 - var, 1.0 + var)
        lower_bound = max(0.1, 1.0 - workload_variance)
        upper_bound = 1.0 + workload_variance
        self.speed_factor = random.uniform(lower_bound, upper_bound) 

    def run_step(self):
        """
        执行一步（一个 Tick）的逻辑。
        """
        if self.state == BlockState.FINISHED:
            return

        if self.state == BlockState.RUNNING:
            # 模拟执行计算任务
            self.current_work_ticks += 1 * self.speed_factor
            
            # 简单的完成判断逻辑
            # 注意：实际中完成状态可能由调度器或指令流决定
            if self.current_work_ticks >= self.total_work_ticks:
                self.state = BlockState.FINISHED
                if self.logger:
                    self.logger.log_event("BLOCK_FINISH", {"block_id": self.id})

    def arrive_at_barrier(self):
        """
        Block 到达栅栏调用此方法。
        """
        if self.state == BlockState.RUNNING:
            self.state = BlockState.WAITING_AT_BARRIER
            
            if self.logger:
                self.logger.log_event("BLOCK_WAIT", {"block_id": self.id, "progress": f"{self.current_work_ticks:.2f}"})
            
            triggered_release = self.barrier.arrive(self.id)
            # triggered_release 为 True 表示这个 Block 是最后一个到达的，触发了释放。
            # 但具体的“唤醒”逻辑由 update_sense 在下一帧或当前帧处理。

    def update_sense(self):
        """
        检查栅栏同步状态。
        
        Block 询问 Barrier 自己是否被释放。
        这使得 Block 可以适配 Centralized, Tree 等不同类型的 Barrier 实现。
        """
        if self.state == BlockState.WAITING_AT_BARRIER:
            released, new_sense = self.barrier.check_release(self.id, self.local_sense)
            if released:
                # 发现翻转，解除等待
                if self.logger:
                    self.logger.log_event("BLOCK_RESUME", {"block_id": self.id, "old_sense": int(self.local_sense), "new_sense": int(new_sense)})
                
                self.local_sense = new_sense
                self.state = BlockState.RUNNING

    def get_progress(self) -> float:
        """
        计算当前进度百分比。
        """
        if self.total_work_ticks <= 0: return 100.0
        return min(100.0, (self.current_work_ticks / self.total_work_ticks) * 100.0)

    def get_status(self) -> dict:
        return {
            "id": self.id,
            "state": self.state.name,
            "progress": self.get_progress(),
            "at_barrier": self.state == BlockState.WAITING_AT_BARRIER
        }
