"""
接口测试 (Interface Tests)

验证 Model 层各模块之间的交互接口是否按设计规范工作。
重点测试模块边界处的数据传递、事件路由、回调触发等跨组件协作行为。

测试覆盖：
  1. EventBus ↔ 订阅者   — 事件发布后回调是否被正确路由
  2. Scheduler → Block    — 调度器是否正确驱动 Block 状态转换
  3. Scheduler ↔ EventBus — 调度器是否正确发布到达事件、响应释放事件
  4. Barrier ↔ Metrics    — 栅栏操作是否正确触发指标采集
  5. SimulationModel.on_barrier_arrival — 到达事件回调是否正确调用 barrier.arrive
"""

import sys
import os
import unittest
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from model.event_bus import EventBus, EventType, Event, create_barrier_release_event
from model.block import Block, BlockState
from model.barrier_metrics import BarrierMetrics
from model.barriers.centralized_barrier import CentralizedBarrier
from model.barriers.tree_barrier import TreeBarrier
from model.barriers.static_tree_barrier import StaticTreeBarrier
from model.schedulers.normal_scheduler import NormalScheduler
from model.schedulers.failure_scheduler import FailureScheduler
from model.simulation_model import SimulationModel, SimulationState


# ═══════════════════════════════════════════════════════════════════════
#  1. EventBus ↔ 订阅者 接口测试
# ═══════════════════════════════════════════════════════════════════════

class TestEventBusRouting(unittest.TestCase):
    """事件总线的跨模块路由机制测试"""

    def test_arrival_event_routed_to_model_callback(self):
        """BARRIER_ARRIVAL 事件应被正确路由到 SimulationModel 的回调"""
        bus = EventBus()
        arrived_ids = []

        def mock_on_arrival(event):
            arrived_ids.append(event.data["block_id"])

        bus.subscribe(EventType.BARRIER_ARRIVAL, mock_on_arrival)
        bus.publish(Event(EventType.BARRIER_ARRIVAL, tick=10, data={"block_id": 3, "barrier_id": "global"}))
        self.assertEqual(arrived_ids, [3])

    def test_release_event_routed_to_scheduler_callback(self):
        """BARRIER_RELEASE 事件应被路由到 Scheduler 的 on_barrier_release"""
        bus = EventBus()
        release_ticks = []

        def mock_on_release(event):
            release_ticks.append(event.tick)

        bus.subscribe(EventType.BARRIER_RELEASE, mock_on_release)
        bus.publish(create_barrier_release_event(tick=50, block_ids=[0, 1]))
        self.assertEqual(release_ticks, [50])

    def test_publish_during_callback_safe(self):
        """在回调中发布新事件不应导致异常（安全性验证）"""
        bus = EventBus()
        secondary_received = []

        def on_arrival(event):
            # 在回调中发布另一个事件
            bus.publish(Event(EventType.TICK_UPDATE, tick=event.tick, data={}))

        def on_tick(event):
            secondary_received.append(event.tick)

        bus.subscribe(EventType.BARRIER_ARRIVAL, on_arrival)
        bus.subscribe(EventType.TICK_UPDATE, on_tick)
        bus.publish(Event(EventType.BARRIER_ARRIVAL, tick=10, data={"block_id": 0}))
        self.assertEqual(secondary_received, [10])


# ═══════════════════════════════════════════════════════════════════════
#  2. NormalScheduler → Block 接口测试
# ═══════════════════════════════════════════════════════════════════════

class TestSchedulerBlockInterface(unittest.TestCase):
    """调度器与线程块之间的驱动接口测试"""

    def setUp(self):
        random.seed(42)
        self.bus = EventBus()
        self.blocks = [Block(i, total_work_ticks=10000, workload_variance=0.0) for i in range(4)]
        self.scheduler = NormalScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.bus,
        )

    def test_assign_targets_sets_phase_target(self):
        """assign_new_targets 应为每个 Block 设置 phase_target_tick"""
        for block in self.blocks:
            self.assertGreater(block.phase_target_tick, 0)

    def test_schedule_tick_drives_block_progress(self):
        """schedule_tick 应驱动 RUNNING 状态的 Block 推进进度"""
        self.scheduler.schedule_tick(1)
        for block in self.blocks:
            # Block 应已开始工作
            self.assertEqual(block.state, BlockState.RUNNING)

    def test_block_enters_waiting_at_target_tick(self):
        """Block 到达 phase_target_tick 时应进入 WAITING_AT_BARRIER"""
        target = self.blocks[0].phase_target_tick
        for tick in range(1, target + 1):
            self.scheduler.schedule_tick(tick)
        self.assertEqual(self.blocks[0].state, BlockState.WAITING_AT_BARRIER)

    def test_arrival_event_published_on_waiting(self):
        """Block 进入等待时应通过 EventBus 发布 BARRIER_ARRIVAL"""
        arrivals = []
        self.bus.subscribe(EventType.BARRIER_ARRIVAL, lambda e: arrivals.append(e))
        target = max(b.phase_target_tick for b in self.blocks)
        for tick in range(1, target + 1):
            self.scheduler.schedule_tick(tick)
        self.assertGreater(len(arrivals), 0)


# ═══════════════════════════════════════════════════════════════════════
#  3. Scheduler ↔ EventBus 释放响应接口测试
# ═══════════════════════════════════════════════════════════════════════

class TestSchedulerReleaseInterface(unittest.TestCase):
    """调度器对栅栏释放事件的响应接口测试"""

    def setUp(self):
        random.seed(42)
        self.bus = EventBus()
        self.blocks = [Block(i, total_work_ticks=10000, workload_variance=0.0) for i in range(4)]
        self.scheduler = NormalScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.bus,
        )

    def test_release_event_resumes_waiting_blocks(self):
        """收到 BARRIER_RELEASE 后，所有 WAITING Block 应恢复 RUNNING"""
        for block in self.blocks:
            block.set_waiting(5)
        release_event = create_barrier_release_event(tick=10, block_ids=[])
        self.bus.publish(release_event)
        for block in self.blocks:
            self.assertEqual(block.state, BlockState.RUNNING)

    def test_release_event_reassigns_targets(self):
        """收到 BARRIER_RELEASE 后，Block 应获得新的 phase_target_tick"""
        for block in self.blocks:
            block.set_waiting(5)
        old_targets = [b.phase_target_tick for b in self.blocks]
        release_event = create_barrier_release_event(tick=10, block_ids=[])
        self.bus.publish(release_event)
        new_targets = [b.phase_target_tick for b in self.blocks]
        self.assertNotEqual(old_targets, new_targets)

    def test_release_with_specific_block_ids(self):
        """指定 block_ids 时，只有相应 Block 被恢复"""
        for block in self.blocks:
            block.set_waiting(5)
        release_event = create_barrier_release_event(tick=10, block_ids=[0, 2])
        self.bus.publish(release_event)
        self.assertEqual(self.blocks[0].state, BlockState.RUNNING)
        self.assertEqual(self.blocks[1].state, BlockState.WAITING_AT_BARRIER)
        self.assertEqual(self.blocks[2].state, BlockState.RUNNING)
        self.assertEqual(self.blocks[3].state, BlockState.WAITING_AT_BARRIER)

    def test_cleanup_unsubscribes(self):
        """cleanup 后 Scheduler 不应再响应释放事件"""
        self.scheduler.cleanup()
        for block in self.blocks:
            block.set_waiting(5)
        self.bus.publish(create_barrier_release_event(tick=10, block_ids=[]))
        # Block 应仍处于 WAITING（无人恢复）
        for block in self.blocks:
            self.assertEqual(block.state, BlockState.WAITING_AT_BARRIER)


# ═══════════════════════════════════════════════════════════════════════
#  4. FailureScheduler 故障接口测试
# ═══════════════════════════════════════════════════════════════════════

class TestFailureSchedulerInterface(unittest.TestCase):
    """失联模式调度器的故障注入与超时检测接口测试"""

    def setUp(self):
        random.seed(42)
        self.bus = EventBus()
        self.blocks = [Block(i, total_work_ticks=10000, workload_variance=0.0) for i in range(4)]

    def test_timeout_detection_fails_waiting_block(self):
        """等待超时的 Block 应被标记为 FAILED"""
        scheduler = FailureScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.bus,
            timeout_threshold=5,
            failure_rate=0.0,  # 关闭随机故障
        )
        # 手动将 Block 设为等待
        self.blocks[0].set_waiting(current_tick=0)
        # 推进时钟超过超时阈值
        scheduler.schedule_tick(10)
        self.assertEqual(self.blocks[0].state, BlockState.FAILED)

    def test_failure_event_published_on_timeout(self):
        """超时时应发布 BLOCK_FAILURE 事件"""
        failures = []
        self.bus.subscribe(EventType.BLOCK_FAILURE, lambda e: failures.append(e))
        scheduler = FailureScheduler(
            blocks=self.blocks,
            barrier_interval=10,
            event_bus=self.bus,
            timeout_threshold=5,
            failure_rate=0.0,
        )
        self.blocks[0].set_waiting(current_tick=0)
        scheduler.schedule_tick(10)
        self.assertGreater(len(failures), 0)
        self.assertEqual(failures[0].data["block_id"], 0)

    def test_high_failure_rate_causes_failures(self):
        """高故障率下应有 Block 被注入故障"""
        scheduler = FailureScheduler(
            blocks=self.blocks,
            barrier_interval=100,
            event_bus=self.bus,
            timeout_threshold=10000,
            failure_rate=1.0,  # 100% 故障率
        )
        scheduler.schedule_tick(1)
        failed = [b for b in self.blocks if b.state == BlockState.FAILED]
        self.assertGreater(len(failed), 0)


# ═══════════════════════════════════════════════════════════════════════
#  5. Barrier ↔ BarrierMetrics 接口测试
# ═══════════════════════════════════════════════════════════════════════

class TestBarrierMetricsInterface(unittest.TestCase):
    """栅栏执行过程中指标采集接口的联动验证"""

    def test_centralized_arrive_records_metrics(self):
        """CentralizedBarrier.arrive 应触发 metrics 记录"""
        barrier = CentralizedBarrier(limit=3)
        barrier.arrive(0, tick=10)
        state = barrier.metrics.get_current_state()
        self.assertEqual(state["arrived_count"], 1)

    def test_centralized_release_records_sync_count(self):
        """完成一次同步后 sync_count 应 +1"""
        barrier = CentralizedBarrier(limit=3)
        for i in range(3):
            barrier.arrive(i, tick=10)
        stats = barrier.metrics.get_statistics()
        self.assertEqual(stats["sync_count"], 1)

    def test_centralized_communication_counted(self):
        """原子操作次数应被正确统计"""
        barrier = CentralizedBarrier(limit=3)
        for i in range(3):
            barrier.arrive(i, tick=10)
        stats = barrier.metrics.get_statistics()
        # arrive(atomicAdd) × 3 + release(atomicExch × 2) = 5
        self.assertGreaterEqual(stats["total_communication"], 5)

    def test_tree_barrier_communication_includes_propagation(self):
        """TreeBarrier 的通信统计应包含树传播开销"""
        barrier = TreeBarrier(limit=4)
        for i in range(4):
            barrier.arrive(i, tick=10)
        stats = barrier.metrics.get_statistics()
        # 树形传播的通信次数应大于集中式
        self.assertGreater(stats["total_communication"], 4)

    def test_static_tree_barrier_communication_includes_propagation(self):
        """StaticTreeBarrier 的通信统计同样应包含树传播开销"""
        barrier = StaticTreeBarrier(limit=4)
        for i in range(4):
            barrier.arrive(i, tick=10)
        stats = barrier.metrics.get_statistics()
        self.assertGreater(stats["total_communication"], 4)


# ═══════════════════════════════════════════════════════════════════════
#  6. SimulationModel.on_barrier_arrival 接口测试
# ═══════════════════════════════════════════════════════════════════════

class TestModelBarrierArrivalInterface(unittest.TestCase):
    """仿真模型对到达事件回调的接口验证"""

    def _make_model(self, barrier_type="CENTRALIZED", num_blocks=3):
        model = SimulationModel()
        model.init_simulation({
            "settings": {
                "num_blocks": num_blocks,
                "barrier_type": barrier_type,
                "barrier_interval": 10,
                "workload_variance": 0.0,
            }
        })
        return model

    def test_arrival_callback_triggers_barrier_arrive(self):
        """on_barrier_arrival 应调用 barrier.arrive()"""
        model = self._make_model(num_blocks=3)
        event = Event(EventType.BARRIER_ARRIVAL, tick=10, data={"block_id": 0, "barrier_id": "global"})
        model.on_barrier_arrival(event)
        self.assertEqual(model.barrier.count, 1)

    def test_full_arrival_publishes_release_event(self):
        """所有 Block 到达后应通过 EventBus 发布 BARRIER_RELEASE"""
        model = self._make_model(num_blocks=3)
        releases = []
        model.event_bus.subscribe(EventType.BARRIER_RELEASE, lambda e: releases.append(e))
        for i in range(3):
            event = Event(EventType.BARRIER_ARRIVAL, tick=10, data={"block_id": i, "barrier_id": "global"})
            model.on_barrier_arrival(event)
        self.assertEqual(len(releases), 1)

    def test_tree_barrier_arrival_interface(self):
        """TreeBarrier 模式下 on_barrier_arrival 同样应正常工作"""
        model = self._make_model(barrier_type="TREE", num_blocks=4)
        releases = []
        model.event_bus.subscribe(EventType.BARRIER_RELEASE, lambda e: releases.append(e))
        for i in range(4):
            event = Event(EventType.BARRIER_ARRIVAL, tick=10, data={"block_id": i, "barrier_id": "global"})
            model.on_barrier_arrival(event)
        self.assertEqual(len(releases), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
