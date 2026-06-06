
# 系统架构设计文档 (System Architecture Design)

> 本文档描述 GPU 栅栏模拟系统的完整架构设计。所有 UML 图表采用 PlantUML 语法，已针对 **A4 黑白打印** 优化。

---

## 一、技术架构图 (Technical Architecture)

> 系统采用 MVC 三层架构。View 层通过 HTTP 轮询获取状态，Controller 层通过命令队列驱动主循环，Model 层内部以 EventBus 实现组件间的发布-订阅解耦。在最新的重构中，全局内存 (`GlobalMemory`) 已从栅栏算法中剥离为独立模块，仅作为被动存储介质供栅栏算法通过原子指令进行读写。

```plantuml
@startuml
' === A4 黑白打印优化 ===
scale max 680 width
skinparam dpi 150
skinparam defaultFontSize 10
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true
skinparam componentStyle rectangle
skinparam packageStyle rectangle
skinparam padding 6
skinparam nodesep 40
skinparam ranksep 40

title GPU栅栏模拟系统 - 技术架构图

package "View 层 (展示层)" {
    component [前端可视化\n(HTTP轮询)] as V1
}

package "Controller 层" {
    component [API服务\n(REST接口)] as C1
    component [仿真控制\n(主循环引擎)] as C2
}

package "Model 层" {
    component [事件总线\n<<发布-订阅>>] as M1
    component [调度策略\n<<策略模式>>] as M2
    component [线程块\n(状态机)] as M3
    component [栅栏算法\n<<工厂模式>>] as M4
    component [全局内存\n(被动存储)] as M5
    component [性能指标\n(通信打点)] as M6
}

V1 -down-> C1 : HTTP请求
C1 -up-> V1 : JSON响应
C1 -down-> C2 : 命令队列
C2 -down-> M2 : schedule_tick()
C2 -down-> M4 : 初始化算法
M2 -right-> M1 : 发布事件
M1 -left-> M2 : 推送事件
M1 -right-> M4 : 转发事件
M4 -left-> M1 : 发布事件
M2 -down-> M3 : 驱动Block
M4 -down-> M5 : read()/write()
M4 -down-> M6 : record_communication()

@enduml
```

### 架构解读

| 层级 | 核心职责 | 技术选型 | 设计模式 |
|------|---------|---------|---------|
| View | 用户交互、可视化 | HTML/CSS/JS + HTTP轮询 | — |
| Controller | 请求路由、主循环调度 | Python单线程 + 命令队列 | — |
| Model | 仿真逻辑、事件协调 | EventBus | 发布-订阅 |
| Scheduler | Block调度策略 | Normal/FailureScheduler | 策略模式 |
| Barrier | 同步算法 + 原子指令 | Centralized/Tree/StaticTree | 工厂模式 |
| GlobalMemory | 被动存储介质 | Dict封装 (read/write) | — |
| Block | 执行单元状态 | 状态机 | — |

**关键设计决策**：
- Controller 通过**命令队列**将 API 请求异步传递给主循环，避免多线程竞争。
- Model 内部通过 **EventBus** 实现 Scheduler 与 Barrier 完全解耦。
- **GlobalMemory 独立解耦**：全局内存从 Barrier 基类中剥离为独立模块，仅提供 `read()` / `write()` / `get_snapshot()` 三个纯访存接口。原子指令仍由 Barrier（代表 SM）发起，内部调用 GlobalMemory 的接口完成"读-改-写"操作。
- 前端采用 **HTTP 轮询**获取实时状态。

---

## 二、功能模块图 (Functional Modules)

展示系统提供的功能集合，从用户视角描述系统能力。

```plantuml
@startuml FuncModules
skinparam monochrome true
skinparam shadowing false
skinparam defaultFontName SimHei
skinparam componentStyle rectangle
skinparam padding 8
skinparam nodesep 40
skinparam ranksep 50

title GPU栅栏模拟系统 - 功能模块图

package "配置功能" {
    rectangle "基础参数设置" as Config1
    rectangle "栅栏算法选择" as Config2
    rectangle "调度模式选择" as Config3
    rectangle "故障参数配置" as Config4
}

package "控制功能" {
    rectangle "启动仿真" as Start
    rectangle "暂停仿真" as Pause
    rectangle "单步执行" as Step
    rectangle "重置仿真" as Reset
}

package "监控功能" {
    rectangle "Block状态监控" as BlockMon
    rectangle "内存状态监控" as MemMon
    rectangle "仿真进度监控" as ProgMon
}

package "分析功能" {
    rectangle "同步次数统计" as SyncStat
    rectangle "通信开销统计" as CommStat
    rectangle "性能对比" as Compare
}

package "展示功能" {
    rectangle "状态网格可视化" as GridVis
    rectangle "内存热力图" as HeatMap
    rectangle "树形拓扑图" as TreeVis
    rectangle "指标数据导出" as Export
}






@enduml
```

| 功能域 | 核心功能 | 对应实现 |
|--------|---------|---------|
| 配置 | 设置Block数量、选择栅栏算法、选择调度模式、配置故障参数 | 前端配置面板 -> Controller |
| 控制 | 启动/暂停/单步/重置仿真 | 前端按钮 -> API /control |
| 监控 | 实时Block状态、内存状态、仿真进度 | 前端轮询 -> API /state |
| 分析 | 同步/通信统计、性能对比 | BarrierMetrics -> API /metrics |
| 展示 | 网格/热力图/拓扑图可视化 | 前端渲染 -> API 数据 |

---

## 三、模块级交互时序图 (Module Interaction Sequence)

展示一个完整仿真周期内各模块之间的调用顺序与数据流向。

```plantuml
@startuml ModuleSequence
scale max 800 width
skinparam dpi 150
skinparam defaultFontSize 10
skinparam sequenceMessageFontSize 9
skinparam sequenceParticipantFontSize 10
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true
skinparam linetype ortho

participant "前端界面" as UI
participant "API服务" as API
participant "命令队列" as QUEUE
participant "主循环引擎" as LOOP
participant "Scheduler" as SCH
participant "EventBus" as EB
participant "Barrier" as BAR
participant "Block" as BLK
participant "全局内存" as MEM
participant "性能指标" as MET

activate UI
UI -> API : 1. POST /api/control {command:START}
activate API
API -> QUEUE : 2. 命令入队
deactivate API
activate QUEUE
QUEUE -> LOOP : 3. 取出命令
deactivate QUEUE
activate LOOP

loop 每个仿真Tick
    LOOP -> SCH : 4. schedule_tick(tick)
    activate SCH
    
    par 每个Block
        SCH -> BLK : 5. run_step()
        activate BLK
        BLK --> SCH : 5.1 进度更新
        deactivate BLK
        
        alt 到达同步点
            SCH -> BLK : 5.2 set_waiting()
            SCH -> EB : 6. publish(ARRIVAL)
            activate EB
        end
    end
    
    EB -> BAR : 7. on_barrier_arrival()
    activate BAR
    BAR -> BAR : 8. arrive(block_id, tick)
    BAR -> MEM : 9. sim_atomic_add(counter, 1)
    activate MEM
    MEM --> BAR : 9.1 old_count
    deactivate MEM
    
    alt 计数器达到阈值
        BAR -> MEM : 10. sim_atomic_exch(counter, 0)
        activate MEM
        MEM --> BAR : 10.1
        deactivate MEM
        
        BAR -> BAR : 11. release_all()
        BAR -> MET : 12. record_release()
        activate MET
        MET --> BAR : 12.1
        deactivate MET
        
        BAR -> EB : 13. publish(RELEASE)
        EB --> SCH : 14. on_release()
        
        loop 每个等待中的Block
            SCH -> BLK : 15. resume()
            activate BLK
            BLK --> SCH : 15.1
            deactivate BLK
        end
    end
    
    BAR --> EB : 
    deactivate BAR
    EB --> SCH : 
    deactivate EB
    SCH --> LOOP : 
    deactivate SCH
    
    LOOP -> LOOP : 16. 更新快照
end

UI -> API : 17. GET /api/state
activate API
API -> LOOP : 18. 获取快照
LOOP --> API : 18.1 snapshot
deactivate LOOP
API --> UI : 19. JSON状态数据
deactivate API

@enduml
```

| 阶段 | 步骤 | 核心操作 | 目的 |
|------|------|---------|------|
| 初始化 | 1-3 | 命令入队取出 | 用户启动仿真 |
| Tick执行 | 4-5 | Scheduler驱动Block | 推进仿真时间 |
| 到达同步 | 6 | 发布ARRIVAL事件 | 通知Barrier |
| 栅栏处理 | 7-10 | 原子操作计数 | 模拟硬件同步 |
| 释放唤醒 | 11-15 | 发布RELEASE事件 | 恢复Block执行 |
| 状态查询 | 16-19 | 快照更新轮询 | 前端数据展示 |

---

## 四、事件驱动通信流程 (Event-Driven Communication)

```plantuml
@startuml EventSequence
' === A4 黑白打印优化 ===
scale max 720 width
skinparam dpi 150
skinparam defaultFontSize 11
skinparam sequenceMessageFontSize 10
skinparam sequenceParticipantFontSize 11
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true

participant "Scheduler" as S
participant "EventBus" as EB
participant "SimulationModel" as SM
participant "Barrier" as B
participant "Block" as BLK

== 单个 Tick 生命周期 ==

SM -> S : schedule_tick(tick)

loop 每个 Block
    S -> BLK : run_step()
    BLK --> S : 进度

    alt 到达同步点
        S -> BLK : set_waiting(tick)
        S -> EB : publish(ARRIVAL)
    end
end

EB -> SM : on_barrier_arrival()
SM -> B : arrive(id, tick)
B -> B : sim_atomic_add("counter")

alt 全部到达
    B --> SM : return true
    SM -> EB : publish(RELEASE)
    EB -> S : on_release()
    loop 释放等待中的 Block
        S -> BLK : resume()
    end
end
@enduml
```

### 事件类型

| 事件              | 发布者           | 订阅者    | 触发时机                     |
| ----------------- | ---------------- | --------- | ---------------------------- |
| `BARRIER_ARRIVAL` | Scheduler        | Model     | Block 进度跨过 interval 倍数 |
| `BARRIER_RELEASE` | Model            | Scheduler | 全部 Block 到达栅栏          |
| `BLOCK_FAILURE`   | FailureScheduler | —         | 超时或随机故障               |

---

## 三、核心类图 (Class Diagram)

```plantuml
@startuml ClassDiagram
' === A4 黑白打印优化 ===
scale max 720 width
skinparam dpi 150
skinparam defaultFontSize 10
skinparam classAttributeFontSize 9
skinparam classFontSize 11
skinparam classAttributeIconSize 0
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true
skinparam linetype ortho

class SimulationController {
    +model : SimulationModel
    +command_queue : Queue
    --
    +run_loop()
    +_handle_command(cmd)
}

class SimulationModel {
    +state : SimulationState
    +current_tick : int
    +blocks : List<Block>
    +barrier : Barrier
    +event_bus : EventBus
    --
    +init_simulation(config)
    +step()
    +get_snapshot() : dict
}

class EventBus {
    -_subscribers : Dict
    -_event_history : List
    --
    +subscribe(type, callback)
    +publish(event)
}

abstract class Barrier {
    +limit : int
    +global_memory : Dict
    +metrics : BarrierMetrics
    --
    +{abstract} arrive(id, tick) : bool
    +{abstract} check_release()
    +{abstract} is_full() : bool
    +{abstract} get_status() : dict
    .. 原子指令封装 ..
    +sim_atomic_add(key, val) : old
    +sim_atomic_exch(key, val) : old
    .. 查询接口 ..
    +get_memory_state() : Dict
    +get_metrics() : Dict
}

class Block {
    +id : int
    +state : BlockState
    +current_work_ticks : float
    +remaining_work : float
    --
    +run_step() : bool
    +set_waiting(tick)
    +resume()
    +fail(reason)
}

class BarrierMetrics {
    +sync_count : int
    --
    +record_arrival(id, tick)
    +record_communication(n)
    +record_release(tick)
    +get_statistics() : Dict
}

class NormalScheduler {
    +barrier_interval : int
    --
    +schedule_tick(tick)
}

class FailureScheduler {
    +timeout_threshold : int
    +failure_rate : float
    --
    +schedule_tick(tick)
    +_perform_health_check()
}

class CentralizedBarrier
class TreeBarrier
class StaticTreeBarrier

SimulationController --> SimulationModel
SimulationModel *-- EventBus
SimulationModel *-- Barrier
SimulationModel "1" o-- "N" Block
Barrier *-- BarrierMetrics

EventBus <.. NormalScheduler
EventBus <.. FailureScheduler

Barrier <|-- CentralizedBarrier
Barrier <|-- TreeBarrier
Barrier <|-- StaticTreeBarrier
@enduml
```

---

## 四、线程块状态机 (Block State Machine)

```plantuml
@startuml BlockStateMachine
' === A4 黑白打印优化 ===
scale max 500 width
skinparam dpi 150
skinparam defaultFontSize 11
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true

[*] --> RUNNING : 初始化

state RUNNING {
    RUNNING : 执行计算任务
    RUNNING : 每tick随机工作量
}

state WAITING_AT_BARRIER {
    WAITING_AT_BARRIER : 等待其他Block
    WAITING_AT_BARRIER : 已到达同步点
}

state FINISHED {
    FINISHED : 全部工作量完成
}

state FAILED {
    FAILED : 超时或故障
}

RUNNING --> WAITING_AT_BARRIER : 到达同步点
RUNNING --> FINISHED : remaining_work ≤ 0
RUNNING --> FAILED : 随机失联 (Failure模式)

WAITING_AT_BARRIER --> RUNNING : BARRIER_RELEASE事件
WAITING_AT_BARRIER --> FAILED : 等待超时 > threshold

FINISHED --> [*]
FAILED --> [*]
@enduml
```

| 状态                 | 含义     | 前端标记 | 触发条件             |
| -------------------- | -------- | -------- | -------------------- |
| `RUNNING`            | 执行计算 | 实心圆   | 初始 / 栅栏释放后    |
| `WAITING_AT_BARRIER` | 等待同步 | 斜线填充 | 进度达 interval 倍数 |
| `FINISHED`           | 完成     | 空心圆   | `remaining_work ≤ 0` |
| `FAILED`             | 故障     | 叉号标记 | 仅 Failure 模式      |

---

## 六、仿真模式选择 (Simulation Modes)

```plantuml
@startuml SimModes
' === A4 黑白打印优化 ===
scale max 600 width
skinparam dpi 150
skinparam defaultFontSize 11
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true

rectangle "config.json\nsimulation_mode" as CFG

rectangle "<<Normal>>\nNormalScheduler\n随机速度 · 无故障" as NS
rectangle "<<Failure>>\nFailureScheduler\n随机速度 · 超时检测\n故障注入 · 健康检查" as FS

rectangle "EventBus" as EB

CFG -down-> NS : "NORMAL"
CFG -down-> FS : "FAILURE"

NS -down-> EB : 发布/订阅
FS -down-> EB : 发布/订阅
@enduml
```

| 模式           | Block 速度 | 故障               | 场景         |
| -------------- | ---------- | ------------------ | ------------ |
| **NORMAL**     | 随机波动   | 无                 | 日常演示     |
| **FAILURE**    | 随机波动   | 超时+失联+健康检查 | 容错测试     |

---

## 七、原子指令封装 (Simulated Atomic Instructions)

`Barrier` 基类封装了两个模拟 GPU 硬件原子指令的方法，在逻辑模型上严格对应 GPU 的 **读-改-写** 不可分割操作。

```plantuml
@startuml AtomicOps
' === A4 黑白打印优化 ===
scale max 600 width
skinparam dpi 150
skinparam defaultFontSize 11
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true

package "GPU 硬件原子指令" {
    rectangle "atomicAdd(&addr, val)" as CA
    rectangle "atomicExch(&addr, val)" as CE
}

package "仿真封装 (Barrier 基类)" {
    rectangle "sim_atomic_add(key, val)\n  old = mem[key]\n  mem[key] += val\n  record_communication(1)\n  return old" as SA
    rectangle "sim_atomic_exch(key, val)\n  old = mem[key]\n  mem[key] = val\n  record_communication(1)\n  return old" as SE
}

CA .right.> SA : <<逻辑等价>>
CE .right.> SE : <<逻辑等价>>
@enduml
```

**用法 (CentralizedBarrier)**:
```python
def arrive(self, block_id, tick):
    old = self.sim_atomic_add("counter", 1)   # CUDA: atomicAdd(&counter, 1)

def release_all(self, tick):
    self.sim_atomic_exch("counter", 0)         # CUDA: atomicExch(&counter, 0)
    self.sim_atomic_exch("sense", new_sense)   # CUDA: atomicExch(&sense, val)
```

---

## 八、数据流概览 (Data Flow)

```plantuml
@startuml DataFlow
' === A4 黑白打印优化 ===
left to right direction
scale max 720 width
skinparam dpi 150
skinparam defaultFontSize 10
skinparam backgroundColor white
skinparam shadowing false
skinparam monochrome true
skinparam nodesep 20

actor "用户" as User

rectangle "Web UI" as WebUI
rectangle "HTTP API" as API
rectangle "Controller" as Ctrl
rectangle "SimulationModel" as Model
rectangle "Scheduler" as Sched
rectangle "Block×N" as Blk
rectangle "EventBus" as EB
rectangle "Barrier" as Bar
rectangle "global_memory" as GM
rectangle "BarrierMetrics" as Met

User --> WebUI : 访问:8000
WebUI --> API : POST /control
API --> Ctrl : 命令Queue

Ctrl --> Model : step()
Model --> Sched : schedule_tick()
Sched --> Blk : run_step()
Sched --> EB : ARRIVAL
EB --> Model : on_arrival()
Model --> Bar : arrive()
Bar --> GM : atomic ops
Bar --> Met : record()

Ctrl --> Model : get_snapshot()

WebUI --> API : GET /state
WebUI --> API : GET /metrics
WebUI --> API : GET /memory
@enduml
```

---

## 九、目录结构

```
GPU_barrier_similation/
├── config/default_scenario.json     ← 仿真参数配置
├── src/
│   ├── main.py                      ← 入口
│   ├── controller/
│   │   └── simulation_controller.py ← API + 主循环
│   ├── model/
│   │   ├── simulation_model.py      ← 仿真协调器
│   │   ├── block.py                 ← 线程块
│   │   ├── barrier.py               ← 栅栏基类 + 原子指令
│   │   ├── barrier_metrics.py       ← 指标收集
│   │   ├── event_bus.py             ← 事件总线
│   │   ├── barriers/                ← 4种栅栏算法
│   │   └── schedulers/              ← 3种调度器
│   ├── view/console_view.py         ← 控制台输出
│   └── web/                         ← Web 前端
├── tests/                           ← 集成测试
└── docs/                            ← 文档
```
## 十、系统用例图 (Use Case Diagram)

```plantuml
@startuml
title 栅栏模拟软件 - 核心用例图

left to right direction
skinparam defaultFontName Microsoft YaHei

actor "系统用户\n(研究员/开发者)" as User

rectangle " 栅栏模拟软件" {

    ' ===== 核心用例 =====
    usecase "配置仿真参数" as UC_Config
    usecase "控制仿真执行" as UC_Control
    usecase "查看模拟结果" as UC_View

    ' ===== 子用例（include）=====
    usecase "设置基础参数" as UC_Base
    usecase "选择调度模式" as UC_Mode
    usecase "选择栅栏算法" as UC_Algo
    usecase "高级故障配置" as UC_Fail

    usecase "启动模拟" as UC_Start
    usecase "暂停模拟" as UC_Pause
    usecase "重置模拟" as UC_Reset

    usecase "查看线程块状态" as UC_Block
    usecase "查看内存状态" as UC_Mem
    usecase "查看性能指标" as UC_Metrics
    usecase "查看拓扑结构" as UC_Topo
}

' ===== 用户交互 =====
User --> UC_Config
User --> UC_Control
User --> UC_View

' ===== include =====
UC_Config --> UC_Base : <<include>>
UC_Config --> UC_Mode : <<include>>
UC_Config --> UC_Algo : <<include>>

UC_Control --> UC_Start : <<include>>
UC_Control --> UC_Pause : <<include>>
UC_Control --> UC_Reset : <<include>>

UC_View --> UC_Block : <<include>>
UC_View --> UC_Mem : <<include>>
UC_View --> UC_Metrics : <<include>>

' ===== extend =====
UC_Mode <.. UC_Fail : <<extend>>\n仅故障模式

UC_View <.. UC_Topo : <<extend>>\n仅树形算法

@enduml
```

### 用例图逻辑说明与需求分析

有别于对既有功能的简单描述，以下基于系统用例图，从**需求工程 (Requirement Engineering)** 视角剖析研究员或开发者对目标软件的实际诉求与需要解决的核心痛点。

#### 1. 实验控制变量的干预需求 (Configuration Requirements)
为了确保仿真环境能逼真还原真实的 GPU 软硬件环境并具备完备的科学对照性，系统必须满足用户全方位干预实验变量的诉求：
*   **基础环境拟真诉求 (`<<include>>` 设置基础参数)**：系统必须能够让研究员自由设定参与并行计算的规模 (Block数目) 与模拟计算周期的基准长度。更关键的是，为打破理想化模型，系统必须提供“负载波动参数 (Workload Variance)”供用户注入，以复刻 GPU 硬件层面的调度非一致性。
*   **鲁棒性极限测试诉求 (`<<include>>` 选择调度模式 -> `<<extend>>` 高级故障配置)**：在正常的性能对比外，研究员迫切需要评估特定同步算法在部分节点失联、超时等极端环境下的抗死锁能力。因此系统必须支持开启“故障容错模式”，且在该触发路径下游，系统被要求提供精细化的故障注入手段（如故障率、判死阈值调节）。
*   **多样化算法适配诉求 (`<<include>>` 选择栅栏算法)**：系统必须内置学术界最具代表性的几种核心同步理念（高争用/集中式、分摊争用/树形），研究人员需要能自由切换以此为对照核心组进行深入调研。

#### 2. 黑盒过程的强干预与掌控需求 (Execution Control Requirements)
传统的并行环境通常是黑盒甚至难以调试的，在此仿真软件中，研究人员的核心诉求是“时空主宰能力”：
*   **瞬态定格与排错诉求**：研究进程中，当某一线程块发生意料之外的“等待停滞”时，用户必须能够瞬间“暂停”全局滴答逻辑此时钟 (Tick)，定格所有底层并发内存快照便于人工推演排查。
*   **重现与复位诉求**：实验环境因失控、死锁或简单跑完后，系统必须支持极其轻量的状态一键“重置”，无需重启整个平台容器，瞬间清空残余快照等待新一次的下发指令。

#### 3. 可视化洞察与性能论证需求 (Validation & Monitoring Requirements)
让复杂的并发时序转化为直观的图表是该系统最为核心的交付物。系统必须提供“多维度、细粒度”的观测探针：
*   **宏观与微观生命周期跟踪**：无论是哪个算法，研究人员都需要一目了然地确诊每一个单独的 Block 目前究竟处于生命周期的哪一状态节点（在跑、在挂起、亦或是超时挂掉）。
*   **瓶颈透视与热点诊断诉求**：解决锁争用的前提是能看见争用。系统被强势要求将隐藏的“全局统一内存池”进行降维展示，通过颜色深度的“热图”机制直观反映出各个存储通信单元在此次同步中承受了多少的通信频次。
*   **定量性能论证诉求**：图表之外，系统必须要能给出冷冰冰但极具公信力的 KPI 数据总结，即给出总通信开销次数和造成的总同步延迟滴答数，用以直接作为毕业论文/研究结论的定量支撑物。
*   **逻辑结构校验诉求 (`<<extend>>` 查看拓扑结构)**：在对 Tree 或 Static Tree 这类分层算法进行研究和改良时，系统有责任展开该算法生成的黑盒抽象树形父子节点图，帮助开发者验证其在算法层面编写的合并策略与下发广播路径是否建立的完美无误。
