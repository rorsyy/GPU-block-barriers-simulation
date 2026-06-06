import random
from ..block import Block, BlockState
from ..event_bus import EventBus, EventType, create_barrier_arrival_event, create_block_failure_event

class Scheduler:
    """
    调度器 (Scheduler) 类
    """
    def __init__(self, blocks: list[Block], barrier_interval: int, event_bus: EventBus, logger=None, failure_rate: float = 0.0, timeout_threshold: int = 2000):
        self.blocks = blocks
        self.barrier_interval = barrier_interval
        self.event_bus = event_bus
        self.logger = logger
        self.failure_rate = failure_rate
        self.timeout_threshold = timeout_threshold
        
        self.last_activity_tick = {b.id: 0 for b in self.blocks}
        self.health_check_interval = 100
        self.last_health_check = 0
        self.stall_threshold = 200
        
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
        if self.failure_rate > 0:
            for block in self.blocks:
                if block.state == BlockState.RUNNING and random.random() < self.failure_rate:
                     block.fail("Random simulated failure")
                     self.event_bus.publish(create_block_failure_event(current_tick, block.id, "Random Fault"))

        for block in self.blocks:
            if block.state == BlockState.RUNNING:
                old_progress = self.last_activity_tick.get(block.id, 0)
                block.run_step(current_tick)
                
                if block.current_work_ticks != old_progress:
                    self.last_activity_tick[block.id] = current_tick
                
                if current_tick >= block.phase_target_tick:
                    block.set_waiting(current_tick)
                    self.last_activity_tick[block.id] = current_tick
                    
                    event = create_barrier_arrival_event(current_tick, block.id)
                    self.event_bus.publish(event)
            
            elif block.state == BlockState.WAITING_AT_BARRIER:
                wait_duration = current_tick - block.wait_start_tick
                if wait_duration > self.timeout_threshold:
                    block.fail(f"Timeout waiting for barrier (> {self.timeout_threshold} ticks)")
                    self.event_bus.publish(create_block_failure_event(current_tick, block.id, "Timeout"))
        
        if current_tick - self.last_health_check >= self.health_check_interval:
            self._perform_health_check(current_tick)
            self.last_health_check = current_tick

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

    def _perform_health_check(self, current_tick: int):
        for block in self.blocks:
            if block.state in [BlockState.RUNNING, BlockState.WAITING_AT_BARRIER]:
                last_activity = self.last_activity_tick.get(block.id, 0)
                idle_duration = current_tick - last_activity
                
                if idle_duration > self.stall_threshold:
                    if self.logger:
                        self.logger.log_event("HEALTH_WARNING", {
                            "block_id": block.id,
                            "state": block.state.name,
                            "idle_ticks": idle_duration,
                            "reason": "Block appears stalled (no progress)"
                        })

    def cleanup(self):
        self.event_bus.unsubscribe(EventType.BARRIER_RELEASE, self.on_barrier_release)
