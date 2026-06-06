"""
单元测试 (Unit Tests)

针对 Model 层各核心模块的最小可测试单元进行独立验证。
每个测试用例只关注单个类/方法的内部逻辑正确性，外部依赖通过构造最小上下文提供。

测试覆盖：
  1. EventBus      — 发布-订阅机制、历史记录管理、异常隔离
  2. Block          — 状态机转换、进度计算、边界条件
  3. BarrierMetrics — 指标采集生命周期、统计计算
  4. Barrier 基类   — 原子指令模拟 (sim_atomic_add / sim_atomic_exch)
  5. CentralizedBarrier — 集中式到达-释放逻辑
  6. TreeBarrier        — 树构建与分层传播
  7. StaticTreeBarrier  — 数组索引树构建与传播
"""

import sys
import os
import unittest
import random

# 将 src 目录加入搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from model.event_bus import EventBus, EventType, Event
from model.event_bus import (
    create_barrier_arrival_event,
    create_barrier_release_event,
    create_block_failure_event,
    create_tick_update_event,
)
from model.block import Block, BlockState
from model.barrier_metrics import BarrierMetrics
from model.barrier import Barrier
from model.barriers.centralized_barrier import CentralizedBarrier
from model.barriers.tree_barrier import TreeBarrier
from model.barriers.static_tree_barrier import StaticTreeBarrier


# ═══════════════════════════════════════════════════════════════════════
#  1. EventBus 单元测试
# ═══════════════════════════════════════════════════════════════════════

class TestEventBus(unittest.TestCase):
    """事件总线核心机制测试"""

    def setUp(self):
        self.bus = EventBus()

    # ── 发布-订阅 ──
    def test_subscribe_and_publish(self):
        """订阅后发布事件，回调应被正确调用"""
        received = []
        self.bus.subscribe(EventType.TICK_UPDATE, lambda e: received.append(e))
        event = Event(EventType.TICK_UPDATE, tick=1, data={})
        self.bus.publish(event)
        self.assertEqual(len(received), 1)
        self.assertIs(received[0], event)

    def test_unsubscribe(self):
        """取消订阅后不应再收到事件"""
        received = []
        callback = lambda e: received.append(e)
        self.bus.subscribe(EventType.TICK_UPDATE, callback)
        self.bus.unsubscribe(EventType.TICK_UPDATE, callback)
        self.bus.publish(Event(EventType.TICK_UPDATE, tick=1, data={}))
        self.assertEqual(len(received), 0)

    def test_multiple_subscribers(self):
        """同一事件类型可有多个订阅者，均应收到通知"""
        results = {"a": 0, "b": 0}
        self.bus.subscribe(EventType.BARRIER_ARRIVAL, lambda e: results.update(a=results["a"] + 1))
        self.bus.subscribe(EventType.BARRIER_ARRIVAL, lambda e: results.update(b=results["b"] + 1))
        self.bus.publish(Event(EventType.BARRIER_ARRIVAL, tick=0, data={}))
        self.assertEqual(results["a"], 1)
        self.assertEqual(results["b"], 1)

    def test_no_cross_type_delivery(self):
        """不同事件类型之间不应交叉投递"""
        received = []
        self.bus.subscribe(EventType.BARRIER_ARRIVAL, lambda e: received.append(e))
        self.bus.publish(Event(EventType.BARRIER_RELEASE, tick=0, data={}))
        self.assertEqual(len(received), 0)

    # ── 异常隔离 ──
    def test_callback_exception_isolation(self):
        """单个回调抛异常不应影响其他订阅者"""
        results = []
        self.bus.subscribe(EventType.TICK_UPDATE, lambda e: (_ for _ in ()).throw(RuntimeError("boom")))
        self.bus.subscribe(EventType.TICK_UPDATE, lambda e: results.append("ok"))
        self.bus.publish(Event(EventType.TICK_UPDATE, tick=0, data={}))
        self.assertEqual(results, ["ok"])

    # ── 历史记录 ──
    def test_event_history_recorded(self):
        """发布的事件应被记录到历史"""
        self.bus.publish(Event(EventType.TICK_UPDATE, tick=1, data={}))
        self.bus.publish(Event(EventType.TICK_UPDATE, tick=2, data={}))
        history = self.bus.get_event_history()
        self.assertEqual(len(history), 2)

    def test_event_history_limit(self):
        """历史记录超过 1000 条时应 FIFO 淘汰"""
        for i in range(1050):
            self.bus.publish(Event(EventType.TICK_UPDATE, tick=i, data={}))
        history = self.bus.get_event_history(limit=2000)
        self.assertLessEqual(len(history), 1000)

    def test_event_history_filter_by_type(self):
        """按类型筛选历史记录"""
        self.bus.publish(Event(EventType.TICK_UPDATE, tick=1, data={}))
        self.bus.publish(Event(EventType.BARRIER_ARRIVAL, tick=2, data={}))
        arrivals = self.bus.get_event_history(event_type=EventType.BARRIER_ARRIVAL)
        self.assertEqual(len(arrivals), 1)
        self.assertEqual(arrivals[0].tick, 2)

    def test_clear_history(self):
        """清空历史后应为空"""
        self.bus.publish(Event(EventType.TICK_UPDATE, tick=1, data={}))
        self.bus.clear_history()
        self.assertEqual(len(self.bus.get_event_history()), 0)

    # ── 工厂函数 ──
    def test_factory_barrier_arrival(self):
        """工厂函数应正确构造 BARRIER_ARRIVAL 事件"""
        e = create_barrier_arrival_event(tick=10, block_id=3)
        self.assertEqual(e.event_type, EventType.BARRIER_ARRIVAL)
        self.assertEqual(e.tick, 10)
        self.assertEqual(e.data["block_id"], 3)

    def test_factory_barrier_release(self):
        e = create_barrier_release_event(tick=20, block_ids=[0, 1, 2])
        self.assertEqual(e.event_type, EventType.BARRIER_RELEASE)
        self.assertEqual(e.data["block_ids"], [0, 1, 2])

    def test_factory_block_failure(self):
        e = create_block_failure_event(tick=5, block_id=1, reason="timeout")
        self.assertEqual(e.event_type, EventType.BLOCK_FAILURE)
        self.assertEqual(e.data["reason"], "timeout")

    def test_factory_tick_update(self):
        e = create_tick_update_event(tick=99)
        self.assertEqual(e.event_type, EventType.TICK_UPDATE)
        self.assertEqual(e.tick, 99)


# ═══════════════════════════════════════════════════════════════════════
#  2. Block 单元测试
# ═══════════════════════════════════════════════════════════════════════

class TestBlock(unittest.TestCase):
    """线程块状态机与进度计算测试"""

    def setUp(self):
        self.block = Block(block_id=0, total_work_ticks=100)

    # ── 初始状态 ──
    def test_initial_state_is_running(self):
        self.assertEqual(self.block.state, BlockState.RUNNING)

    def test_initial_progress_is_zero(self):
        self.assertAlmostEqual(self.block.get_progress(), 0.0)

    # ── 进度计算 (run_step) ──
    def test_run_step_advances_progress(self):
        """设置阶段目标后 run_step 应推进工作进度"""
        self.block.set_phase_target(0, 50, 50)
        self.block.run_step(25)
        self.assertGreater(self.block.current_work_ticks, 0)

    def test_run_step_linear_interpolation(self):
        """进度应按线性插值计算"""
        self.block.set_phase_target(0, 100, 100)
        self.block.run_step(50)
        self.assertAlmostEqual(self.block.current_work_ticks, 50.0)

    def test_run_step_clamp_at_boundary(self):
        """进度比率应被钳制在 [0, 1]"""
        self.block.set_phase_target(0, 10, 10)
        self.block.run_step(20)  # 超出 target
        self.assertLessEqual(self.block.current_work_ticks, self.block.total_work_ticks)

    # ── 状态转换 ──
    def test_set_waiting_from_running(self):
        """RUNNING → WAITING_AT_BARRIER"""
        self.block.set_waiting(10)
        self.assertEqual(self.block.state, BlockState.WAITING_AT_BARRIER)
        self.assertEqual(self.block.wait_start_tick, 10)

    def test_set_waiting_only_from_running(self):
        """非 RUNNING 状态下 set_waiting 无效"""
        self.block.state = BlockState.FINISHED
        self.block.set_waiting(10)
        self.assertEqual(self.block.state, BlockState.FINISHED)

    def test_resume_from_waiting(self):
        """WAITING_AT_BARRIER → RUNNING"""
        self.block.set_waiting(10)
        self.block.resume(new_sense=True)
        self.assertEqual(self.block.state, BlockState.RUNNING)
        self.assertTrue(self.block.local_sense)

    def test_resume_only_from_waiting(self):
        """非 WAITING 状态下 resume 无效"""
        self.block.resume()
        self.assertEqual(self.block.state, BlockState.RUNNING)

    def test_fail_sets_failed_state(self):
        """fail() 应将状态设置为 FAILED"""
        self.block.fail("test failure")
        self.assertEqual(self.block.state, BlockState.FAILED)

    def test_run_step_returns_false_when_finished(self):
        """FINISHED 状态下 run_step 返回 False"""
        self.block.state = BlockState.FINISHED
        self.assertFalse(self.block.run_step(10))

    def test_run_step_returns_false_when_failed(self):
        """FAILED 状态下 run_step 返回 False"""
        self.block.fail("test")
        self.assertFalse(self.block.run_step(10))

    def test_finished_when_work_exhausted(self):
        """工作量耗尽时应自动转入 FINISHED"""
        self.block = Block(block_id=0, total_work_ticks=10)
        self.block.set_phase_target(0, 10, 10)
        self.block.run_step(10)
        self.assertEqual(self.block.state, BlockState.FINISHED)

    # ── get_status ──
    def test_get_status_dict_keys(self):
        """get_status 应包含规定的字段"""
        status = self.block.get_status()
        for key in ["id", "state", "progress", "work_done", "at_barrier"]:
            self.assertIn(key, status)


# ═══════════════════════════════════════════════════════════════════════
#  3. BarrierMetrics 单元测试
# ═══════════════════════════════════════════════════════════════════════

class TestBarrierMetrics(unittest.TestCase):
    """栅栏性能指标收集器测试"""

    def setUp(self):
        self.metrics = BarrierMetrics("TestBarrier")

    def test_initial_sync_count_is_zero(self):
        self.assertEqual(self.metrics.sync_count, 0)

    def test_record_arrival_updates_ticks(self):
        """记录到达应更新首次和最后到达时间"""
        self.metrics.record_arrival(0, tick=10)
        self.assertEqual(self.metrics._current_first_arrival_tick, 10)
        self.assertEqual(self.metrics._current_last_arrival_tick, 10)
        self.metrics.record_arrival(1, tick=15)
        self.assertEqual(self.metrics._current_first_arrival_tick, 10)
        self.assertEqual(self.metrics._current_last_arrival_tick, 15)

    def test_record_communication_accumulates(self):
        """通信计数应逐次累加"""
        self.metrics.record_communication(3)
        self.metrics.record_communication(2)
        self.assertEqual(self.metrics._current_communication, 5)

    def test_record_release_finalizes_cycle(self):
        """record_release 应完成同步周期并重置临时数据"""
        self.metrics.record_arrival(0, tick=10)
        self.metrics.record_communication(5)
        self.metrics.record_release(release_tick=10)
        self.assertEqual(self.metrics.sync_count, 1)
        self.assertEqual(self.metrics.total_communication, 5)
        # 临时数据已重置
        self.assertIsNone(self.metrics._current_first_arrival_tick)
        self.assertEqual(self.metrics._current_communication, 0)

    def test_get_statistics_structure(self):
        """统计输出应包含规定字段"""
        stats = self.metrics.get_statistics()
        for key in ["barrier_type", "sync_count", "avg_communication", "total_communication"]:
            self.assertIn(key, stats)

    def test_avg_communication_calculation(self):
        """平均通信开销应正确计算"""
        for i in range(3):
            self.metrics.record_arrival(i, tick=i * 10)
            self.metrics.record_communication(6)
            self.metrics.record_release(release_tick=i * 10)
        stats = self.metrics.get_statistics()
        self.assertAlmostEqual(stats["avg_communication"], 6.0)

    def test_reset_clears_all_data(self):
        """reset 应清空所有累积数据"""
        self.metrics.record_arrival(0, tick=5)
        self.metrics.record_communication(10)
        self.metrics.record_release(release_tick=5)
        self.metrics.reset()
        self.assertEqual(self.metrics.sync_count, 0)
        self.assertEqual(self.metrics.total_communication, 0)

    def test_negative_tick_ignored(self):
        """负值 tick 不应被记录"""
        self.metrics.record_arrival(0, tick=-1)
        self.assertIsNone(self.metrics._current_first_arrival_tick)


# ═══════════════════════════════════════════════════════════════════════
#  4. Barrier 基类原子指令测试
# ═══════════════════════════════════════════════════════════════════════

class TestBarrierAtomicInstructions(unittest.TestCase):
    """Barrier 基类的模拟原子指令测试（通过 CentralizedBarrier 实例）"""

    def setUp(self):
        self.barrier = CentralizedBarrier(limit=4)

    def test_sim_atomic_add_returns_old_value(self):
        """atomicAdd 应返回修改前的旧值"""
        old = self.barrier.sim_atomic_add("counter", 1)
        self.assertEqual(old, 0)
        old = self.barrier.sim_atomic_add("counter", 1)
        self.assertEqual(old, 1)

    def test_sim_atomic_add_updates_memory(self):
        """atomicAdd 应正确更新全局内存"""
        self.barrier.sim_atomic_add("counter", 5)
        self.assertEqual(self.barrier.global_memory["counter"], 5)

    def test_sim_atomic_exch_returns_old_value(self):
        """atomicExch 应返回旧值"""
        self.barrier.global_memory["sense"] = 0
        old = self.barrier.sim_atomic_exch("sense", 1)
        self.assertEqual(old, 0)
        self.assertEqual(self.barrier.global_memory["sense"], 1)

    def test_atomic_operations_record_communication(self):
        """每次原子操作应触发一次通信记录"""
        initial_comm = self.barrier.metrics._current_communication
        self.barrier.sim_atomic_add("counter", 1)
        self.assertEqual(self.barrier.metrics._current_communication, initial_comm + 1)


# ═══════════════════════════════════════════════════════════════════════
#  5. CentralizedBarrier 单元测试
# ═══════════════════════════════════════════════════════════════════════

class TestCentralizedBarrier(unittest.TestCase):
    """集中式栅栏的到达-释放逻辑测试"""

    def setUp(self):
        self.barrier = CentralizedBarrier(limit=3)

    def test_arrive_increments_count(self):
        """每次 arrive 应增加计数"""
        self.barrier.arrive(0, tick=0)
        self.assertEqual(self.barrier.count, 1)

    def test_arrive_not_release_until_full(self):
        """未满时不应触发释放"""
        result = self.barrier.arrive(0, tick=0)
        self.assertFalse(result)
        self.assertFalse(self.barrier.released)

    def test_arrive_triggers_release_when_full(self):
        """所有 Block 到齐时应触发释放"""
        self.barrier.arrive(0, tick=0)
        self.barrier.arrive(1, tick=0)
        result = self.barrier.arrive(2, tick=0)
        self.assertTrue(result)
        self.assertTrue(self.barrier.released)

    def test_release_resets_counter(self):
        """释放后计数器应重置为 0"""
        for i in range(3):
            self.barrier.arrive(i, tick=0)
        self.assertEqual(self.barrier.count, 0)

    def test_release_flips_sense(self):
        """释放应翻转 sense 标志"""
        old_sense = self.barrier.sense
        for i in range(3):
            self.barrier.arrive(i, tick=0)
        self.assertNotEqual(self.barrier.sense, old_sense)

    def test_global_memory_reflects_state(self):
        """全局内存应反映栅栏的当前状态"""
        for i in range(3):
            self.barrier.arrive(i, tick=0)
        self.assertEqual(self.barrier.global_memory["counter"], 0)
        self.assertEqual(self.barrier.global_memory["sense"], int(self.barrier.sense))

    def test_get_status_structure(self):
        """get_status 应包含规定字段"""
        status = self.barrier.get_status()
        for key in ["type", "count", "limit", "sense", "is_released"]:
            self.assertIn(key, status)
        self.assertEqual(status["type"], "CENTRALIZED")

    def test_check_release_detects_sense_change(self):
        """check_release 应检测 sense 变化"""
        old_sense = self.barrier.sense
        for i in range(3):
            self.barrier.arrive(i, tick=0)
        released, new_sense = self.barrier.check_release(0, old_sense)
        self.assertTrue(released)


# ═══════════════════════════════════════════════════════════════════════
#  6. TreeBarrier 单元测试
# ═══════════════════════════════════════════════════════════════════════

class TestTreeBarrier(unittest.TestCase):
    """树形栅栏的构建与同步逻辑测试"""

    def setUp(self):
        self.barrier = TreeBarrier(limit=4)

    def test_tree_has_correct_leaf_count(self):
        """4 个 Block 应映射到叶子节点"""
        self.assertEqual(len(self.barrier.leaves), 4)

    def test_tree_has_root(self):
        """树应有根节点"""
        self.assertIsNotNone(self.barrier.root)

    def test_partial_arrival_no_release(self):
        """部分到达不应触发释放"""
        self.assertFalse(self.barrier.arrive(0, tick=0))
        self.assertFalse(self.barrier.arrive(1, tick=0))
        self.assertFalse(self.barrier.released)

    def test_full_arrival_triggers_release(self):
        """所有 Block 到齐应触发释放"""
        for i in range(4):
            result = self.barrier.arrive(i, tick=0)
        self.assertTrue(result)
        self.assertTrue(self.barrier.released)

    def test_sense_propagated_to_all_nodes(self):
        """释放后 sense 应通过树广播至所有节点"""
        for i in range(4):
            self.barrier.arrive(i, tick=0)
        root_sense = self.barrier.root.sense
        for node in self.barrier.nodes:
            self.assertEqual(node.sense, root_sense)

    def test_invalid_block_id_returns_false(self):
        """无效 block_id 的 arrive 应返回 False"""
        self.assertFalse(self.barrier.arrive(999, tick=0))

    def test_get_topology_structure(self):
        """get_topology 应包含 nodes 和 leaves"""
        topo = self.barrier.get_topology()
        self.assertIn("nodes", topo)
        self.assertIn("leaves", topo)

    def test_global_memory_snapshot_updated(self):
        """arrive 后全局内存快照应被更新"""
        self.barrier.arrive(0, tick=0)
        has_count_keys = any(".count" in k for k in self.barrier.global_memory)
        self.assertTrue(has_count_keys)


# ═══════════════════════════════════════════════════════════════════════
#  7. StaticTreeBarrier 单元测试
# ═══════════════════════════════════════════════════════════════════════

class TestStaticTreeBarrier(unittest.TestCase):
    """静态树栅栏的数组索引构建与同步逻辑测试"""

    def setUp(self):
        self.barrier = StaticTreeBarrier(limit=4)

    def test_correct_total_nodes(self):
        """4 个 Block 应生成 7 个节点 (2n-1)"""
        self.assertEqual(len(self.barrier.nodes), 7)

    def test_block_to_node_mapping(self):
        """所有 Block 应被映射到叶子节点"""
        self.assertEqual(len(self.barrier.block_to_node), 4)

    def test_parent_child_indexing(self):
        """父子关系应符合 (i-1)//2 数学公式"""
        for nid, node in self.barrier.nodes.items():
            if nid == 0:
                self.assertIsNone(node.parent_id)
            else:
                expected_parent = (nid - 1) // 2
                self.assertEqual(node.parent_id, expected_parent)

    def test_full_arrival_triggers_release(self):
        """所有 Block 到齐应触发释放"""
        for i in range(4):
            result = self.barrier.arrive(i, tick=0)
        self.assertTrue(result)
        self.assertTrue(self.barrier.released)

    def test_sense_propagated_after_release(self):
        """释放后 sense 应被广播至全部节点"""
        for i in range(4):
            self.barrier.arrive(i, tick=0)
        root_sense = self.barrier.nodes[0].sense
        for node in self.barrier.nodes.values():
            self.assertEqual(node.sense, root_sense)

    def test_invalid_block_id_returns_false(self):
        self.assertFalse(self.barrier.arrive(999, tick=0))

    def test_global_memory_keys_follow_naming(self):
        """全局内存键名应符合 'nodeN.count' / 'nodeN.sense' 格式"""
        for key in self.barrier.global_memory:
            self.assertRegex(key, r'^node\d+\.(count|sense)$')

    def test_get_topology_structure(self):
        topo = self.barrier.get_topology()
        self.assertIn("nodes", topo)
        self.assertIn("leaves", topo)


if __name__ == '__main__':
    unittest.main(verbosity=2)
