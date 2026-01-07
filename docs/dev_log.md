# 开发日志 (Development Log)

本文档用于记录开发过程中的关键操作、环境变更及决策，以确保工程状态可追溯。

## 2026-01-06

### 环境初始化 (Environment Initialization)
- **操作目标**: 创建本地虚拟环境并初始化 Git 仓库。
- **状态**: 
    - [x] 创建虚拟环境 (`.venv`)
    - [x] 配置 `.gitignore`
    - [x] 初始化 Git

### 已完成功能清单 (Completed Features)
记录截至目前已完成的关键开发任务：

#### 1. 文档建设
- [x] **技术文档**: 创建了 `technical_docs.md` (中文)，覆盖系统架构 (MVC)、核心组件 (Block/Barrier/Scheduler) 及数据结构。
- [x] **API 文档**: 创建了 `api_docs.md`，定义了 HTTP 控制接口规范。
- [x] **系统设计**: 整理了 `system_design_info.md`，包含研究背景与设计思路。

#### 2. 核心功能实现 (Core Implementation)
- [x] **多样化栅栏算法**:
    - 重构了 `Barrier` 抽象基类。
    - **CentralizedBarrier**: 传统的集中式计数器实现。
    - **TreeBarrier**: 模拟二叉树结构的对数级同步算法。
    - **ButterflyBarrier**: 模拟多阶段成对交换的蝴蝶形同步算法。
- [x] **通用 Block 逻辑**:
    - 更新了 `Block.py`，引入 `check_release` 接口，解耦了 Block 对 Barrier 内部实现细节（如 sense 变量）的依赖。

#### 3. 接口与控制 (API & Control)
- [x] **HTTP API Server**:
    - 在 `SimulationController` 中集成了多线程 HTTP Server (端口 8000)。
    - 支持 `POST /api/control` 进行 START/PAUSE/STEP/RESET 操作。
    - 支持 `GET /api/state` 获取实时仿真快照。

#### 4. 高级特性 (Enhancements)
- [x] **可配置的负载波动 (Workload Variance)**:
    - `SimulationModel` 读取配置文件中的 `behavior_profile.workload_variance`。
    - `Block` 根据方差随机初始化运行速度因子 (`speed_factor`)，模拟真实的异构执行环境。
- [x] **异常检测 (Anomaly Detection)**:
    - `Scheduler` 新增死锁/挂起检测逻辑。当所有 Block 等待由于栅栏未释放而卡死时，记录警告日志。

#### 5. 验证 (Verification)
- [x] **集成测试**:
    - 编写并运行了 `tests/test_api.py` (及 `debug_reset.py`)。
    - 验证了通过 API 启动仿真、动态切换栅栏类型 (Centralized -> Tree) 的正确性。

#### 6. 可视化前端 (Visualization Frontend)
- [x] **Web UI**:
    - 创建了 `src/web/index.html`, `styles.css`, `app.js`。
    - 实现了基于 Grid 的 Block 状态可视化 (颜色区分 Running/Waiting/Finished) 和进度条。
    - 提供了 Start/Pause/Step/Reset 图形化控制面板。
- [x] **静态资源服务**:
    - 更新 `SimulationController`，使其在 `/` 路径下服务静态文件，成为一个自包含的 Web 应用。
