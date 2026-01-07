import json
import time

class SimulationLogger:
    """
    仿真日志记录器 (Simulation Logger)
    
    负责将系统运行过程中的关键事件记录到持久化存储（如文本文件）。
    日志格式采用 JSON Lines (NDJSON)，即每一行是一个合法的 JSON 对象。
    这种格式便于后续的脚本解析、数据分析或“时光倒流”回放功能的实现。
    """
    def __init__(self, filepath="trace.log"):
        """
        初始化日志记录器。
        
        :param filepath: 日志文件的保存路径。默认保存到当前目录的 trace.log。
        """
        self.filepath = filepath
        # 使用 utf-8 编码打开文件，以支持中文字符（如果有）
        self.file = open(self.filepath, "w", encoding="utf-8")
        
    def log_event(self, event_type: str, details=None):
        """
        记录一条事件。
        
        :param event_type: 事件类型字符串，如 "STEP", "BARRIER_ARRIVE", "BLOCK_WAIT" 等。
                           统一的大写命名有助于后续过滤。
        :param details: 字典类型的详细信息。例如 {"block_id": 1, "progress": 50.5}。
        """
        if details is None:
            details = {}
        
        # 构造日志记录对象
        record = {
            "event": event_type,
            "timestamp": time.time(), # 物理时间戳，用于性能分析
            **details                 # 展开详细信息
        }
        
        # 写入文件并立即刷新缓冲区，防止程序崩溃时日志丢失
        self.file.write(json.dumps(record) + "\n")
        self.file.flush()

    def close(self):
        """
        关闭日志文件句柄。应在程序退出时调用。
        """
        if self.file:
            self.file.close()
