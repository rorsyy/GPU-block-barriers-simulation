import os

class ConsoleView:
    """
    控制台视图 (Console View) 类
    
    负责将仿真模型的实时状态渲染到命令行终端。
    虽然本项目最终目标可能包括 GUI，但控制台视图对于早期调试、
    验证逻辑以及在无图形界面服务器上运行非常重要。
    """
    
    def render(self, snapshot: dict):
        """
        渲染一帧画面。
        
        :param snapshot: 由 SimulationModel.get_snapshot() 生成的状态字典。
                         包含 tick, blocks, barrier 等信息。
        """
        # 清屏操作 (可选)。
        # 为了避免 flicker (闪烁) 和保留滚动历史，这里暂时注释掉。
        # 如果需要类似动画的效果，可以取消注释。
        # os.system('cls' if os.name == 'nt' else 'clear')
        
        tick = snapshot.get('tick', 0)
        blocks = snapshot.get('blocks', [])
        barrier = snapshot.get('barrier', {})
        
        # 1. 打印全局状态头信息
        # 显示当前时钟 Tick，栅栏计数器状态 (Count/Limit)，以及当前的 Sense (0/1)
        barrier_info = f"Barrier: {barrier.get('count', 0)}/{barrier.get('limit', '?')}"
        sense_info = f"Sense: {barrier.get('sense', 0)}"
        print(f"Tick: {tick:5d} | {barrier_info} | {sense_info}")
        
        # 2. 打印每个 Block 的简要状态
        # 为了在控制台一行内显示多个 Block，我们使用精简的符号：
        # [.] - RUNNING (运行中)
        # [#] - WAITING (等待栅栏)
        # [F] - FINISHED (完成)
        line = ""
        for b in blocks:
            state = b.get('state', 'UNKNOWN')
            symbol = "?"
            if state == 'RUNNING':
                symbol = "."
            elif state == 'WAITING_AT_BARRIER':
                symbol = "#"
            elif state == 'FINISHED':
                symbol = "F"
            
            # 格式: ID:符号 (例如 0:. 1:#)
            line += f"{b.get('id', '?')}:{symbol} "
            
        print(line)
        print("-" * 40) # 分隔线
