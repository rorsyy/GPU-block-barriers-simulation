# tests/ 测试目录说明

## 目录结构

```
tests/
├── test_unit.py           # 单元测试（46 用例）
├── test_interface.py      # 接口测试（22 用例）
├── test_integration.py    # 整体测试（29 用例）
├── test_runner_ui.py      # 可视化测试面板（Web UI）
├── test_api.py            # API 接口测试（需先启动后端）
├── test_frontend.py       # 前端静态资源测试（需先启动后端）
├── test_all_algorithms.py # 算法验证脚本（需先启动后端）
└── README.md              # 本文件
```

## 前置条件

> **⚠ 重要提醒**：部分测试依赖后端服务器，请根据下方说明判断是否需要先启动主程序。

| 测试文件 | 是否需要启动后端 | 说明 |
|---------|:---------------:|------|
| `test_unit.py` | ❌ 不需要 | 纯 Model 层单元测试，无外部依赖 |
| `test_interface.py` | ❌ 不需要 | 模块间接口测试，无外部依赖 |
| `test_integration.py` | ❌ 不需要 | 端到端仿真测试，无外部依赖 |
| `test_runner_ui.py` | ❌ 不需要 | 自带 HTTP 服务器，独立运行 |
| `test_api.py` | ✅ **需要** | 测试 HTTP API 接口，依赖后端服务 |
| `test_frontend.py` | ✅ **需要** | 测试静态资源服务，依赖后端服务 |
| `test_all_algorithms.py` | ✅ **需要** | 通过 API 验证算法切换，依赖后端服务 |

### 启动后端服务

对于标记为"需要"的测试，请先在**另一个终端窗口**中启动后端：

```bash
python src/main.py
```

等待出现以下输出后，再运行对应测试：

```
API Server started on http://localhost:8000
仿真已就绪。按 Ctrl+C 可随时停止。
```

## 快速开始

### 运行核心测试（无需启动后端）

```bash
python -m pytest tests/test_unit.py tests/test_interface.py tests/test_integration.py -v
```

### 运行单个测试文件

```bash
python -m pytest tests/test_unit.py -v          # 仅单元测试
python -m pytest tests/test_interface.py -v      # 仅接口测试
python -m pytest tests/test_integration.py -v    # 仅整体测试
```

### 运行某个测试类

```bash
python -m pytest tests/test_unit.py::TestCentralizedBarrier -v
```

### 运行需要后端的测试

```bash
# 终端 1：启动后端
python src/main.py

# 终端 2：运行 API 测试
python tests/test_api.py
python tests/test_frontend.py
python tests/test_all_algorithms.py
```

### 启动可视化测试面板

```bash
python tests/test_runner_ui.py
```

启动后在浏览器中打开 `http://localhost:8899`，通过左侧按钮点击运行测试，右侧实时查看结果。

> 注：可视化面板仅包含核心测试（单元/接口/整体），不需要启动后端。

## 测试分层说明

### 单元测试 (`test_unit.py`)

针对 Model 层各核心模块的最小可测试单元进行独立验证。

| 测试类 | 被测模块 | 用例数 | 测试重点 |
|--------|---------|--------|---------|
| TestEventBus | EventBus | 12 | 发布-订阅、异常隔离、历史记录、工厂函数 |
| TestBlock | Block | 13 | 状态机四态转换、线性插值进度、边界条件 |
| TestBarrierMetrics | BarrierMetrics | 8 | 采集生命周期、统计计算、reset |
| TestBarrierAtomicInstructions | Barrier 基类 | 4 | sim_atomic_add / sim_atomic_exch 语义 |
| TestCentralizedBarrier | CentralizedBarrier | 8 | 到达-释放逻辑、sense 翻转、内存一致性 |
| TestTreeBarrier | TreeBarrier | 8 | 树构建、分层传播、sense 广播 |
| TestStaticTreeBarrier | StaticTreeBarrier | 8 | 数组索引树、父子公式、键名格式 |

### 接口测试 (`test_interface.py`)

验证模块之间的交互接口是否按设计规范工作。

| 测试类 | 测试接口 | 用例数 | 测试重点 |
|--------|---------|--------|---------|
| TestEventBusRouting | EventBus ↔ 订阅者 | 3 | 事件路由、回调中发布安全性 |
| TestSchedulerBlockInterface | Scheduler → Block | 4 | 目标分配、工作推进、到达等待 |
| TestSchedulerReleaseInterface | Scheduler ↔ EventBus | 4 | 释放恢复、目标重分配、cleanup |
| TestFailureSchedulerInterface | FailureScheduler | 3 | 超时检测、故障注入、事件发布 |
| TestBarrierMetricsInterface | Barrier ↔ Metrics | 5 | 到达记录、同步计数、通信统计 |
| TestModelBarrierArrivalInterface | Model → Barrier | 3 | 到达回调、释放事件发布 |

### 整体测试 (`test_integration.py`)

验证仿真系统端到端的核心流程。

| 测试类 | 测试场景 | 用例数 | 测试重点 |
|--------|---------|--------|---------|
| TestModelInitialization | 模型初始化 | 9 | 三种栅栏 × 两种调度器的正确创建 |
| TestSingleSyncCycle | 单轮同步 | 5 | 到达 → 释放 → 恢复的完整闭环 |
| TestMultiSyncCycles | 多轮同步 | 4 | 连续多阶段同步的稳定性 |
| TestSnapshotIntegrity | 快照完整性 | 8 | get_snapshot 数据结构验证 |
| TestAlgorithmConsistency | 算法一致性 | 4 | 三种算法在相同条件下的行为对比 |
| TestFailureModeIntegration | 失联模式 | 2 | 故障注入下的端到端稳定性 |

## 相关文档

- 测试用例与结果的正式文档：[`docs/test_document.md`](../docs/test_document.md)
