"""
全局内存 (Global Memory) 模块

在真实 GPU 硬件中，全局内存是一块被动的物理存储介质 (DRAM)，
本身不具备任何计算能力。所有的原子操作 (atomicAdd / atomicExch)
均由 SM (Streaming Multiprocessor) 发起并完成。

本类严格遵循该硬件语义，仅提供最基础的 read / write 接口，
不包含任何业务逻辑或通信打点行为。
"""
from typing import Dict, Any


class GlobalMemory:
    """
    全局内存 —— 被动存储介质。

    职责：
      - 存储共享变量（如 counter、sense、各树节点状态等）
      - 提供 read / write / get_snapshot 三个纯粹的访存接口
    """

    def __init__(self, initial: Dict[str, Any] = None):
        """
        :param initial: 可选的初始内存内容
        """
        self._memory: Dict[str, Any] = dict(initial) if initial else {}

    def read(self, key: str, default: Any = 0) -> Any:
        """
        读取指定键的值。

        :param key:     内存变量名
        :param default: 若不存在时的默认值
        :return:        当前存储的值
        """
        return self._memory.get(key, default)

    def write(self, key: str, value: Any) -> None:
        """
        写入指定键的值。

        :param key:   内存变量名
        :param value: 要写入的值
        """
        self._memory[key] = value

    def get_snapshot(self) -> Dict[str, Any]:
        """
        获取全局内存当前状态的完整快照（浅拷贝）。
        """
        return self._memory.copy()
