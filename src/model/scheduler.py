from .block import Block, BlockState
from .barrier import Barrier

class Scheduler:
    """
    调度器 (Scheduler) 类
    
    负责推进模拟的时钟 (Tick)，并调度所有 Block 的执行。
    在每个 Tick 中，遍历所有 Block，执行它们的 run_step，并检查是否需要同步。
    """
    def __init__(self, blocks: list[Block], barrier_interval: int, logger=None):
        """
        :param blocks: 受调度的 Block 列表
        :param barrier_interval: 简单的模拟参数，指每隔多少工作量触发一次栅栏（仅用于演示）
        :param logger: 日志记录器
        """
        self.blocks = blocks
        self.barrier_interval = barrier_interval
        self.logger = logger

    def schedule_tick(self):
        """
        推进一个时钟步 (Tick)。
        """
        # 1. 遍历更新所有 Block
        for block in self.blocks:
            # 首先检查 Block 是否感知到了由于其他 Block 到达而导致的栅栏释放 (Sense Reversal)
            # 这允许 Block 在检测到释放后，能够有机会在同一帧或下一帧恢复运行
            block.update_sense()

            # 如果 Block 处于运行状态，则执行具体逻辑
            if block.state == BlockState.RUNNING:
                block.run_step()
                
                # 检查是否需要触发同步 (Mock 逻辑)
                # 这里简单设定：当已完成的工作量整除 interval 时，尝试到达栅栏
                # 只有当 progress > 0 且发生了跨越倍数点的变化时才触发
                # 为了简化，我们假设 current_work_ticks 是浮点数模拟进度，
                # 我们取整判断是否达到了新的同步点
                
                # 注意：为了避免浮点数多次触发同一个整数点，通常需要记录 "last_synced_tick"
                # 但这里为了演示简化，我们假设 interval 是比较大的步长
                if int(block.current_work_ticks) > 0 and \
                   int(block.current_work_ticks) % self.barrier_interval == 0:
                     
                     # 简单的防抖动逻辑：如果当前正正好在 interval 点上，调用 arrive
                     # 实际代码可能需要更复杂的指令流模拟
                     block.arrive_at_barrier()

        # 2. 死锁检测 (可选/高级)
        self._detect_deadlock()

    def _detect_deadlock(self):
        """
        检测潜在的死锁或挂起状态。
        如果所有 Block 都在等待栅栏，但栅栏未满（count < limit），且持续了很长时间，可能发生了死锁。
        (简化起见，这里只检测全员等待但未释放的情况)
        """
        blocks_at_barrier = [b for b in self.blocks if b.state == BlockState.WAITING_AT_BARRIER]
        
        # 简单判定：所有 Block 都到了，但栅栏没有触发释放（可能是 barrier 逻辑错误，或 failed to arrive）
        # 正常情况下，最后一个 Block 到达后会瞬间触发释放，所以不应该观察到所有 Block 同时处于 WAITING 状态且 Barrier 未释放
        # 注意：Barrier.check_release 是由 Block 主动调用的，
        # 如果 Barrier 内部 count == limit，那么 state 应该在 Block.update_sense 后翻转。
        
        # 获取 Barrier 状态 (需要 Barrier 提供一些 getter)
        # 这里假设 Barrier 有 is_full() 方法或者我们可以推断
        # 更为了解耦，我们只看 Block 状态：
        
        if len(blocks_at_barrier) == len(self.blocks):
            # 所有 Block 都在等待
            # 如果此时 tick 还在走，且 barrier 没有释放的迹象，说明卡住了
            # 真实 GPU 中可能有更复杂的情况，这里做个简单 Log
            if self.logger:
                # 为了防止每帧都刷屏，可以加个 flag 或计数器，这里仅做一次性演示
                self.logger.log_event("WARNING_POTENTIAL_DEADLOCK", {
                    "waiting_count": len(blocks_at_barrier),
                    "total_blocks": len(self.blocks)
                })
