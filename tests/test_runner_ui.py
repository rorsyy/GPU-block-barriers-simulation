# -*- coding: utf-8 -*-
"""
极简版测试前端服务器（左右分布，只显示原始结果确保稳定）
"""

import http.server
import json
import subprocess
import sys
import os
import time

PORT = 8899
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TESTS_DIR)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>GPU仿真 · 测试面板</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333333; height: 100vh; display: flex; flex-direction: column; overflow: hidden; font-size: 16px; }

header { padding: 18px 24px; background: #ffffff; border-bottom: 1px solid #e4e7eb; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
header h1 { margin: 0; font-size: 20px; color: #2c3e50; }

.container { display: flex; flex: 1; overflow: hidden; }

/* 左侧栏 */
.sidebar { width: 340px; background: #ffffff; border-right: 1px solid #e4e7eb; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 8px; }
.sidebar h2 { font-size: 16px; color: #7f8c8d; margin: 18px 0 8px 0; border-bottom: 2px solid #f0f2f5; padding-bottom: 6px; }
.sidebar h2:first-child { margin-top: 0; }

.btn { width: 100%; text-align: left; padding: 12px 14px; background: transparent; color: #4a4a4a; border: 1px solid transparent; border-radius: 6px; cursor: pointer; font-size: 15px; font-weight: 500; font-family: inherit; transition: all 0.2s; }
.btn:hover { background: #f0f3f6; color: #111; }
.btn.running { background: #f39c12; color: #fff; }
.btn.success { border-left: 5px solid #2ecc71; background: #eafaf1; color: #27ae60; }
.btn.error { border-left: 5px solid #e74c3c; background: #fdedec; color: #c0392b; }

.run-all { background: #3498db; color: #ffffff; font-weight: bold; border: none; text-align: center; margin-bottom: 15px; padding: 14px; border-radius: 6px; font-size: 16px; box-shadow: 0 4px 6px rgba(52, 152, 219, 0.2); }
.run-all:hover { background: #2980b9; transform: translateY(-1px); }

/* 右侧内容 */
.main { flex: 1; display: flex; flex-direction: column; background: #f5f7fa; padding: 24px; overflow-y: auto; }
.terminal { background: #ffffff; border-radius: 8px; padding: 20px; font-family: 'Consolas', 'Courier New', monospace; font-size: 15px; line-height: 1.6; color: #2c3e50; min-height: 50vh; white-space: pre-wrap; word-wrap: break-word; overflow-y: auto; border: 1px solid #dcdfe6; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05); }

/* 日志颜色 */
.log-title { color: #2980b9; font-weight: bold; font-size: 16px; margin-bottom: 12px; border-bottom: 1px dashed #e4e7eb; padding-bottom: 8px; }
.log-pass { color: #27ae60; font-weight: bold; }
.log-fail { color: #e74c3c; font-weight: bold; }

::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 5px; }
::-webkit-scrollbar-thumb:hover { background: #c0c4cc; }
</style>
</head>
<body>

<header>
  <h1>GPU 栅栏同步仿真 · 测试面板</h1>
</header>

<div class="container">
  <!-- 左侧控制区 -->
  <div class="sidebar">
    <button class="btn run-all" onclick="runAll()">全部顺次执行</button>

    <h2>单元测试 (Unit)</h2>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestEventBus', this)">EventBus</button>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestBlock', this)">Block 状态机</button>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestBarrierMetrics', this)">BarrierMetrics</button>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestBarrierAtomicInstructions', this)">模拟原子指令</button>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestCentralizedBarrier', this)">集中式栅栏</button>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestTreeBarrier', this)">树形栅栏</button>
    <button class="btn" onclick="runTest('tests/test_unit.py::TestStaticTreeBarrier', this)">静态树栅栏</button>

    <h2>接口测试 (Interface)</h2>
    <button class="btn" onclick="runTest('tests/test_interface.py::TestEventBusRouting', this)">事件路由</button>
    <button class="btn" onclick="runTest('tests/test_interface.py::TestSchedulerBlockInterface', this)">调度器->块接口</button>
    <button class="btn" onclick="runTest('tests/test_interface.py::TestSchedulerReleaseInterface', this)">栅栏释放恢复</button>
    <button class="btn" onclick="runTest('tests/test_interface.py::TestFailureSchedulerInterface', this)">失效调度与注入</button>
    <button class="btn" onclick="runTest('tests/test_interface.py::TestBarrierMetricsInterface', this)">通信量打点日志</button>
    <button class="btn" onclick="runTest('tests/test_interface.py::TestModelBarrierArrivalInterface', this)">Model层接口适配</button>

    <h2>整体架构测试 (Integration)</h2>
    <button class="btn" onclick="runTest('tests/test_integration.py::TestModelInitialization', this)">依赖注入初始化</button>
    <button class="btn" onclick="runTest('tests/test_integration.py::TestSingleSyncCycle', this)">单轮同步(端到端)</button>
    <button class="btn" onclick="runTest('tests/test_integration.py::TestMultiSyncCycles', this)">多轮反复同步</button>
    <button class="btn" onclick="runTest('tests/test_integration.py::TestSnapshotIntegrity', this)">内存快照一致性</button>
    <button class="btn" onclick="runTest('tests/test_integration.py::TestAlgorithmConsistency', this)">算法一致性比对</button>
    <button class="btn" onclick="runTest('tests/test_integration.py::TestFailureModeIntegration', this)">崩溃恢复全流程</button>
  </div>

  <!-- 右侧终端输出区 -->
  <div class="main">
    <div class="terminal" id="term">
<span style='color:#7f9f7f;'>准备就绪。点击左侧的测试按钮开始捕获 CMD 执行结果...</span>
    </div>
  </div>
</div>

<script>
function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

function processLog(text) {
    let esc = escapeHtml(text);
    // 简单的关键词染色
    esc = esc.replace(/PASSED/g, "<span class='log-pass'>PASSED</span>");
    esc = esc.replace(/FAILED/g, "<span class='log-fail'>FAILED</span>");
    esc = esc.replace(/ERROR/g, "<span class='log-fail'>ERROR</span>");
    esc = esc.replace(/===.+===/g, match => `<span style='color:#c678dd;'>${match}</span>`);
    return esc;
}

async function runTest(target, btnEl) {
    const term = document.getElementById('term');
    
    // 还原所有按钮状态
    if (!document.isRunAll) {
        document.querySelectorAll('.btn:not(.run-all)').forEach(b => {
             b.className = 'btn';
        });
    }
    
    btnEl.className = 'btn running';
    term.innerHTML = `<div class="log-title">🚀 正在执行: pytest ${target}</div>运行中，请稍候...<br/><br/>`;

    try {
        const res = await fetch('/api/run', {
            method: 'POST',
            body: JSON.stringify({ target: target })
        });
        
        if (!res.ok) throw new Error("服务器返回异常状态码: " + res.status);
        
        const data = await res.json();
        const success = (data.return_code === 0);
        
        btnEl.className = success ? 'btn success' : 'btn error';
        
        // 渲染终端输出
        term.innerHTML = `<div class="log-title">📋 结果报表 (${data.duration}s): ${target}</div>`;
        term.innerHTML += processLog(data.output);

    } catch (e) {
        btnEl.className = 'btn error';
        term.innerHTML = `<span class='log-fail'>网络或系统错误: ${e.message}</span>`;
    }
}

async function runAll() {
    document.querySelectorAll('.btn:not(.run-all)').forEach(b => b.className = 'btn');
    document.isRunAll = true;
    const btns = Array.from(document.querySelectorAll('.sidebar .btn:not(.run-all)'));
    
    for(let i=0; i<btns.length; i++){
        await runTest(btns[i].getAttribute('onclick').match(/'([^']+)'/)[1], btns[i]);
    }
    document.isRunAll = false;
}
</script>
</body>
</html>
"""

class TestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

    def do_POST(self):
        if self.path == '/api/run':
            length = int(self.headers['Content-Length'])
            req_body = self.rfile.read(length)
            
            try:
                data = json.loads(req_body)
                target = data.get('target', '')
                
                start_time = time.time()
                
                # 最纯粹稳定的执行方式，加入 --cov 提供强有力的测试实证结果！
                cmd = [sys.executable, "-m", "pytest", target, "-v", "-s", "--cov=src", "--cov-report=term-missing"]
                
                # 设置环境变量，强制 Python 不使用 GBK 而使用 UTF-8
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                
                process = subprocess.run(
                    cmd,
                    cwd=PROJECT_DIR,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace',
                    env=env
                )
                
                output = process.stdout + "\n" + process.stderr
                return_code = process.returncode
                duration = round(time.time() - start_time, 2)
                
            except Exception as e:
                output = f"后台执行异常: {str(e)}"
                return_code = -1
                duration = 0

            # 确保序列化一定能通过
            json_str = json.dumps({
                "output": output,
                "return_code": return_code,
                "duration": duration
            }, ensure_ascii=False)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json_str.encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass # 完全静默，杜绝一切终端编码导致崩溃的问题


if __name__ == '__main__':
    server = http.server.HTTPServer(('localhost', PORT), TestHandler)
    print(f"极简测试终端服务已启动: http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已关闭。")
        server.server_close()
