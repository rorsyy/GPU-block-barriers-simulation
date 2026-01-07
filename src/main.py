import sys
import os

# 将 src 目录添加到 Python 的模块搜索路径中
# 这确保了我们可以直接 import model, controller 等包，而不需要处理相对导入的复杂性
sys.path.append(os.path.join(os.path.dirname(__file__), "."))

from controller.simulation_controller import SimulationController
from view.console_view import ConsoleView

def main():
    """
    程序主入口函数 (Main Entry Point)
    
    负责：
    1. 确定配置文件的路径。
    2. 实例化 Controller (核心控制逻辑)。
    3. 实例化 View (显示层)。
    4. 将 View 注入到 Controller 中，完成组装。
    5. 启动仿真循环，并处理用户中断 (Ctrl+C)。
    """
    
    # 构造默认配置文件的绝对路径
    # 假设目录结构: src/main.py, config/default_scenario.json
    base_dir = os.path.dirname(os.path.dirname(__file__)) # 获取项目根目录 (即 src 的上一级)
    config_path = os.path.join(base_dir, "config", "default_scenario.json")
    
    print(f"正在启动 GPU 栅栏模拟系统...")
    print(f"加载配置文件: {config_path}")
    
    # 1. 初始化控制器
    try:
        controller = SimulationController(config_path)
    except FileNotFoundError:
        print(f"错误: 找不到配置文件 {config_path}")
        return

    # 2. 初始化视图 (控制台视图)
    view = ConsoleView()
    
    # 3. 依赖注入
    controller.set_view(view)
    
    print("仿真已就绪。按 Ctrl+C 可随时停止。")
    print("Starting simulation...")
    
    # 4. 启动主循环
    try:
        controller.start()
    except KeyboardInterrupt:
        # 捕获 Ctrl+C 中断，优雅退出
        print("\n用户终止了仿真。")
    except Exception as e:
        print(f"\n发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
    
if __name__ == "__main__":
    main()
