"""
静态树栅栏 (Static Tree Barrier)
"""

from typing import Dict, Any, Tuple
import math
from ..barrier_metrics import BarrierMetrics
from ..barrier import Barrier
from ..global_memory import GlobalMemory

class StaticTreeBarrier(Barrier):
    """
    静态树栅栏 (Static Tree Barrier)
    """
    
    class StaticNode:
        def __init__(self, node_id):
            self.id = node_id
            self.count = 0
            self.limit = 0
            self.sense = False
            self.parent_id = None
            self.children_ids = []
    
    def __init__(self, limit: int, logger=None):
        super().__init__(limit, logger)
        
        self.tree_depth = math.ceil(math.log2(limit)) + 1 if limit > 0 else 1
        self.nodes = {}  # node_id -> StaticNode
        self.block_to_node = {}  # block_id -> node_id
        
        self._build_static_tree(limit)
        
        self.global_sense = False
        self.metrics = BarrierMetrics("StaticTreeBarrier")
        
        self.mem = GlobalMemory()
        for nid in self.nodes:
            self.mem.write(f"node{nid}.count", 0)
            self.mem.write(f"node{nid}.sense", 0)

    def _build_static_tree(self, num_blocks):
        if num_blocks == 0:
            return
        
        total_nodes = num_blocks * 2 - 1 if num_blocks > 1 else 1
        
        for i in range(total_nodes):
            self.nodes[i] = self.StaticNode(i)
        
        for i in range(total_nodes):
            left_child = 2 * i + 1
            right_child = 2 * i + 2
            
            if left_child < total_nodes:
                self.nodes[i].children_ids.append(left_child)
                self.nodes[left_child].parent_id = i
            
            if right_child < total_nodes:
                self.nodes[i].children_ids.append(right_child)
                self.nodes[right_child].parent_id = i
        
        for node in self.nodes.values():
            node.limit = len(node.children_ids) if node.children_ids else 1
        
        leaf_start = total_nodes - num_blocks
        for i in range(num_blocks):
            self.block_to_node[i] = leaf_start + i
        
        self.root_id = 0
    
    def arrive(self, block_id: int, tick: int = 0) -> bool:
        self.metrics.record_arrival(block_id, tick)
        if block_id not in self.block_to_node:
            return False
        
        self.metrics.record_communication(1)
        
        node_id = self.block_to_node[block_id]
        current_id = node_id
        triggered_global = False
        
        while current_id is not None:
            node = self.nodes[current_id]
            node.count += 1
            self.mem.write(f"node{node.id}.count", node.count)
            
            if node.count >= node.limit:
                node.count = 0
                self.mem.write(f"node{node.id}.count", 0)
                
                if node.parent_id is not None:
                    self.metrics.record_communication(1)
                    current_id = node.parent_id
                else:
                    self._release_tree(tick)
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

    def _release_tree(self, tick: int = 0):
        root = self.nodes[self.root_id]
        root.sense = not root.sense
        self.global_sense = root.sense
        self.released = True
        self.metrics.record_release(tick)
        self._propagate_sense(self.root_id)
    
    def _propagate_sense(self, node_id):
        node = self.nodes[node_id]
        self.mem.write(f"node{node.id}.sense", int(node.sense))
        
        for child_id in node.children_ids:
            child = self.nodes[child_id]
            self.metrics.record_communication(1)
            child.sense = node.sense
            self._propagate_sense(child_id)
    
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        if block_id not in self.block_to_node:
            return False, local_sense
        
        node_id = self.block_to_node[block_id]
        node = self.nodes[node_id]
        
        self.metrics.record_communication(1)
        
        if local_sense != node.sense:
            return True, node.sense
        return False, local_sense
    
    def is_full(self) -> bool:
        return self.released
    
    def get_status(self) -> Dict[str, Any]:
        root = self.nodes[self.root_id]
        return {
            "type": "STATIC_TREE",
            "root_sense": int(root.sense),
            "tree_depth": self.tree_depth,
            "is_released": self.released
        }

    def get_topology(self) -> Dict[str, Any]:
        nodes_data = []
        for node_id, node in self.nodes.items():
            nodes_data.append({
                "id": str(node.id),
                "parent": str(node.parent_id) if node.parent_id is not None else None,
                "children": [str(c) for c in node.children_ids],
                "count": node.count,
                "limit": node.limit
            })
        leaves_data = {block_id: str(node_id) for block_id, node_id in self.block_to_node.items()}
        return {
            "nodes": nodes_data,
            "leaves": leaves_data
        }
