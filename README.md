# GPU 栅栏模拟系统 (GPU Barrier Simulation) Version 3.0

一个用于模拟和可视化GPU线程块级栅栏同步机制的教学与研究工具。

## 功能特性

### 核心仿真
- **3种栅栏算法**：Centralized、Tree、Static Tree
- **2种仿真模式**：
    - **Normal**: 正常模式，模拟真实的随机负载波动
    - **Failure**: 失联模式，支持随机失联注入与超时检测，展示栅栏的容错能力
- **全局内存模拟**：可视化栅栏算法内部的内存状态（如计数器、标志位）

### 性能指标
- **简化核心指标**：聚焦于 延迟 (Latency) 和 通信开销 (Communication Overhead)
- **实时热图 (Heatmap)**：直观展示 Block 在时间轴上的状态分布（运行、等待、释放）
- **动态仪表盘**：Web 端实时图表显示

### Web 界面 (v3.0)
- **现代化 UI**：基于 Grid 布局的 Block 状态网格
- **交互控制**：
    - START / PAUSE / STEP 控制
    - 动态调节负载不均衡度 (Workload Variance)
    - 实时切换 栅栏算法 和 仿真模式
- **中英文支持**：界面全面中文化

## 系统要求

- Python 3.7+
- 推荐使用虚拟环境

## 快速开始


### 1. 安装依赖

```bash
cd d:\code\GPU_barrier_similation

# 安装依赖（如果使用虚拟环境，请先激活）
pip install -r requirements.txt
```

> **注意**：如果 `requirements.txt` 为空或缺失，核心功能不需要额外依赖（只使用Python标准库），但测试脚本需要 `requests` 库：
> ```bash
> pip install requests
> ```

### 2. 运行程序

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 运行程序
python src/main.py
```

**预期输出**：
```
API Server started on http://localhost:8000
Tick:     1 | Barrier: 0/8 | Sense: 0
0:. 1:. 2:. 3:. 4:. 5:. 6:. 7:. 
----------------------------------------
Tick:     2 | Barrier: 0/8 | Sense: 0
0:. 1:. 2:. 3:. 4:. 5:. 6:. 7:. 
----------------------------------------
...
```

### 3. 访问Web UI

打开浏览器，访问：

**http://localhost:8000**

你将看到全新的可视化界面，包含 Block 网格、控制面板和实时图表。

## 使用指南

### 核心操作

1. **选择模式与算法**：
   - 在左侧面板选择 **仿真模式** (Normal/Failure)
   - 选择 **栅栏类型** (Centralized, Tree, Static Tree)
   - 调节 **负载方差** (影响 Block 速度的随机波动)

2. **控制运行**：
   - 点击 **START** 运行仿真
   - 点击 **RESET & APPLY** 应用新的配置（模式/算法/方差）
   - 点击 **PAUSE** 暂停

3. **观察结果**：
   - **状态网格**：绿色-运行，黄色-等待，红色-故障
   - **Metrics 面板**：显示平均延迟和通信开销
   - **Comparison 面板**：对比不同算法的历史性能
   - **Heatmap 面板**：查看时间轴上的 Block 行为

### 失联模式测试 (Failure Mode)

1. 选择 **Failure Mode**
2. 选择一种栅栏算法（如 Centralized）
3. 运行仿真，观察部分 Block 变红（随机故障或超时）
4. 观察系统是否能从故障中恢复（目前 Centralized 会死锁等待，展示了非容错栅栏的弱点）

## 项目结构 (v3.0 重构)

```
GPU_barrier_similation/
├── config/                  # 配置文件
│   └── default_scenario.json
├── docs/                    # 文档目录
│   ├── api_docs.md          # API 接口文档
│   ├── technical_docs.md    # 技术架构文档
│   └── dev_log.md           # 开发日志
├── src/
│   ├── main.py              # 程序入口
│   ├── controller/          # 仿真控制器
│   ├── model/               # 模型层
│   │   ├── simulation_model.py
│   │   ├── block.py
│   │   ├── barriers/        # [NEW] 栅栏算法实现库
│   │   │   ├── centralized_barrier.py
│   │   │   └── tree_barrier.py ...
│   │   ├── schedulers/      # [NEW] 调度器实现库
│   │   │   ├── normal_scheduler.py
│   │   │   └── failure_scheduler.py
│   │   └── event_bus.py     # 事件总线
│   └── web/                 # Web 前端资源
│       ├── index.html
│       ├── app.js
│       ├── styles.css
│       └── ...
├── tests/                   # 测试脚本
│   └── test_all_algorithms.py
└── README.md                # 本文件
```

## API与开发

完整 API 文档请查看：[docs/api_docs.md](docs/api_docs.md)

### 常用 API

- `POST /api/control`: 发送 START, PAUSE, RESET 命令
- `GET /api/state`: 获取当前仿真快照
- `GET /api/metrics`: 获取性能指标
- `GET /api/memory`: [NEW] 获取栅栏内部内存状态

## 运行测试

```bash
# 运行全面测试（测试所有3种算法及API）
python tests/test_all_algorithms.py
```



