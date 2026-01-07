"""
静态树栅栏 (Static Tree Barrier)

原理：预先分配的完全二叉树结构，Arrival Tree + Release Tree
优势：避免动态构建开销，缓存友好
通信轮数：log₂(N) 轮
适用场景：线程块数量固定的场景
"""

from typing import Dict, Any, Tuple
import math
from .barrier_metrics import BarrierMetrics


class StaticTreeBarrier:
    """
    静态树栅栏 (Static Tree Barrier)
    
    使用预先构建的静态树结构，性能优于动态树。
    分为两个阶段：
    1. Arrival Phase: 向上传播到达信号
    2. Release Phase: 从根向下传播释放信号
    """
    
    class StaticNode:
        """静态树节点"""
        def __init__(self, node_id):
            self.id = node_id
            self.count = 0
            self.limit = 0
            self.sense = False
            self.parent_id = None
            self.children_ids = []
    
    def __init__(self, limit: int, logger=None):
        self.limit = limit
        self.logger = logger
        self.released = False
        
        # 预先构建静态树
        self.tree_depth = math.ceil(math.log2(limit)) + 1 if limit > 0 else 1
        self.nodes = {}  # node_id -> StaticNode
        self.block_to_node = {}  # block_id -> node_id
        
        self._build_static_tree(limit)
        
        # Global sense
        self.global_sense = False
        
        # 性能指标
        self.metrics = BarrierMetrics("StaticTreeBarrier")
        self.metrics.set_tree_depth(self.tree_depth)
    
    def _build_static_tree(self, num_blocks):
        """构建静态完全二叉树"""
        if num_blocks == 0:
            return
        
        # 计算总节点数（叶子节点 + 内部节点）
        # 对于完全二叉树，如果有N个叶子，约需要N-1个内部节点
        total_nodes = num_blocks * 2 - 1 if num_blocks > 1 else 1
        
        # 创建所有节点
        for i in range(total_nodes):
            self.nodes[i] = self.StaticNode(i)
        
        # 建立父子关系（使用数组表示的完全二叉树）
        for i in range(total_nodes):
            left_child = 2 * i + 1
            right_child = 2 * i + 2
            
            if left_child < total_nodes:
                self.nodes[i].children_ids.append(left_child)
                self.nodes[left_child].parent_id = i
            
            if right_child < total_nodes:
                self.nodes[i].children_ids.append(right_child)
                self.nodes[right_child].parent_id = i
        
        # 计算每个节点需要等待的子节点数
        for node in self.nodes.values():
            node.limit = len(node.children_ids) if node.children_ids else 1
        
        # 映射block到叶子节点
        # 叶子节点是倒数 num_blocks 个节点
        leaf_start = total_nodes - num_blocks
        for i in range(num_blocks):
            self.block_to_node[i] = leaf_start + i
        
        self.root_id = 0
    
    def arrive(self, block_id: int) -> bool:
        """Block到达栅栏"""
        if block_id not in self.block_to_node:
            return False
        
        # 静态树的竞争非常低（缓存友好，预分配）
        contention_estimate = max(1, math.ceil(math.log2(self.limit) * 0.5))
        self.metrics.record_contention(contention_estimate)
        
        node_id = self.block_to_node[block_id]
        current_id = node_id
        triggered_global = False
        
        while current_id is not None:
            node = self.nodes[current_id]
            node.count += 1
            
            if node.count >= node.limit:
                node.count = 0
                if node.parent_id is not None:
                    current_id = node.parent_id
                else:
                    # 到达根节点
                    self._release_tree()
                    triggered_global = True
                    break
            else:
                break
        
        if self.logger:
            self.logger.log_event("BARRIER_ARRIVE", {
                "type": "STATIC_TREE",
                "block_id": block_id,
                "triggered_release": triggered_global
            })
        
        return triggered_global
    
    def _release_tree(self):
        """释放整棵树"""
        root = self.nodes[self.root_id]
        root.sense = not root.sense
        self.global_sense = root.sense
        self.released = True
        
        # 传播到所有节点
        self._propagate_sense(self.root_id)
    
    def _propagate_sense(self, node_id):
        """递归传播sense"""
        node = self.nodes[node_id]
        for child_id in node.children_ids:
            child = self.nodes[child_id]
            child.sense = node.sense
            self._propagate_sense(child_id)
    
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        """检查是否被释放"""
        if block_id not in self.block_to_node:
            return False, local_sense
        
        node_id = self.block_to_node[block_id]
        node = self.nodes[node_id]
        
        if local_sense != node.sense:
            return True, node.sense
        return False, local_sense
    
    def is_full(self) -> bool:
        """检查栅栏是否已满"""
        return self.released
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        root = self.nodes[self.root_id]
        return {
            "type": "STATIC_TREE",
            "root_sense": int(root.sense),
            "tree_depth": self.tree_depth,
            "is_released": self.released
        }
    
    def reset_released_flag(self):
        """重置释放标志"""
        self.released = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.get_statistics()
