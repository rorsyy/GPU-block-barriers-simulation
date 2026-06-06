"""
正常模式调度器 (Normal Scheduler)

使用完全随机的工作负载，模拟真实的负载不均衡场景。
每次运行都会产生不同的结果。
"""

import random
from typing import List
from ..block import Block, BlockState
from ..event_bus import EventBus, EventType, create_barrier_arrival_event

class NormalScheduler:
    """
    正常模式调度器
    
    特点：
    - 完全随机工作量（每次运行都不同）
    - 无超时失联
    - 无健康检查
    - 由Block自身的workload_variance决定负载波动
    """
    
    def __init__(self, blocks: List[Block], barrier_interval: int, event_bus: EventBus, logger=None):
        self.blocks = blocks
        self.barrier_interval = barrier_interval
        self.event_bus = event_bus
        self.logger = logger
        
        self.assign_new_targets(current_tick=0)
        self.event_bus.subscribe(EventType.BARRIER_RELEASE, self.on_barrier_release)

    def assign_new_targets(self, current_tick: int):
        for block in self.blocks:
            if block.state in (BlockState.FINISHED, BlockState.FAILED):
                continue
            variance = block.workload_variance
            noise = random.uniform(-variance, variance)
            delay = int(self.barrier_interval * (1.0 + noise))
            delay = max(1, delay)
            block.set_phase_target(current_tick, current_tick + delay, self.barrier_interval)
    
    def schedule_tick(self, current_tick: int):
        for block in self.blocks:
            if block.state == BlockState.RUNNING:
                block.run_step(current_tick)
                if current_tick >= block.phase_target_tick:
                    block.set_waiting(current_tick)
                    event = create_barrier_arrival_event(current_tick, block.id)
                    self.event_bus.publish(event)
    
    def on_barrier_release(self, event):
        block_ids = event.data.get("block_ids", [])
        tick = event.tick
        
        if not block_ids:
            for block in self.blocks:
                if block.state == BlockState.WAITING_AT_BARRIER:
                    block.resume()
        else:
            target_ids = set(block_ids)
            for block in self.blocks:
                if block.id in target_ids and block.state == BlockState.WAITING_AT_BARRIER:
                    block.resume()
                    
        self.assign_new_targets(tick)
    
    def cleanup(self):
        self.event_bus.unsubscribe(EventType.BARRIER_RELEASE, self.on_barrier_release)
