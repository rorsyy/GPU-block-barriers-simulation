"""
整体测试 (Integration Tests)

验证仿真系统从初始化到完成的端到端核心流程。
测试多个模块协同工作时，完整的仿真循环是否能正确运转。

测试覆盖：
  1. SimulationModel 初始化 — 三种栅栏 × 两种调度模式的正确创建
  2. 完整仿真循环         — 时钟推进 → Block 到达 → 栅栏释放 → Block 恢复
  3. 多轮同步测试         — 连续多个同步阶段的闭环验证
  4. 状态快照完整性       — get_snapshot 返回数据结构的正确性
  5. 三种算法一致性       — 相同规模下三种栅栏均能完成同步
"""

import sys
import os
import unittest
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from model.event_bus import EventType
from model.block import BlockState
from model.simulation_model import SimulationModel, SimulationState


# ═══════════════════════════════════════════════════════════════════════
#  辅助方法
# ═══════════════════════════════════════════════════════════════════════

def make_model(barrier_type="CENTRALIZED", simulation_mode="NORMAL",
               num_blocks=4, barrier_interval=10, workload_variance=0.0,
               failure_rate=0.0, timeout_threshold=500):
    """构建标准测试用的 SimulationModel 实例"""
    model = SimulationModel()
    model.init_simulation({
        "settings": {
            "num_blocks": num_blocks,
            "barrier_type": barrier_type,
            "barrier_interval": barrier_interval,
            "workload_variance": workload_variance,
            "simulation_mode": simulation_mode,
        },
        "behavior_profile": {
            "failure_rate": failure_rate,
            "timeout_threshold": timeout_threshold,
        }
    })
    return model


def run_until(model, max_ticks=500, stop_condition=None):
    """驱动仿真直到满足停止条件或达到最大 tick"""
    model.start()
    for tick in range(max_ticks):
        if model.state != SimulationState.RUNNING:
            break
        model.step()
        if stop_condition and stop_condition(model):
            break
    return model.current_tick


# ═══════════════════════════════════════════════════════════════════════
#  1. SimulationModel 初始化测试
# ═══════════════════════════════════════════════════════════════════════

class TestModelInitialization(unittest.TestCase):
    """仿真模型初始化的完整性验证"""

    def test_centralized_barrier_created(self):
        """CENTRALIZED 模式应创建 CentralizedBarrier"""
        model = make_model(barrier_type="CENTRALIZED")
        self.assertEqual(model.barrier.__class__.__name__, "CentralizedBarrier")

    def test_tree_barrier_created(self):
        """TREE 模式应创建 TreeBarrier"""
        model = make_model(barrier_type="TREE")
        self.assertEqual(model.barrier.__class__.__name__, "TreeBarrier")

    def test_static_tree_barrier_created(self):
        """STATIC_TREE 模式应创建 StaticTreeBarrier"""
        model = make_model(barrier_type="STATIC_TREE")
        self.assertEqual(model.barrier.__class__.__name__, "StaticTreeBarrier")

    def test_normal_scheduler_created(self):
        """NORMAL 模式应创建 NormalScheduler"""
        model = make_model(simulation_mode="NORMAL")
        self.assertEqual(model.scheduler.__class__.__name__, "NormalScheduler")

    def test_failure_scheduler_created(self):
        """FAILURE 模式应创建 FailureScheduler"""
        model = make_model(simulation_mode="FAILURE")
        self.assertEqual(model.scheduler.__class__.__name__, "FailureScheduler")

    def test_blocks_count_matches_config(self):
        """Block 数量应与配置一致"""
        model = make_model(num_blocks=8)
        self.assertEqual(len(model.blocks), 8)

    def test_event_bus_created(self):
        """EventBus 应被正确初始化"""
        model = make_model()
        self.assertIsNotNone(model.event_bus)

    def test_initial_state_is_stopped(self):
        """初始化后仿真状态应为 STOPPED"""
        model = make_model()
        self.assertEqual(model.state, SimulationState.STOPPED)

    def test_initial_tick_is_zero(self):
        """初始化后 tick 应为 0"""
        model = make_model()
        self.assertEqual(model.current_tick, 0)


# ═══════════════════════════════════════════════════════════════════════
#  2. 完整仿真循环测试（单轮同步）
# ═══════════════════════════════════════════════════════════════════════

class TestSingleSyncCycle(unittest.TestCase):
    """单轮同步的完整闭环验证"""

    def setUp(self):
        random.seed(42)

    def _run_single_sync(self, barrier_type):
        """执行单轮同步并返回模型"""
        model = make_model(
            barrier_type=barrier_type,
            num_blocks=4,
            barrier_interval=10,
            workload_variance=0.0,
        )
        model.start()

        # 运行足够 tick 使所有 Block 到达同步点并释放
        barrier_released = False
        for tick in range(1, 50):
            if model.state != SimulationState.RUNNING:
                break
            model.step()
            if model.barrier.released:
                barrier_released = True
                break

        return model, barrier_released

    def test_centralized_single_sync_completes(self):
        """集中式栅栏应能完成一轮同步"""
        model, released = self._run_single_sync("CENTRALIZED")
        self.assertTrue(released)

    def test_tree_single_sync_completes(self):
        """树形栅栏应能完成一轮同步"""
        model, released = self._run_single_sync("TREE")
        self.assertTrue(released)

    def test_static_tree_single_sync_completes(self):
        """静态树栅栏应能完成一轮同步"""
        model, released = self._run_single_sync("STATIC_TREE")
        self.assertTrue(released)

    def test_blocks_resume_after_release(self):
        """栅栏释放后 Block 应恢复为 RUNNING"""
        model, released = self._run_single_sync("CENTRALIZED")
        self.assertTrue(released)
        # 释放后再推进一步让 resume 生效
        if model.state == SimulationState.RUNNING:
            model.step()
        running_blocks = [b for b in model.blocks if b.state == BlockState.RUNNING]
        # 至少有部分 Block 恢复了 RUNNING
        self.assertGreater(len(running_blocks), 0)

    def test_metrics_recorded_after_sync(self):
        """完成一轮同步后 metrics.sync_count 应为 1"""
        model, released = self._run_single_sync("CENTRALIZED")
        self.assertTrue(released)
        stats = model.barrier.metrics.get_statistics()
        self.assertEqual(stats["sync_count"], 1)


# ═══════════════════════════════════════════════════════════════════════
#  3. 多轮同步测试
# ═══════════════════════════════════════════════════════════════════════

class TestMultiSyncCycles(unittest.TestCase):
    """连续多轮同步的闭环验证"""

    def setUp(self):
        random.seed(42)

    def test_centralized_multi_sync(self):
        """集中式栅栏应能完成至少 2 轮同步"""
        model = make_model(
            barrier_type="CENTRALIZED",
            num_blocks=4,
            barrier_interval=10,
            workload_variance=0.0,
        )
        run_until(model, max_ticks=200)
        stats = model.barrier.metrics.get_statistics()
        self.assertGreaterEqual(stats["sync_count"], 2)

    def test_tree_multi_sync(self):
        """树形栅栏应能完成至少 2 轮同步"""
        model = make_model(
            barrier_type="TREE",
            num_blocks=4,
            barrier_interval=10,
            workload_variance=0.0,
        )
        run_until(model, max_ticks=200)
        stats = model.barrier.metrics.get_statistics()
        self.assertGreaterEqual(stats["sync_count"], 2)

    def test_static_tree_multi_sync(self):
        """静态树栅栏应能完成至少 2 轮同步"""
        model = make_model(
            barrier_type="STATIC_TREE",
            num_blocks=4,
            barrier_interval=10,
            workload_variance=0.0,
        )
        run_until(model, max_ticks=200)
        stats = model.barrier.metrics.get_statistics()
        self.assertGreaterEqual(stats["sync_count"], 2)

    def test_tick_advances_correctly(self):
        """多轮同步过程中 tick 应持续递增"""
        model = make_model(num_blocks=4, barrier_interval=10)
        final_tick = run_until(model, max_ticks=100)
        self.assertGreater(final_tick, 0)


# ═══════════════════════════════════════════════════════════════════════
#  4. 状态快照完整性测试
# ═══════════════════════════════════════════════════════════════════════

class TestSnapshotIntegrity(unittest.TestCase):
    """get_snapshot 返回数据结构的完整性验证"""

    def setUp(self):
        random.seed(42)

    def _get_snapshot_after_run(self, barrier_type="CENTRALIZED"):
        model = make_model(barrier_type=barrier_type, num_blocks=4)
        model.start()
        for _ in range(20):
            if model.state == SimulationState.RUNNING:
                model.step()
        return model.get_snapshot()

    def test_snapshot_has_required_keys(self):
        """快照应包含 tick, simulation_state, blocks, barrier"""
        snap = self._get_snapshot_after_run()
        for key in ["tick", "simulation_state", "blocks", "barrier"]:
            self.assertIn(key, snap)

    def test_snapshot_blocks_count(self):
        """快照中 blocks 数量应与配置一致"""
        snap = self._get_snapshot_after_run()
        self.assertEqual(len(snap["blocks"]), 4)

    def test_snapshot_has_metrics(self):
        """快照应包含 metrics 数据"""
        snap = self._get_snapshot_after_run()
        self.assertIn("metrics", snap)

    def test_snapshot_has_global_memory(self):
        """快照应包含 global_memory 数据"""
        snap = self._get_snapshot_after_run()
        self.assertIn("global_memory", snap)

    def test_tree_snapshot_has_topology(self):
        """TreeBarrier 快照应包含 topology 数据"""
        snap = self._get_snapshot_after_run(barrier_type="TREE")
        self.assertIn("topology", snap)

    def test_static_tree_snapshot_has_topology(self):
        """StaticTreeBarrier 快照应包含 topology 数据"""
        snap = self._get_snapshot_after_run(barrier_type="STATIC_TREE")
        self.assertIn("topology", snap)

    def test_centralized_snapshot_no_topology(self):
        """CentralizedBarrier 快照不应包含 topology"""
        snap = self._get_snapshot_after_run(barrier_type="CENTRALIZED")
        # CentralizedBarrier 没有 get_topology 方法，快照中不应有此字段
        self.assertNotIn("topology", snap)

    def test_block_status_fields(self):
        """每个 Block 状态应包含规定字段"""
        snap = self._get_snapshot_after_run()
        for block in snap["blocks"]:
            for key in ["id", "state", "progress", "work_done", "at_barrier"]:
                self.assertIn(key, block)


# ═══════════════════════════════════════════════════════════════════════
#  5. 三种算法一致性对比测试
# ═══════════════════════════════════════════════════════════════════════

class TestAlgorithmConsistency(unittest.TestCase):
    """三种栅栏算法在相同配置下的行为一致性验证"""

    def setUp(self):
        random.seed(42)

    def test_all_algorithms_reach_sync(self):
        """三种算法在相同条件下均应能完成至少一轮同步"""
        for barrier_type in ["CENTRALIZED", "TREE", "STATIC_TREE"]:
            random.seed(42)
            model = make_model(
                barrier_type=barrier_type,
                num_blocks=4,
                barrier_interval=10,
                workload_variance=0.0,
            )
            run_until(model, max_ticks=100)
            stats = model.barrier.metrics.get_statistics()
            self.assertGreaterEqual(
                stats["sync_count"], 1,
                f"{barrier_type} 未能完成任何同步"
            )

    def test_tree_communication_higher_than_centralized(self):
        """树形算法的通信开销应高于集中式（O(log n) 层传播 vs O(1) 直接计数）"""
        results = {}
        for barrier_type in ["CENTRALIZED", "TREE"]:
            random.seed(42)
            model = make_model(
                barrier_type=barrier_type,
                num_blocks=8,
                barrier_interval=10,
                workload_variance=0.0,
            )
            run_until(model, max_ticks=100)
            stats = model.barrier.metrics.get_statistics()
            if stats["sync_count"] > 0:
                results[barrier_type] = stats["avg_communication"]

        if "CENTRALIZED" in results and "TREE" in results:
            self.assertGreater(results["TREE"], results["CENTRALIZED"])

    def test_model_state_transitions(self):
        """仿真状态应遵循 STOPPED → RUNNING 的转换"""
        model = make_model()
        self.assertEqual(model.state, SimulationState.STOPPED)
        model.start()
        self.assertEqual(model.state, SimulationState.RUNNING)
        model.pause()
        self.assertEqual(model.state, SimulationState.PAUSED)

    def test_different_block_counts(self):
        """不同 Block 数量下三种算法均应正常工作"""
        for num_blocks in [2, 4, 8]:
            for barrier_type in ["CENTRALIZED", "TREE", "STATIC_TREE"]:
                random.seed(42)
                model = make_model(
                    barrier_type=barrier_type,
                    num_blocks=num_blocks,
                    barrier_interval=10,
                    workload_variance=0.0,
                )
                run_until(model, max_ticks=100)
                stats = model.barrier.metrics.get_statistics()
                self.assertGreaterEqual(
                    stats["sync_count"], 1,
                    f"{barrier_type} num_blocks={num_blocks} 未能完成同步"
                )


# ═══════════════════════════════════════════════════════════════════════
#  6. 失联模式整体流程测试
# ═══════════════════════════════════════════════════════════════════════

class TestFailureModeIntegration(unittest.TestCase):
    """失联模式下的端到端仿真验证"""

    def test_failure_mode_runs_without_crash(self):
        """失联模式应能顺利运行不崩溃"""
        random.seed(42)
        model = make_model(
            barrier_type="CENTRALIZED",
            simulation_mode="FAILURE",
            num_blocks=4,
            barrier_interval=10,
            failure_rate=0.01,
            timeout_threshold=50,
        )
        # 即使有故障注入也不应引发异常
        run_until(model, max_ticks=200)
        self.assertGreater(model.current_tick, 0)

    def test_failure_mode_detects_failed_blocks(self):
        """失联模式下应有 Block 被标记为 FAILED"""
        random.seed(42)
        model = make_model(
            barrier_type="CENTRALIZED",
            simulation_mode="FAILURE",
            num_blocks=4,
            barrier_interval=10,
            failure_rate=0.1,       # 较高故障率
            timeout_threshold=20,   # 较低超时阈值
        )
        run_until(model, max_ticks=200)
        failed = [b for b in model.blocks if b.state == BlockState.FAILED]
        self.assertGreater(len(failed), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
