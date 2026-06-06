/**
 * 树形拓扑链接高亮模块
 * 
 * 功能：当线程块到达同步点向全局内存传递信息时，
 * 在树形拓扑结构图中标记该 Block 叶子节点到其父节点的链接变色，
 * 直到线程块被释放。
 * 
 * 使用方式：在 index.html 中引入此文件即可
 * 删除方式：直接从 index.html 中移除 <script src="tree_link_highlight.js"></script> 即可
 */

(function() {
    'use strict';

    // 存储当前正在等待同步的 Block 及其路径信息
    let waitingBlocksPaths = new Map(); // blockId -> { leafNodeId, path: [nodeIds], tick }
    let previousWaitingBlocks = new Set();

    /**
     * 获取 Block 对应的叶子节点在树中的路径
     * @param {Object} topology - 拓扑结构
     * @param {number} blockId - Block ID
     * @returns {Array} 从叶子节点到根节点的路径节点ID数组
     */
    function getBlockPathToRoot(topology, blockId) {
        if (!topology || !topology.leaves) return null;
        
        const leafNodeId = topology.leaves[String(blockId)];
        if (!leafNodeId) return null;

        const path = [leafNodeId];
        const nodesMap = new Map();
        topology.nodes.forEach(n => nodesMap.set(String(n.id), n));

        // 向上追溯到根节点
        let currentNodeId = leafNodeId;
        while (currentNodeId) {
            const node = nodesMap.get(String(currentNodeId));
            if (!node || !node.parent) break;
            
            const parentId = String(node.parent);
            const parentNode = nodesMap.get(parentId);
            if (!parentNode) break;
            
            path.push(parentId);
            currentNodeId = parentId;
            
            if (path.length > 100) break;
        }

        return path;
    }

    /**
     * 更新等待路径信息
     * @param {Object} state - 模拟状态快照
     */
    function updateWaitingPaths(state) {
        if (!state.barrier || !state.topology) return;

        const topology = state.topology;
        const blocks = state.blocks || [];
        
        const currentTick = state.tick;
        const currentWaitingBlocks = new Set();

        // 计算当前等待的 Block
        const newWaitingPaths = new Map();
        blocks.forEach(block => {
            if (block.at_barrier || block.state === 'WAITING_AT_BARRIER') {
                const blockId = String(block.id);
                currentWaitingBlocks.add(blockId);
                
                const path = getBlockPathToRoot(topology, block.id);
                if (path && path.length > 0) {
                    newWaitingPaths.set(blockId, {
                        blockId: blockId,
                        leafNodeId: path[0],
                        path: path,
                        tick: currentTick
                    });
                }
            }
        });

        // 检测已释放的 Block（从等待变为运行中）
        previousWaitingBlocks.forEach(blockId => {
            if (!currentWaitingBlocks.has(blockId)) {
                highlightPathRemoved(blockId);
            }
        });

        // 检测新到达的 Block
        currentWaitingBlocks.forEach(blockId => {
            const info = newWaitingPaths.get(blockId);
            if (info && !waitingBlocksPaths.has(blockId)) {
                highlightPathAdded(info);
            }
        });

        waitingBlocksPaths = newWaitingPaths;
        previousWaitingBlocks = currentWaitingBlocks;
    }

    /**
     * 标记路径高亮（添加）
     * @param {Object} pathInfo - 路径信息
     */
    function highlightPathAdded(pathInfo) {
        const { blockId, path } = pathInfo;
        
        document.body.classList.add('tree-highlight-active');

        // 为路径上的每个节点添加高亮
        for (let i = 0; i < path.length; i++) {
            const nodeId = path[i];
            
            // 叶子节点
            if (i === 0) {
                const leafBox = document.querySelector(`.node-box[data-leaf-node="${nodeId}"]`);
                if (leafBox) {
                    leafBox.classList.add('leaf-communicating');
                    leafBox.dataset.blockId = blockId;
                }
            }
            
            // 父节点（不包括叶子）
            if (i > 0) {
                const parentNodeId = path[i];
                const childNodeId = path[i - 1];
                const parentBox = document.querySelector(`.node-box[data-node-id="${parentNodeId}"]`);
                if (parentBox) {
                    parentBox.classList.add('node-parent-of-communicating');
                    parentBox.dataset.blockId = blockId;
                }
                
                // 精确匹配：从子节点到父节点的那条连接线
                const childLi = document.querySelector(`li[data-parent-link="${parentNodeId}"][data-child-node="${childNodeId}"]`);
                if (childLi) {
                    childLi.classList.add('has-communicating-child');
                    childLi.dataset.blockId = blockId;
                }
            }
        }
    }

    /**
     * 移除路径高亮（释放）
     * @param {string} blockId - Block ID
     */
    function highlightPathRemoved(blockId) {
        // 移除叶子节点的高亮
        const leafBox = document.querySelector(`.leaf-communicating[data-block-id="${blockId}"]`);
        if (leafBox) {
            leafBox.classList.remove('leaf-communicating');
            leafBox.classList.add('leaf-communicating-done');
            leafBox.removeAttribute('data-block-id');
            
            setTimeout(() => {
                leafBox.classList.remove('leaf-communicating-done');
            }, 1000);
        }

        // 移除父节点的高亮
        const parentBoxes = document.querySelectorAll(`.node-parent-of-communicating[data-block-id="${blockId}"]`);
        parentBoxes.forEach(box => {
            box.classList.remove('node-parent-of-communicating');
            box.classList.add('node-parent-released');
            box.removeAttribute('data-block-id');
            
            setTimeout(() => {
                box.classList.remove('node-parent-released');
            }, 1000);
        });

        // 移除 li 连接线的高亮
        const liElements = document.querySelectorAll(`.has-communicating-child[data-block-id="${blockId}"]`);
        liElements.forEach(li => {
            li.classList.remove('has-communicating-child');
            li.classList.add('communicating-released');
            li.removeAttribute('data-block-id');
            
            setTimeout(() => {
                li.classList.remove('communicating-released');
            }, 1000);
        });

        // 如果没有其他等待的 Block，移除全局激活类
        if (waitingBlocksPaths.size === 0) {
            setTimeout(() => {
                document.body.classList.remove('tree-highlight-active');
            }, 500);
        }
    }

    /**
     * 清除所有高亮
     */
    function clearAllHighlights() {
        document.querySelectorAll('.leaf-communicating, .node-communicating, .node-parent-of-communicating').forEach(el => {
            el.classList.remove('leaf-communicating', 'node-communicating', 'node-parent-of-communicating');
            el.removeAttribute('data-block-id');
        });
        document.querySelectorAll('.has-communicating-child, .communicating-released').forEach(el => {
            el.classList.remove('has-communicating-child', 'communicating-released');
            el.removeAttribute('data-block-id');
        });
        document.body.classList.remove('tree-highlight-active');
        waitingBlocksPaths.clear();
        previousWaitingBlocks.clear();
    }

    // 暴露全局 API
    window.TreeLinkHighlight = {
        updateWaitingPaths,
        clearAllHighlights,
        getWaitingBlocks: () => Array.from(waitingBlocksPaths.entries())
    };

    // 监听状态更新
    const originalFetchState = window.fetchState;
    if (typeof originalFetchState === 'function') {
        const wrappedFetchState = async function() {
            await originalFetchState();
            
            try {
                const res = await fetch('/api/state');
                if (res.ok) {
                    const state = await res.json();
                    updateWaitingPaths(state);
                }
            } catch (e) {
                // 静默失败
            }
        };
        
        // 替换全局 fetchState
        window.fetchState = wrappedFetchState;
    }

    // 监听重置按钮
    document.addEventListener('DOMContentLoaded', () => {
        const resetBtn = document.getElementById('btn-reset');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                setTimeout(clearAllHighlights, 100);
            });
        }
    });

    console.log('[TreeLinkHighlight] 模块已加载 - 树形拓扑链接高亮功能已启用');
    console.log('[TreeLinkHighlight] 如需移除此功能，请从 index.html 中删除 <script src="tree_link_highlight.js"></script>');
})();
