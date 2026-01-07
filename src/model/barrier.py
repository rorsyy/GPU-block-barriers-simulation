from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import math
from .barrier_metrics import BarrierMetrics

class Barrier(ABC):
    """
    栅栏 (Barrier) 抽象基类
    定义所有栅栏算法必须遵循的通用接口。
    """
    def __init__(self, limit: int, logger=None):
        self.limit = limit
        self.logger = logger
        self.released = False
        # 性能指标收集器（由子类在初始化时设置正确的名称）
        self.metrics = None
        # self.sense 移除，由各子类自行维护或仅用于 Debug

    @abstractmethod
    def arrive(self, block_id: int) -> bool:
        """
        Block 尝试到达栅栏。
        :return: 是否触发了释放 (对于集中式通常是最后一个到达者触发，对于分布式可能是局部触发)
        """
        pass

    @abstractmethod
    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        """
        检查指定 Block 是否被释放。
        :param block_id: 查询的 Block ID
        :param local_sense: Block 当前持有的 sense
        :return: (is_released, new_sense)
        """
        pass

    @abstractmethod
    def is_full(self) -> bool:
        """检查栅栏是否已满"""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取内部状态快照"""
        pass
    
    def reset_released_flag(self):
        """重置UI显示的释放标志"""
        self.released = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标统计"""
        if self.metrics:
            return self.metrics.get_statistics()
        return {}


class CentralizedBarrier(Barrier):
    """
    集中式栅栏 (Centralized Barrier)
    """
    def __init__(self, limit: int, logger=None):
        super().__init__(limit, logger)
        self.count = 0
        self.sense = False
        # 初始化性能指标收集器
        self.metrics = BarrierMetrics("CentralizedBarrier") 

    def arrive(self, block_id: int) -> bool:
        # 记录竞争次数（集中式栅栏的竞争发生在全局计数器）
        self.metrics.record_contention(1)
        
        self.count += 1
        
        if self.logger:
            self.logger.log_event("BARRIER_ARRIVE", {
                "type": "CENTRALIZED", 
                "block_id": block_id, 
                "count": self.count, 
                "limit": self.limit
            })

        if self.count >= self.limit:
            self.release_all()
            return True
        return False

    def release_all(self):
        old_sense = self.sense
        self.sense = not self.sense
        self.count = 0
        self.released = True
        
        # 记录释放时间（使用当前tick，由外部传入或使用占位符）
        # 注意：这里无法获取当前tick，需要在调用时传入或从外部获取
        # 暂时使用0作为占位符，后续优化
        
        if self.logger:
            self.logger.log_event("BARRIER_RELEASE", {
                "type": "CENTRALIZED",
                "sense_flip": f"{int(old_sense)}->{int(self.sense)}"
            })

    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        # 集中式：只需要对比全局 sense
        if local_sense != self.sense:
            return True, self.sense
        return False, local_sense

    def is_full(self) -> bool:
        return self.count >= self.limit

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "CENTRALIZED",
            "count": self.count,
            "limit": self.limit,
            "sense": int(self.sense),
            "is_released": self.released
        }


class TreeBarrier(Barrier):
    """
    树形栅栏 (Tree Barrier)
    
    模拟一个二叉树结构。
    Block Arrive -> Leaf -> Parent -> ... -> Root.
    Release -> Root -> ... -> Leaf -> Block.
    """
    class Node:
        def __init__(self, parent=None):
            self.count = 0
            self.limit = 0 # 需要等待几个孩子/block
            self.sense = False
            self.parent = parent
            self.children = []
            
    def __init__(self, limit: int, logger=None):
        super().__init__(limit, logger)
        self.radix = 2 # 二叉树
        self.nodes = [] # 存储所有节点以便可视化
        self.leaves = {} # map block_id -> leaf_node
        self._build_tree(limit)
        # 初始化性能指标收集器
        self.metrics = BarrierMetrics("TreeBarrier")
        # 计算树深度
        tree_depth = math.ceil(math.log2(limit)) + 1 if limit > 0 else 0
        self.metrics.set_tree_depth(tree_depth)
        
    def _build_tree(self, num_blocks):
        # 这是一个简化版的构建，假设完全二叉树
        # 真实硬件中可能有专门的物理布局
        # 我们自底向上构建：先创建 num_blocks 个 Leaf slot (逻辑)
        # 每个 LeafNode 管理 radix 个 Block
        
        # 1. 计算需要的 Leaf Node 数量
        num_leaves = math.ceil(num_blocks / self.radix)
        current_layer = []
        
        # 创建叶子层
        for i in range(num_leaves):
            node = self.Node()
            # 计算该节点管理的 block 数量 (处理剩余不足 radix 的情况)
            # 例如 8 blocks, radix 2 -> 4 nodes, each manages 2
            managed = min(self.radix, num_blocks - i * self.radix)
            node.limit = managed
            current_layer.append(node)
            self.nodes.append(node)
            
            # 映射 block_id
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
        if block_id not in self.leaves:
            return False # Should not happen
            
        node = self.leaves[block_id]
        
        # 记录竞争次数（树形栅栏的竞争分散在各个节点）
        # 粗略估算：每层都有一次竞争
        contention_estimate = math.ceil(math.log2(self.limit)) if self.limit > 1 else 1
        self.metrics.record_contention(contention_estimate)
        
        # 递归（或循环）向上更新
        # 简化模拟：假设瞬间向上传播，不模拟中间的网络延迟
        # 真实模拟中，可能需要 state machine 逐步推进
        
        curr = node
        triggered_global = False
        
        while curr:
            curr.count += 1
            if curr.count == curr.limit:
                # 本节点满，重置计数，并尝试触发父节点
                curr.count = 0
                if curr.parent:
                    curr = curr.parent # 继续循环处理父节点
                else:
                    # 到达根节点 -> 触发释放
                    self._release_tree()
                    triggered_global = True
                    break
            else:
                # 阻塞在当前节点
                break
                
        if self.logger:
             self.logger.log_event("BARRIER_ARRIVE", {
                "type": "TREE", 
                "block_id": block_id,
                "triggered_release": triggered_global
            })
        return triggered_global

    def _release_tree(self):
        # 从根节点开始翻转 sense
        # 在真实硬件中，这是一个向下传播的过程
        # 这里我们直接翻转所有节点的 sense，或者只翻转 root，让子节点根据父节点 sense 翻转
        # 采用 standard tree barrier logic:
        # Root sense flips. Children see parent sense flip, then flip their own.
        # 既然是 instants simulation，我们简化：
        # 翻转 Root sense。check_release 逻辑负责递归检查。
        self.root.sense = not self.root.sense
        self.released = True
        
        # 为了让 check_release 简单，我们可以“推”更变到所有节点，或者“拉”
        # 这里采用：递归更新全树 sense，模拟传播完成
        self._propagate_sense(self.root)
        
    def _propagate_sense(self, node):
        # 这是一个模拟 hack，表示信号瞬间传遍全树
        for child in node.children:
            child.sense = node.sense
            self._propagate_sense(child)

    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        # Block 检查其所属叶子节点的 sense
        node = self.leaves[block_id]
        if local_sense != node.sense:
            return True, node.sense
        return False, local_sense

    def is_full(self) -> bool:
        return self.released # 简化判断

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "TREE",
            "root_sense": int(self.root.sense) if self.root else 0,
            "is_released": self.released
        }


class ButterflyBarrier(Barrier):
    """
    蝴蝶形栅栏 (Butterfly Barrier)
    
    多阶段成对交换同步。
    Stage k: sync with (id XOR 2^k).
    需要 log2(N) 个阶段。
    """
    def __init__(self, limit: int, logger=None):
        super().__init__(limit, logger)
        self.num_stages = math.ceil(math.log2(limit)) if limit > 1 else 1
        # 存储每个 Block 当前处于第几个阶段
        # block_stages[id] = k (0..num_stages)
        # 当 == num_stages 时，表示该 Block 完成了本轮 Barrier
        self.block_stages = {i: 0 for i in range(limit)}
        
        # 存储每一轮的 sense
        # butterfly 通常不使用单一的 global sense，而是每一轮交互都有握手
        # 这里为了适配接口，我们让 block 完成所有 stage 后，获得一个新的 global_sense
        self.global_sense = False
        
        # 存储 Block 在当前 Stage 是否已经 Arrive
        # 结构：arrived[stage][block_id] = True/False
        # 这种数据结构需要在每次 barrier 完成后通过某种方式重置?
        # 更好的方式：使用奇偶轮次或者 incrementing epoch
        self.epoch = 0 # 当前的栅栏轮次
        self.arrived_state = {} #(epoch, stage, block_id) -> bool
        # 初始化性能指标收集器
        self.metrics = BarrierMetrics("ButterflyBarrier")
        # 记录通信轮数（每次同步需要log2(N)轮）
        self.metrics.communication_rounds = self.num_stages

    def arrive(self, block_id: int) -> bool:
        # Butterfly 比较特殊，Block会多次调用 arrive (每完成一个 stage)
        # 但现在的 Block.py 逻辑是：arrive -> wait -> update_sense -> resume
        # 原有模型是“一次性” barrier。
        # 为了适配，我们在内部模拟所有 stage 的瞬间/快速完成，或者修改 Block 行为。
        # 鉴于题目是“模拟”，我们假设 Block 调用一次 arrive，
        # 然后我们在内部模拟“如果所有 peers 都到了，就推进”。
        
        # 这里简化实现：当所有人都调用了 arrive，才释放。
        # 这其实退化成了 Centralized 的行为，失去了 Butterfly 的“局部性”演示意义。
        
        # 正确的 Butterfly 模拟应当是：
        # Block 不只是 check global sense，而是 check "Peer Ready".
        # 但 check_release 接口只能返回 True/False。
        
        # 方案：
        # 内部维护 counts。
        # Butterfly 的特性是：不需要所有人到齐，只要我的伙伴们到齐，我就可以过。
        # 但为了保持 Block 代码通用，我们只能用 check_release 模拟。
        
        # 既然是模拟 Barrier *机制*，我们保留 Centralized 的外壳，
        # 但内部逻辑记录“伙伴”关系。
        # 由于 Block 模型简单 (RUNNING -> WAITING)，
        # 我们在这里只能做一个近似：ButterflyBarrier 依然等所有人，但在 log 中打印成对交互。
        
        # 或者：让 check_release 在伙伴到达时就返回 True？
        # 如果 Block A 的伙伴 B 到了，A 可以通过 barrier 吗？
        # 不可以，A 必须等所有 stages 完成。
        # 所以对于 Block 而言，依然是“进 -> 等 -> 出”。
        # 区别在于内部状态。
        
        # 记录竞争次数（蝴蝶形的竞争较低，约log2(N)次）
        self.metrics.record_contention(self.num_stages)
        
        self.block_stages[block_id] = 0 # Reset stage
        self._record_arrival(block_id)
        
        # 检查是否全部到达 (简单的一致性检查)
        all_arrived = len(self.arrived_state) >= self.limit
        if all_arrived:
             self.release_all()
             return True
             
        return False

    def _record_arrival(self, block_id):
        self.arrived_state[block_id] = True
        if self.logger:
             self.logger.log_event("BARRIER_ARRIVE", {"type": "BUTTERFLY", "block_id": block_id})

    def release_all(self):
        old_sense = self.global_sense
        self.global_sense = not self.global_sense
        self.arrived_state.clear()
        self.released = True
        if self.logger:
            self.logger.log_event("BARRIER_RELEASE", {"type": "BUTTERFLY", "stages": self.num_stages})

    def check_release(self, block_id: int, local_sense: bool) -> Tuple[bool, bool]:
        if local_sense != self.global_sense:
            return True, self.global_sense
        return False, local_sense

    def is_full(self) -> bool:
        return self.released

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "BUTTERFLY",
            "arrived_count": len(self.arrived_state),
            "stages": self.num_stages,
            "is_released": self.released
        }
