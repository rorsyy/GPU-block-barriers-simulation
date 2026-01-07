# GPU Barrier Simulation API Documentation

本文件定义了 GPU 栅栏模拟系统的 HTTP API 接口。前端（View 层或独立 Web UI）可以通过这些接口控制仿真流程、切换栅栏算法及获取实时状态。

**Base URL**: `http://localhost:8000/api`
**Web UI**: `http://localhost:8000/` (浏览器直接访问此地址即可进入图形化界面)

## 接口实现状态 (API Implementation Status)
- [x] POST /api/control (START/PAUSE/STEP/RESET)
- [x] GET /api/state

## 1. 仿真控制 (Simulation Control)

### 1.1 启动/恢复仿真
启动新的仿真或从暂停状态恢复。

- **Endpoint**: `/control`
- **Method**: `POST`
- **Content-Type**: `application/json`
- **Body**:
  ```json
  {
    "command": "START"
  }
  ```
- **Response**:
  ```json
  { "status": "ok", "message": "Simulation started" }
  ```

### 1.2 暂停仿真
暂停当前正在运行的仿真。

- **Endpoint**: `/control`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "command": "PAUSE"
  }
  ```

### 1.3 单步调试
在暂停状态下，向前执行 N 个 Tick。

- **Endpoint**: `/control`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "command": "STEP",
    "steps": 1
  }
  ```

### 1.4 重置/配置仿真
重置仿真环境，并可选择性地应用新配置（如切换栅栏类型）。

- **Endpoint**: `/control`
- **Method**: `POST`
- **Body**:
  ```json
  {
    "command": "RESET",
    "config": {
      "num_blocks": 8,
      "barrier_type": "TREE",  // 可选值: "CENTRALIZED", "TREE", "BUTTERFLY"
      "barrier_interval": 100
    }
  }
  ```

## 2. 状态查询 (State Query)

### 2.1 获取当前快照
获取当前仿真帧的完整状态。

- **Endpoint**: `/state`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "tick": 105,
    "simulation_state": "RUNNING",
    "barrier_type": "TREE",
    "blocks": [
      { "id": 0, "state": "RUNNING", "progress": 45.5 },
      { "id": 1, "state": "WAITING_AT_BARRIER", "progress": 50.0 }
    ],
    "barrier": {
      "active": true,
      "count": 3,
      "limit": 8
    }
  }
  ```

## 3. 栅栏类型说明

- **CENTRALIZED**: 集中式栅栏。使用单一全局计数器。适合小规模同步。
- **TREE**: 树形栅栏。节点构成树状结构，减少单点热点竞争。适合中大规模同步。
- **BUTTERFLY**: 蝴蝶形（成对交换）栅栏。多阶段成对同步。通信延迟低，适合特定网络拓扑。
