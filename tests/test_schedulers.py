"""
调度器单元测试

测试核心调度器模块的各个功能：
- NormalScheduler: 正常模式调度器
- FailureScheduler: 失联模式调度器
"""

import unittest
import sys
import os
from unittest.mock import MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.model.schedulers.normal_scheduler import NormalScheduler
from src.model.schedulers.failure_scheduler import FailureScheduler
from src.model.block import Block, BlockState
from src.model.event_bus import EventBus, EventType


class TestNormalScheduler(unittest.TestCase):
    """NormalScheduler 单元测试"""

    def setUp(self):
        """测试前准备"""
        self.event_bus = EventBus(logger=None)
        self.blocks = [
            Block(block_id=i, total_work_ticks=100, logger=None, workload_variance=0)
            for i in range(4)
        ]
        self.scheduler = NormalScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.event_bus,
            logger=None
        )

    def tearDown(self):
        """测试后清理"""
        if hasattr(self.scheduler, 'cleanup'):
            self.scheduler.cleanup()

    def test_initialization(self):
        """测试调度器初始化"""
        self.assertEqual(len(self.scheduler.blocks), 4)
        self.assertEqual(self.scheduler.barrier_interval, 10)
        self.assertIsNotNone(self.scheduler.event_bus)

    def test_assign_new_targets(self):
        """测试分配新目标"""
        current_tick = 0
        self.scheduler.assign_new_targets(current_tick)
        
        for block in self.blocks:
            self.assertGreater(block.phase_target_tick, current_tick)
            self.assertGreaterEqual(block.phase_target_tick, block.phase_start_tick)

    def test_schedule_tick_with_zero_variance(self):
        """测试零方差调度"""
        for block in self.blocks:
            block.workload_variance = 0
            block.set_phase_target(0, 0 + 10, 10)
        
        self.scheduler.schedule_tick(5)
        
        # 在 phase_target_tick 之前不应该等待
        for block in self.blocks:
            self.assertEqual(block.state, BlockState.RUNNING)

    def test_schedule_tick_reaches_target(self):
        """测试达到目标时进入等待"""
        for block in self.blocks:
            block.set_phase_target(0, 10, 10)
        
        self.scheduler.schedule_tick(10)
        
        # 至少一个块应该进入等待状态
        waiting_blocks = [b for b in self.blocks if b.state == BlockState.WAITING_AT_BARRIER]
        self.assertGreater(len(waiting_blocks), 0)

    def test_barrier_release_resumes_all(self):
        """测试栅栏释放恢复所有等待块"""
        # 让所有块进入等待
        for block in self.blocks:
            block.set_waiting(10)
        
        # 发布释放事件
        from src.model.event_bus import create_barrier_release_event
        event = create_barrier_release_event(tick=15, block_ids=[])
        self.scheduler.on_barrier_release(event)
        
        # 所有块应该恢复运行
        for block in self.blocks:
            self.assertEqual(block.state, BlockState.RUNNING)

    def test_barrier_release_with_specific_ids(self):
        """测试带特定ID的栅栏释放"""
        # 让部分块进入等待
        self.blocks[0].set_waiting(10)
        self.blocks[1].set_waiting(10)
        
        # 只释放 block 0
        from src.model.event_bus import create_barrier_release_event
        event = create_barrier_release_event(tick=15, block_ids=[0])
        self.scheduler.on_barrier_release(event)
        
        self.assertEqual(self.blocks[0].state, BlockState.RUNNING)
        self.assertEqual(self.blocks[1].state, BlockState.WAITING_AT_BARRIER)

    def test_finished_blocks_not_assigned(self):
        """测试完成的块不再分配新目标"""
        self.blocks[0].state = BlockState.FINISHED
        original_target = self.blocks[0].phase_target_tick
        
        self.scheduler.assign_new_targets(100)
        
        # 完成的块不应该改变目标
        self.assertEqual(self.blocks[0].phase_target_tick, original_target)

    def test_failed_blocks_not_assigned(self):
        """测试失败的块不再分配新目标"""
        self.blocks[0].state = BlockState.FAILED
        original_target = self.blocks[0].phase_target_tick
        
        self.scheduler.assign_new_targets(100)
        
        # 失败的块不应该改变目标
        self.assertEqual(self.blocks[0].phase_target_tick, original_target)


class TestFailureScheduler(unittest.TestCase):
    """FailureScheduler 单元测试"""

    def setUp(self):
        """测试前准备"""
        self.event_bus = EventBus(logger=None)
        self.blocks = [
            Block(block_id=i, total_work_ticks=100, logger=None, workload_variance=0)
            for i in range(4)
        ]
        self.scheduler = FailureScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.event_bus,
            logger=None,
            timeout_threshold=50,
            failure_rate=0.0  # 禁用随机失联以进行确定性测试
        )

    def tearDown(self):
        """测试后清理"""
        if hasattr(self.scheduler, 'cleanup'):
            self.scheduler.cleanup()

    def test_initialization_with_params(self):
        """测试带参数的初始化"""
        self.assertEqual(self.scheduler.timeout_threshold, 50)
        self.assertEqual(self.scheduler.failure_rate, 0.0)
        self.assertEqual(self.scheduler.stall_threshold, 200)

    def test_timeout_detection(self):
        """测试超时检测"""
        # 模拟块等待超时
        self.blocks[0].set_waiting(0)
        self.blocks[0].wait_start_tick = 0
        
        # 运行到超时
        self.scheduler.schedule_tick(60)
        
        # 块应该失败
        self.assertEqual(self.blocks[0].state, BlockState.FAILED)

    def test_no_timeout_within_threshold(self):
        """测试阈值内不触发超时"""
        self.blocks[0].set_waiting(10)
        
        # 在阈值内
        self.scheduler.schedule_tick(55)
        
        # 块不应失败
        self.assertNotEqual(self.blocks[0].state, BlockState.FAILED)

    def test_health_check_logging(self):
        """测试健康检查日志记录"""
        mock_logger = MagicMock()
        scheduler = FailureScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.event_bus,
            logger=mock_logger,
            timeout_threshold=500,
            failure_rate=0.0
        )
        
        # 设置块为停滞状态
        self.blocks[0].state = BlockState.RUNNING
        scheduler.last_activity_tick[0] = 0
        
        # 运行健康检查
        scheduler._perform_health_check(300)
        
        # 应该记录健康警告
        mock_logger.log_event.assert_called()
        call_args = mock_logger.log_event.call_args
        self.assertEqual(call_args[0][0], "HEALTH_WARNING")
        
        if hasattr(scheduler, 'cleanup'):
            scheduler.cleanup()

    def test_failure_event_published(self):
        """测试失败事件发布"""
        # 订阅失败事件
        failure_events = []
        def on_failure(event):
            failure_events.append(event)
        self.event_bus.subscribe(EventType.BLOCK_FAILURE, on_failure)
        
        # 模拟超时
        self.blocks[0].set_waiting(0)
        self.blocks[0].wait_start_tick = 0
        self.scheduler.schedule_tick(60)
        
        # 应该有失败事件
        self.assertEqual(len(failure_events), 1)
        self.assertEqual(failure_events[0].data['block_id'], 0)
        self.assertEqual(failure_events[0].data['reason'], "Timeout")

    def test_barrier_release_resumes_waiting(self):
        """测试栅栏释放恢复等待块"""
        for block in self.blocks:
            block.set_waiting(10)
        
        from src.model.event_bus import create_barrier_release_event
        event = create_barrier_release_event(tick=15, block_ids=[])
        self.scheduler.on_barrier_release(event)
        
        for block in self.blocks:
            self.assertEqual(block.state, BlockState.RUNNING)


class TestSchedulerIntegration(unittest.TestCase):
    """调度器集成测试"""

    def setUp(self):
        """测试前准备"""
        self.event_bus = EventBus(logger=None)

    def test_normal_scheduler_complete_cycle(self):
        """测试正常调度器完整周期"""
        blocks = [
            Block(block_id=i, total_work_ticks=100, logger=None, workload_variance=0)
            for i in range(3)
        ]
        scheduler = NormalScheduler(
            blocks=blocks,
            barrier_interval=5,
            event_bus=self.event_bus,
            logger=None
        )
        
        # 运行多个周期
        for tick in range(20):
            scheduler.schedule_tick(tick)
        
        # 验证调度器仍然可用
        self.assertEqual(len(scheduler.blocks), 3)
        
        if hasattr(scheduler, 'cleanup'):
            scheduler.cleanup()

    def test_event_bus_integration(self):
        """测试事件总线集成"""
        blocks = [Block(block_id=0, total_work_ticks=100, logger=None)]
        scheduler = NormalScheduler(
            blocks=blocks,
            barrier_interval=5,
            event_bus=self.event_bus,
            logger=None
        )
        
        arrival_events = []
        def on_arrival(event):
            arrival_events.append(event)
        self.event_bus.subscribe(EventType.BARRIER_ARRIVAL, on_arrival)
        
        blocks[0].set_phase_target(0, 5, 5)
        scheduler.schedule_tick(5)
        
        self.assertGreater(len(arrival_events), 0)
        
        if hasattr(scheduler, 'cleanup'):
            scheduler.cleanup()


if __name__ == '__main__':
    # 设置随机种子以确保测试可重复
    import random
    random.seed(42)
    
    # 运行测试
    unittest.main(verbosity=2)
