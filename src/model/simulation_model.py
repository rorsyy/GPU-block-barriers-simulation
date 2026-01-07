from enum import Enum, auto
from typing import List, Dict
from .block import Block
from .barrier import CentralizedBarrier, TreeBarrier, ButterflyBarrier
from .scheduler import Scheduler

class SimulationState(Enum):
    STOPPED = auto()    # 停止
    RUNNING = auto()    # 运行中
    PAUSED = auto()     # 暂停
    COMPLETED = auto()  # 完成

class SimulationModel:
    """
    仿真模型 (Simulation Model) 主类
    
    作为 Model 层的入口，聚合了 Scheduler, Block, Barrier 等对象。
    负责管理仿真的全局生命周期状态 (State) 和当前时钟 (Tick)。
    """
    def __init__(self, logger=None):
        self.state = SimulationState.STOPPED
        self.current_tick = 0
        self.blocks: List[Block] = []
        self.barrier = None
        self.scheduler = None
        self.logger = logger
    
    def init_simulation(self, config: dict):
        """
        根据配置初始化仿真环境。
        """
        settings = config.get("settings", {})
        num_blocks = settings.get("num_blocks", 8)
        max_work = settings.get("max_ticks", 10000)
        barrier_interval = settings.get("barrier_interval", 100) 
        barrier_type = settings.get("barrier_type", "CENTRALIZED").upper()

        # 初始化全局栅栏
        if barrier_type == "TREE":
             self.barrier = TreeBarrier(limit=num_blocks, logger=self.logger)
        elif barrier_type == "BUTTERFLY":
             self.barrier = ButterflyBarrier(limit=num_blocks, logger=self.logger)
        else:
             self.barrier = CentralizedBarrier(limit=num_blocks, logger=self.logger)
        
        # 初始化 Blocks
        # Get behavior profile settings
        behavior = config.get("behavior_profile", {})
        workload_variance = behavior.get("workload_variance", 0.0)

        self.blocks = []
        for i in range(num_blocks):
            # Create Block with variance
            block = Block(
                block_id=i, 
                total_work_ticks=max_work, 
                barrier=self.barrier, 
                logger=self.logger,
                workload_variance=workload_variance
            )
            self.blocks.append(block)
            
        # 初始化调度器
        self.scheduler = Scheduler(self.blocks, barrier_interval=barrier_interval, logger=self.logger)
        
        self.state = SimulationState.STOPPED
        self.current_tick = 0
        
        if self.logger:
            self.logger.log_event("INIT", {"num_blocks": num_blocks, "interval": barrier_interval, "type": barrier_type})

    def start(self):
        """开始仿真"""
        self.state = SimulationState.RUNNING
        if self.logger:
            self.logger.log_event("CMD_START", {})

    def pause(self):
        """暂停仿真"""
        self.state = SimulationState.PAUSED
        if self.logger:
            self.logger.log_event("CMD_PAUSE", {})

    def step(self):
        """
        执行单步仿真。
        只有在 RUNNING 状态下才有效。
        """
        if self.state != SimulationState.RUNNING:
            return

        self.current_tick += 1
        self.scheduler.schedule_tick()
        
        # 检查是否所有 Block 都已完成
        all_finished = all(b.state.name == "FINISHED" for b in self.blocks)
        if all_finished:
            self.state = SimulationState.COMPLETED
            if self.logger:
                self.logger.log_event("SIMULATION_COMPLETE", {"total_ticks": self.current_tick})

    def get_snapshot(self) -> dict:
        """
        获取当前帧的完整状态快照，用于前端/View层渲染。
        """
        return {
            "tick": self.current_tick,
            "simulation_state": self.state.name,
            "blocks": [b.get_status() for b in self.blocks],
            "barrier": self.barrier.get_status() if self.barrier else {}
        }
