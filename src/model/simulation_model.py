from enum import Enum, auto
from typing import List, Dict
from .block import Block, BlockState
from .barriers.centralized_barrier import CentralizedBarrier
from .barriers.tree_barrier import TreeBarrier
from .barriers.static_tree_barrier import StaticTreeBarrier
from .schedulers.scheduler import Scheduler
from .event_bus import EventBus, EventType, create_barrier_release_event

class SimulationState(Enum):
    STOPPED = auto()    # 停止
    RUNNING = auto()    # 运行中
    PAUSED = auto()     # 暂停
    COMPLETED = auto()  # 完成

class SimulationModel:
    """
    仿真模型 (Simulation Model) 主类
    """
    def __init__(self, logger=None):
        self.state = SimulationState.STOPPED
        self.current_tick = 0
        self.blocks: List[Block] = []
        self.barrier = None
        self.scheduler = None
        self.logger = logger
        self.event_bus = None
    
    def init_simulation(self, config: dict):
        self.event_bus = EventBus(logger=self.logger)
        
        settings = config.get("settings", {})
        num_blocks = settings.get("num_blocks", 8)
        max_work = settings.get("max_ticks", 10000)
        barrier_interval = settings.get("barrier_interval", 100) 
        barrier_type = settings.get("barrier_type", "CENTRALIZED").upper()
        simulation_mode = settings.get("simulation_mode", "NORMAL").upper()  # NEW

        barrier_type_upper = barrier_type.upper()
        
        if barrier_type_upper == "TREE":
            self.barrier = TreeBarrier(limit=num_blocks, logger=self.logger)
        elif barrier_type_upper == "STATIC_TREE" or barrier_type_upper == "STATIC":
            self.barrier = StaticTreeBarrier(limit=num_blocks, logger=self.logger)
        else:
            self.barrier = CentralizedBarrier(limit=num_blocks, logger=self.logger)
        
        behavior = config.get("behavior_profile", {})
        workload_variance = settings.get("workload_variance", behavior.get("workload_variance", 0.2))
        failure_rate = behavior.get("failure_rate", 0.001)
        timeout_threshold = behavior.get("timeout_threshold", 500)

        self.blocks = []
        for i in range(num_blocks):
            block = Block(
                block_id=i, 
                total_work_ticks=max_work, 
                logger=self.logger,
                workload_variance=workload_variance
            )
            self.blocks.append(block)
            
        # 根据仿真模式选择调度器
        if simulation_mode == "FAILURE":
            from .schedulers.failure_scheduler import FailureScheduler
            self.scheduler = FailureScheduler(
                blocks=self.blocks,
                barrier_interval=barrier_interval,
                event_bus=self.event_bus,
                logger=self.logger,
                timeout_threshold=timeout_threshold,
                failure_rate=failure_rate
            )
        else:  # NORMAL or default
            from .schedulers.normal_scheduler import NormalScheduler
            self.scheduler = NormalScheduler(
                blocks=self.blocks,
                barrier_interval=barrier_interval,
                event_bus=self.event_bus,
                logger=self.logger
            )
        
        self.event_bus.subscribe(EventType.BARRIER_ARRIVAL, self.on_barrier_arrival)
        
        self.state = SimulationState.STOPPED
        self.current_tick = 0
        
        if self.logger:
            self.logger.log_event("INIT", {
                "num_blocks": num_blocks, 
                "interval": barrier_interval, 
                "type": barrier_type,
                "mode": simulation_mode  # 记录模式
            })

    def start(self):
        self.state = SimulationState.RUNNING
        if self.logger:
            self.logger.log_event("CMD_START", {})

    def pause(self):
        self.state = SimulationState.PAUSED
        if self.logger:
            self.logger.log_event("CMD_PAUSE", {})

    def step(self):
        if self.state != SimulationState.RUNNING:
            return

        self.current_tick += 1
        
        self.scheduler.schedule_tick(self.current_tick)
        
        active_blocks = [b for b in self.blocks if b.state in [BlockState.RUNNING, BlockState.WAITING_AT_BARRIER]]
        if not active_blocks:
            self.state = SimulationState.COMPLETED
            if self.logger:
                self.logger.log_event("SIMULATION_COMPLETE", {"total_ticks": self.current_tick})

    def on_barrier_arrival(self, event):
        block_id = event.data["block_id"]
        # Pass current tick to barrier
        should_release = self.barrier.arrive(block_id, self.current_tick)

        if should_release:
             release_event = create_barrier_release_event(self.current_tick, [], barrier_id="global")
             self.event_bus.publish(release_event)

    def get_snapshot(self) -> dict:
        snapshot = {
            "tick": self.current_tick,
            "simulation_state": self.state.name,
            "blocks": [b.get_status() for b in self.blocks],
            "barrier": self.barrier.get_status() if self.barrier else {}
        }
        
        if self.barrier and hasattr(self.barrier, 'get_metrics'):
            snapshot["metrics"] = self.barrier.get_metrics()
            
        if self.barrier and hasattr(self.barrier, 'get_memory_state'):
            snapshot["global_memory"] = self.barrier.get_memory_state()

        if self.barrier and hasattr(self.barrier, 'get_topology'):
            snapshot["topology"] = self.barrier.get_topology()
        
        return snapshot
    
    def get_barrier_metrics(self) -> Dict:
        if self.barrier and hasattr(self.barrier, 'get_metrics'):
            return self.barrier.get_metrics()
        return {}
