"""
组合树栅栏 (Combining Tree Barrier)

原理：利用树结构减少对根节点的竞争，支持请求合并
优势：减少热点竞争，适合高竞争环境
通信轮数：log₂(N) 轮
适用场景：多核CPU、共享内存系统
"""

from typing import Dict, Any, Tuple
import math
from .barrier_metrics import BarrierMetrics


class CombiningTreeBarrier:
    """
    组合树栅栏 (Combining Tree Barrier)
    
    通过树形结构合并请求，减少对共享变量的竞争。
    每个节点可以合并多个子节点的到达请求。
    """
    
    class Node:
        """组合树节点"""
        def __init__(self, parent=None):
            self.count = 0
            self.limit = 0
            self.sense = False
            self.parent = parent
            self.children = []
            self.locked = False  # 合并时的锁状态（模拟）
    
    def __init__(self, limit: int, logger=None):
        self.limit = limit
        self.logger = logger
        self.released = False
        
        # 树的基数（每个节点的子节点数）
        self.radix = 2
        
        # 构建树结构
        self.nodes = []
        self.leaves = {}  # block_id -> node mapping
        self._build_tree(limit)
        
        # Global sense
        self.global_sense = False
        
        # 性能指标
        self.metrics = BarrierMetrics("CombiningTreeBarrier")
        tree_depth = math.ceil(math.log2(limit)) + 1 if limit > 0 else 0
        self.metrics.set_tree_depth(tree_depth)
    
    def _build_tree(self, num_blocks):
        """构建组合树"""
        # 与TreeBarrier类似的结构
        num_leaves = math.ceil(num_blocks / self.radix)
        current_layer = []
        
        # 创建叶子层
        for i in range(num_leaves):
            node = self.Node()
            managed = min(self.radix, num_blocks - i * self.radix)
            node.limit = managed
            current_layer.append(node)
            self.nodes.append(node)
            
            # 映射block_id
            start_id = i * self.radix
            for b in range(managed):
                self.leaves[start_id + b] = node
        
        # 构建上层
        while len(current_layer) > 1:
            next_layer = []
            num_nodes = math.ceil(len(current_layer) / self.radix)
            for i in range(num_nodes):
                parent = self.Node()
                children_slice = current_layer[i*self.radix : (i+1)*self.radix]
                parent.limit = len(children_slice)
                parent.children = children_slice
                for child in children_slice:
                    child.parent = parent
                
                next_layer.append(parent)
                self.nodes.append(parent)
            current_layer = next_layer
        
        self.root = current_layer[0]
    
    def arrive(self, block_id: int) -> bool:
        """Block到达栅栏"""
        if block_id not in self.leaves:
            return False
        
        # 组合树的关键：合并减少竞争
        # 这里的竞争次数比普通树形栅栏更低
        contention_estimate = math.ceil(math.log2(self.limit) / 2) if self.limit > 1 else 1
        self.metrics.record_contention(contention_estimate)
        
        node = self.leaves[block_id]
        curr = node
        triggered_global = False
        
        while curr:
            # 模拟"combining"：多个Block同时到达时，可以合并请求
            curr.count += 1
            if curr.count == curr.limit:
                curr.count = 0
                if curr.parent:
                    curr = curr.parent
                else:
                    # 到达根节点
                    self._release_tree()
                    triggered_global = True
                    break
            else:
                break
        
        if self.logger:
            self.logger.log_event("BARRIER_ARRIVE", {
                "type": "COMBINING_TREE",
                "block_id": block_id,
                "triggered_release": triggered_global
            })
        
        return triggered_global
    
    def _release_tree(self):
        """释放整棵树"""
        self.root.sense = not self.root.sense
        self.released = True
        self._propagate_sense(self.root)
    
    def _propagate_sense(self, node):
        """传播sense信号"""
        for child in node.children:
            child.sense = node.sense
            self._propagate_sense(child)
    
    
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        """检查是否被释放"""
        node = self.leaves[block_id]
        if local_sense != node.sense:
            return True, node.sense
        return False, local_sense
    
    def is_full(self) -> bool:
        """检查栅栏是否已满"""
        return self.released
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "type": "COMBINING_TREE",
            "root_sense": int(self.root.sense) if self.root else 0,
            "is_released": self.released
        }
    
    def reset_released_flag(self):
        """重置释放标志"""
        self.released = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.get_statistics()
