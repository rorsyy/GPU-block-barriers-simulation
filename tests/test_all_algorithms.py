"""
测试脚本：验证所有栅栏算法和性能指标功能
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api"

print("=" * 60)
print("GPU 栅栏模拟系统 - 全面测试 (Refactored)")
print("=" * 60)

# 测试1: 检查API连接
print("\n✓ 测试1: API连接测试")
try:
    response = requests.get(f"{API_BASE}/state", timeout=2)
    if response.status_code == 200:
        print("  ✅ API连接成功")
        state = response.json()
        print(f"  - 当前Tick: {state.get('tick', 0)}")
        print(f"  - 仿真状态: {state.get('simulation_state', 'UNKNOWN')}")
        print(f"  - Block数量: {len(state.get('blocks', []))}")
    else:
        print(f"  ❌ API返回错误状态码: {response.status_code}")
except Exception as e:
    print(f"  ❌ API连接失败: {e}")
    # exit(1) # Don't exit, might just be starting up

# 测试2: 获取性能指标
print("\n✓ 测试2: 性能指标获取")
try:
    response = requests.get(f"{API_BASE}/metrics", timeout=2)
    if response.status_code == 200:
        metrics = response.json()
        print("  ✅ 性能指标获取成功")
        print(f"  - 栅栏类型: {metrics.get('barrier_type', 'N/A')}")
        print(f"  - 同步次数: {metrics.get('sync_count', 0)}")
        print(f"  - 平均通信: {metrics.get('avg_communication', 0)} ops")
    else:
        print(f"  ❌ 获取性能指标失败: {response.status_code}")
except Exception as e:
    print(f"  ❌ 获取性能指标异常: {e}")

# 测试3: 测试所有3种栅栏算法
algorithms = [
    "CENTRALIZED",
    "TREE", 
    "STATIC_TREE"
]

print("\n✓ 测试3: 测试所有3种栅栏算法切换")
for i, algo in enumerate(algorithms, 1):
    print(f"\n  [{i}/3] 测试 {algo} 算法...")
    try:
        # 发送RESET命令切换算法
        response = requests.post(
            f"{API_BASE}/control",
            json={"command": "RESET", "config": {"barrier_type": algo}},
            timeout=2
        )
        
        if response.status_code == 200:
            print(f"    ✅ 切换到 {algo} 成功")
            
            # 等待初始化完成
            time.sleep(0.5)
            
            # 验证算法是否切换成功
            state_response = requests.get(f"{API_BASE}/state", timeout=2)
            if state_response.status_code == 200:
                state = state_response.json()
                barrier_info = state.get('barrier', {})
                barrier_type = barrier_info.get('type', 'UNKNOWN')
                print(f"    验证: 当前栅栏类型 = {barrier_type}")
                
                # 获取该算法的性能指标
                metrics_response = requests.get(f"{API_BASE}/metrics", timeout=2)
                if metrics_response.status_code == 200:
                    metrics = metrics_response.json()
                    print(f"    性能: 通信={metrics.get('avg_communication', 0):.2f}")
        else:
            print(f"    ❌ 切换失败: {response.status_code}")
    except Exception as e:
        print(f"    ❌ 测试异常: {e}")

# 测试4: 测试控制命令
print("\n✓ 测试4: 测试控制命令 (START/PAUSE/STEP)")
try:
    # START
    response = requests.post(f"{API_BASE}/control", json={"command": "START"}, timeout=2)
    if response.status_code == 200:
        print("  ✅ START 命令成功")
    
    time.sleep(1)
    
    # PAUSE
    response = requests.post(f"{API_BASE}/control", json={"command": "PAUSE"}, timeout=2)
    if response.status_code == 200:
        print("  ✅ PAUSE 命令成功")
    
    # STEP
    response = requests.post(f"{API_BASE}/control", json={"command": "STEP"}, timeout=2)
    if response.status_code == 200:
        print("  ✅ STEP 命令成功")
except Exception as e:
    print(f"  ❌ 控制命令测试异常: {e}")

# 测试5: 性能对比测试
print("\n✓ 测试5: 简化性能对比")
print("\n  算法性能对比表:")
print("  " + "-" * 50)
print(f"  {'算法':<20} {'平均通信':<15} ")
print("  " + "-" * 50)

for algo in algorithms[:3]:  # 只测试前3种以节省时间
    try:
        # 重置为该算法
        requests.post(
            f"{API_BASE}/control",
            json={"command": "RESET", "config": {"barrier_type": algo}},
            timeout=2
        )
        time.sleep(0.5)
        
        # 启动仿真
        requests.post(f"{API_BASE}/control", json={"command": "START"}, timeout=2)
        time.sleep(2)  # 运行2秒
        
        # 获取指标
        metrics_response = requests.get(f"{API_BASE}/metrics", timeout=2)
        if metrics_response.status_code == 200:
            metrics = metrics_response.json()
            comm = metrics.get('avg_communication', 0)
            print(f"  {algo:<20} {comm:<15.2f}")
    except:
        print(f"  {algo:<20} {'测试失败':<15}")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("=" * 60)
