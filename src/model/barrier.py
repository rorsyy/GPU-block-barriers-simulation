from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from .barrier_metrics import BarrierMetrics
from .global_memory import GlobalMemory

class Barrier(ABC):
    """
    栅栏 (Barrier) 抽象基类

    在硬件映射中，Barrier 代表 SM (Streaming Multiprocessor) 的控制逻辑。
    原子指令 (sim_atomic_add / sim_atomic_exch) 由 SM 发起，
    通过引用独立的 GlobalMemory 模块完成底层的读写操作，
    并在此刻触发 metrics 进行通信开销打点。
    """
    def __init__(self, limit: int, logger=None):
        self.limit = limit
        self.logger = logger
        self.released = False
        self.metrics: BarrierMetrics = None
        self.mem: GlobalMemory = GlobalMemory()

    @abstractmethod
    def arrive(self, block_id: int, tick: int = 0) -> bool:
        """
        Block 尝试到达栅栏。
        :param tick: 当前时钟
        :return: 是否触发了释放
        """
        pass

    @abstractmethod
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        pass

    @abstractmethod
    def is_full(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        pass
    
    def reset_released_flag(self):
        self.released = False

    # ── 模拟 GPU 原子指令 (Simulated Atomic Instructions) ──────────────
    # 虽然仿真器底层基于 Python 的串行事件处理机制，但在逻辑模型上，
    # 这些方法严格对应 GPU 的硬件原子指令，确保了对共享变量（如计数器）
    # 的'读-改-写'操作具备不可分割性（Atomicity）。
    # 每次调用都会记录一次通信事件，用于统计通信开销。

    def sim_atomic_add(self, key: str, value: int = 1) -> int:
        """
        模拟 GPU atomicAdd 指令。
        
        对 global_memory[key] 执行原子加法，返回修改前的旧值。
        语义等价于 CUDA: old = atomicAdd(&global_memory[key], value);
        
        :param key:   global_memory 中的变量名（如 "counter"）
        :param value: 要累加的值（默认 +1）
        :return:      操作前的旧值（old value）
        """
        old_value = self.mem.read(key, 0)
        self.mem.write(key, old_value + value)
        # 记录一次全局内存原子访问通信
        if self.metrics:
            self.metrics.record_communication(1)
        return old_value

    def sim_atomic_exch(self, key: str, new_value: Any) -> Any:
        """
        模拟 GPU atomicExch 指令。
        
        将 global_memory[key] 的值替换为 new_value，返回修改前的旧值。
        语义等价于 CUDA: old = atomicExch(&global_memory[key], new_value);
        
        :param key:       global_memory 中的变量名（如 "sense"）
        :param new_value: 要写入的新值
        :return:          操作前的旧值（old value）
        """
        old_value = self.mem.read(key, 0)
        self.mem.write(key, new_value)
        # 记录一次全局内存原子访问通信
        if self.metrics:
            self.metrics.record_communication(1)
        return old_value
        
    def get_memory_state(self) -> Dict[str, Any]:
        return self.mem.get_snapshot()
    
    def get_metrics(self) -> Dict[str, Any]:
        if self.metrics:
            return self.metrics.get_statistics()
        return {}
