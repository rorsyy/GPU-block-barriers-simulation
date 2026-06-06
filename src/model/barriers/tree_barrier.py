"""
树形栅栏 (Tree Barrier)
"""
from typing import Dict, Any, Tuple
import math
from ..barrier_metrics import BarrierMetrics
from ..barrier import Barrier
from ..global_memory import GlobalMemory

class TreeBarrier(Barrier):
    """
    树形栅栏
    """
    class Node:
        def __init__(self, id, parent=None):
            self.id = id 
            self.count = 0
            self.limit = 0
            self.sense = False
            self.parent = parent
            self.children = []
            
    def __init__(self, limit: int, logger=None):
        super().__init__(limit, logger)
        self.radix = 2
        self.nodes = []
        self.leaves = {} 
        self._build_tree(limit)
        self.metrics = BarrierMetrics("TreeBarrier")
        self._update_memory_snapshot()

    def _build_tree(self, num_blocks):
        num_leaves = math.ceil(num_blocks / self.radix)
        current_layer = []
        node_counter = 0
        
        for i in range(num_leaves):
            node = self.Node(f"node_{node_counter}")
            node_counter += 1
            managed = min(self.radix, num_blocks - i * self.radix)
            node.limit = managed
            current_layer.append(node)
            self.nodes.append(node)
            start_id = i * self.radix
            for b in range(managed):
                self.leaves[start_id + b] = node
        
        while len(current_layer) > 1:
            next_layer = []
            num_nodes = math.ceil(len(current_layer) / self.radix)
            for i in range(num_nodes):
                parent = self.Node(f"node_{node_counter}")
                node_counter += 1
                children_slice = current_layer[i*self.radix : (i+1)*self.radix]
                parent.limit = len(children_slice)
                parent.children = children_slice
                for child in children_slice:
                    child.parent = parent
                next_layer.append(parent)
                self.nodes.append(parent)
            current_layer = next_layer
        self.root = current_layer[0] if current_layer else None
        if self.root and self.root not in self.nodes:
            self.nodes.append(self.root)

    def _update_memory_snapshot(self):
        for node in self.nodes:
            self.mem.write(f"{node.id}.count", node.count)
            self.mem.write(f"{node.id}.sense", int(node.sense))

    def arrive(self, block_id: int, tick: int = 0) -> bool:
        self.metrics.record_arrival(block_id, tick)
        if block_id not in self.leaves:
            return False
            
        node = self.leaves[block_id]
        self.metrics.record_communication(1)
        
        curr = node
        triggered_global = False
        
        while curr:
            curr.count += 1
            if curr.count == curr.limit:
                curr.count = 0
                if curr.parent:
                    self.metrics.record_communication(1)
                    curr = curr.parent
                else:
                    self._release_tree(tick)
                    triggered_global = True
                    break
            else:
                break
        
        self._update_memory_snapshot()
        
        if self.logger:
             self.logger.log_event("BARRIER_ARRIVE", {"type": "TREE", "block_id": block_id})
        return triggered_global

    def _release_tree(self, tick: int = 0):
        if self.root:
            self.root.sense = not self.root.sense
            self.released = True
            self._propagate_sense(self.root)
            self.metrics.record_release(tick)

    def _propagate_sense(self, node):
        for child in node.children:
            self.metrics.record_communication(1)
            child.sense = node.sense
            self._propagate_sense(child)

    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        node = self.leaves[block_id]
        self.metrics.record_communication(1)
        if local_sense != node.sense:
            return True, node.sense
        return False, local_sense

    def is_full(self) -> bool:
        return self.released

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "TREE",
            "root_sense": int(self.root.sense) if self.root else 0,
            "is_released": self.released
        }

    def get_topology(self) -> Dict[str, Any]:
        nodes_data = []
        for node in self.nodes:
            nodes_data.append({
                "id": node.id,
                "parent": node.parent.id if node.parent else None,
                "children": [c.id for c in node.children],
                "count": node.count,
                "limit": node.limit
            })
        leaves_data = {block_id: node.id for block_id, node in self.leaves.items()}
        return {
            "nodes": nodes_data,
            "leaves": leaves_data
        }
