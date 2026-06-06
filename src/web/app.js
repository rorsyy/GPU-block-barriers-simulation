const API_BASE = '/api';

const els = {
    status: document.getElementById('connection-status'),
    tick: document.getElementById('tick-display'),
    barrierType: document.getElementById('barrier-type-display'),
    simState: document.getElementById('sim-state-display'),
    blockTableBody: document.getElementById('block-table-body'),
    log: document.getElementById('log-content'),
    btns: {
        start: document.getElementById('btn-start'),
        pause: document.getElementById('btn-pause'),
        step: document.getElementById('btn-step'),
        reset: document.getElementById('btn-reset'),
    },
    select: {
        barrier: document.getElementById('select-barrier'),
        mode: document.getElementById('select-mode')
    },
    workloadVariance: document.getElementById('workload-variance'),
    varianceDisplay: document.getElementById('variance-display'),
    varianceConfig: document.getElementById('variance-config'),
    numBlocks: document.getElementById('num-blocks'),

    metrics: {
        syncCount: document.getElementById('metric-sync-count'),
        avgComm: document.getElementById('metric-avg-comm')
    },
    memoryPanel: document.getElementById('memory-panel'),
    memoryStructureSection: document.getElementById('memory-structure-section'),
    memoryStructurePanel: document.getElementById('memory-structure-panel'),
    topologySection: document.getElementById('topology-section'),
    topologyContainer: document.getElementById('topology-container')
};

let isConnected = false;
let lastTick = -1;
let blockRows = new Map(); // 缓存block表格行DOM元素，避免重复创建

// --- API Helpers ---

async function postCommand(command, payload = {}) {
    try {
        const res = await fetch(`${API_BASE}/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command, ...payload })
        });
        return await res.json();
    } catch (e) {
        log(`Error sending ${command}: ${e}`);
    }
}

async function fetchState() {
    try {
        const res = await fetch(`${API_BASE}/state`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        updateUI(data);
        setConnected(true);

        if (data.metrics) {
            updateMetrics(data.metrics);
        } else {
            fetchMetrics();
        }
    } catch (e) {
        setConnected(false);
    }
}

async function fetchMetrics() {
    try {
        const res = await fetch(`${API_BASE}/metrics`);
        if (!res.ok) return;
        const metrics = await res.json();
        updateMetrics(metrics);
    } catch (e) {
        // 静默失败
    }
}

// --- UI Updates ---

function setConnected(status) {
    if (status !== isConnected) {
        isConnected = status;
        els.status.textContent = status ? "已连接" : "未连接";
        els.status.className = status ? "status-online" : "status-offline";
    }
}

// 中文状态名映射
const stateNamesCN = {
    'STOPPED': '已停止',
    'RUNNING': '运行中',
    'PAUSED': '已暂停',
    'COMPLETED': '已完成'
};

// Block 状态中文映射
const blockStatesCN = {
    'RUNNING': '运行中',
    'WAITING_AT_BARRIER': '等待中',
    'FINISHED': '已完成',
    'FAILED': '已失败'
};

function updateUI(state) {
    updateTextContent(els.tick, `时钟: ${state.tick}`);
    updateTextContent(els.simState, `状态: ${stateNamesCN[state.simulation_state] || state.simulation_state}`);

    const bType = state.barrier ? state.barrier.type : "未知";
    updateTextContent(els.barrierType, `栅栏: ${bType}`);

    renderBlocks(state.blocks);

    if (state.global_memory) {
        renderGlobalMemory(state.global_memory);
        renderMemoryStructure(state.global_memory, state.barrier ? state.barrier.type : null, state.topology);
    }

    // 树形/静态树形栅栏: 显示后端返回的拓扑
    if (state.topology && state.topology.nodes && state.topology.nodes.length > 0) {
        els.topologySection.classList.remove('hidden');
        renderTopology(state.topology, state.blocks);
    } else if (state.barrier && state.barrier.type === 'CENTRALIZED') {
        // 集中式栅栏: 生成星型拓扑
        els.topologySection.classList.remove('hidden');
        renderCentralizedTopology(state.barrier, state.blocks);
    } else {
        els.topologySection.classList.add('hidden');
    }
}

function updateTextContent(element, newText) {
    if (element.textContent !== newText) {
        element.textContent = newText;
    }
}

// --- 表格渲染：线程块 ---

function renderBlocks(blocks) {
    const currentBlockIds = new Set(blocks.map(b => b.id));

    // 移除不存在的行
    for (const [id, row] of blockRows.entries()) {
        if (!currentBlockIds.has(id)) {
            row.remove();
            blockRows.delete(id);
        }
    }

    // 更新或创建行
    blocks.forEach((block, index) => {
        let row = blockRows.get(block.id);

        if (!row) {
            row = createBlockRow(block);
            blockRows.set(block.id, row);

            const existingRows = Array.from(els.blockTableBody.children);
            if (index < existingRows.length) {
                els.blockTableBody.insertBefore(row, existingRows[index]);
            } else {
                els.blockTableBody.appendChild(row);
            }
        } else {
            updateBlockRow(row, block);
        }
    });
}

function createBlockRow(block) {
    const row = document.createElement('tr');
    row.dataset.blockId = block.id;

    const stateClass = block.state.toLowerCase();
    const stateCN = blockStatesCN[block.state] || block.state;
    const workDone = block.work_done !== undefined ? block.work_done : '—';

    row.innerHTML = `
        <td style="font-weight:600;">${block.id}</td>
        <td><span class="state-badge ${stateClass}">${stateCN}</span></td>
        <td style="font-family:'Consolas',monospace;text-align:center;">${workDone}</td>
        <td>${block.at_barrier
            ? '<span class="barrier-yes">🛑 是</span>'
            : '<span class="barrier-no">否</span>'}</td>
    `;

    return row;
}

function updateBlockRow(row, block) {
    const cells = row.children;

    // 更新状态 badge
    const stateCell = cells[1];
    const stateClass = block.state.toLowerCase();
    const stateCN = blockStatesCN[block.state] || block.state;
    const badge = stateCell.querySelector('.state-badge');
    if (badge) {
        const newClass = `state-badge ${stateClass}`;
        if (badge.className !== newClass) {
            badge.className = newClass;
        }
        updateTextContent(badge, stateCN);
    }

    // 更新工作量
    const workCell = cells[2];
    const workDone = block.work_done !== undefined ? String(block.work_done) : '—';
    updateTextContent(workCell, workDone);

    // 更新栅栏标记
    const barrierCell = cells[3];
    const newBarrierHTML = block.at_barrier
        ? '<span class="barrier-yes">🛑 是</span>'
        : '<span class="barrier-no">否</span>';
    const currentBarrierSpan = barrierCell.querySelector('span');
    const isCurrentlyAtBarrier = currentBarrierSpan && currentBarrierSpan.classList.contains('barrier-yes');
    if (block.at_barrier !== isCurrentlyAtBarrier) {
        barrierCell.innerHTML = newBarrierHTML;
    }
}

// --- 指标更新 ---

function updateMetrics(metrics) {
    const safeProp = (obj, prop, def = '0') => (obj && obj[prop] !== undefined) ? obj[prop] : def;

    updateMetricValue(els.metrics.syncCount, safeProp(metrics, 'sync_count'));
    updateMetricValue(els.metrics.avgComm, safeProp(metrics, 'avg_communication', '0') + ' 次');
}

function updateMetricValue(element, newValue) {
    const currentValue = element.textContent;
    if (currentValue !== String(newValue)) {
        element.classList.add('updating');
        requestAnimationFrame(() => {
            element.textContent = newValue;
            setTimeout(() => {
                element.classList.remove('updating');
            }, 300);
        });
    }
}

// --- 全局内存渲染 (表格式) ---

function renderGlobalMemory(memory) {
    if (!memory || Object.keys(memory).length === 0) {
        els.memoryPanel.innerHTML = '<div class="memory-empty">无内存状态</div>';
        return;
    }

    const entries = Object.entries(memory).slice(0, 15);
    const values = entries.map(([, v]) => parseInt(v) || 0);
    const maxValue = Math.max(...values, 1);

    let html = '<table class="memory-table">';
    html += '<thead><tr><th>变量</th><th>值</th><th>热度</th></tr></thead>';
    html += '<tbody>';

    entries.forEach(([key, value]) => {
        const val = parseInt(value) || 0;
        const intensity = Math.min(val / maxValue, 1.0);

        let heatColor;
        if (intensity === 0) {
            heatColor = '#93c5fd'; // 浅蓝
        } else if (intensity < 0.3) {
            heatColor = '#3b82f6'; // 蓝
        } else if (intensity < 0.7) {
            heatColor = '#f59e0b'; // 橙
        } else {
            heatColor = '#ef4444'; // 红
        }

        html += `
            <tr>
                <td class="mem-key">${key}</td>
                <td class="mem-val">${value}</td>
                <td class="mem-heat"><span class="heat-dot" style="background:${heatColor};"></span></td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    els.memoryPanel.innerHTML = html;
}

// --- 全局内存存储结构渲染 ---

function renderMemoryStructure(memory, barrierType, topology) {
    if (!memory || Object.keys(memory).length === 0) {
        els.memoryStructureSection.classList.add('hidden');
        return;
    }

    const countKeys = Object.keys(memory).filter(k => k.includes('.count') || k.endsWith('.count'));
    if (countKeys.length === 0) {
        els.memoryStructureSection.classList.add('hidden');
        return;
    }

    els.memoryStructureSection.classList.remove('hidden');
    els.memoryStructurePanel.innerHTML = '';

    // 判断栅栏类型并渲染
    if (barrierType === 'TREE' || (barrierType && barrierType.includes('Tree') && !barrierType.includes('STATIC'))) {
        // TreeBarrier: 显示邻接表
        renderAdjacencyList(memory, topology);
    } else if (barrierType === 'STATIC_TREE') {
        // StaticTreeBarrier: 显示数组结构
        renderArrayStructure(memory, topology);
    }
}

// TreeBarrier: 邻接表格式
function renderAdjacencyList(memory, topology) {
    if (!topology || !topology.nodes) {
        els.memoryStructurePanel.innerHTML = '<div class="mem-struct-empty">无法获取拓扑信息</div>';
        return;
    }

    // 构建节点到线程块的反向映射
    const nodeToBlocks = new Map();
    if (topology.leaves) {
        Object.entries(topology.leaves).forEach(([blockId, nodeId]) => {
            const nid = String(nodeId);
            if (!nodeToBlocks.has(nid)) {
                nodeToBlocks.set(nid, []);
            }
            nodeToBlocks.get(nid).push(blockId);
        });
    }

    let html = `
        <div class="mem-struct-section">
            <h4>邻接表 (Adjacency List)</h4>
            <p class="mem-struct-desc">每个节点存储其子节点列表，便于快速遍历</p>
            <div class="adjacency-list">
    `;

    // 按 ID 排序显示所有节点
    const sortedNodes = [...topology.nodes].sort((a, b) => {
        const aId = parseInt(String(a.id).replace(/node_/g, ''));
        const bId = parseInt(String(b.id).replace(/node_/g, ''));
        return aId - bId;
    });

    sortedNodes.forEach(node => {
        const nodeId = String(node.id).replace(/node_/g, '');
        const nodeFullId = String(node.id);
        const children = node.children || [];
        const countKey = `node_${nodeId}.count`;
        const senseKey = `node_${nodeId}.sense`;
        const count = memory[countKey] ?? 0;
        const sense = memory[senseKey] ?? 0;

        const isLeaf = children.length === 0;
        const nodeClass = isLeaf ? 'adj-node-leaf' : 'adj-node-internal';

        // 叶子节点：从反向映射中查找管理的线程块
        let blockLabel = '';
        if (isLeaf) {
            const blocks = nodeToBlocks.get(nodeFullId) || nodeToBlocks.get(nodeId) || [];
            if (blocks.length > 0) {
                blockLabel = ` → Block [${blocks.sort((a, b) => parseInt(a) - parseInt(b)).join(', ')}]`;
            }
        }

        html += `
            <div class="adj-node ${nodeClass}">
                <span class="adj-node-id">node_${nodeId}${blockLabel}</span>
                <span class="adj-node-count">[${count}]</span>
                <span class="adj-node-sense">sense:${sense}</span>
                ${!isLeaf ? `<span class="adj-children">→ [${children.map(c => String(c).replace(/node_/g, '')).join(', ')}]</span>` : ''}
            </div>
        `;
    });

    html += '</div></div>';
    els.memoryStructurePanel.innerHTML = html;
}

// StaticTreeBarrier: 数组结构
function renderArrayStructure(memory, topology) {
    // 提取所有节点
    const nodeIds = [];
    Object.keys(memory).forEach(key => {
        const match = key.match(/node(\d+)\.count/);
        if (match && !nodeIds.includes(match[1])) {
            nodeIds.push(match[1]);
        }
    });
    nodeIds.sort((a, b) => parseInt(a) - parseInt(b));

    const totalNodes = nodeIds.length;

    // 从拓扑数据中获取真实的叶节点集合和叶节点到线程块的映射
    const leafNodeIds = new Set();
    const nodeToBlocks = new Map();
    if (topology && topology.leaves) {
        Object.entries(topology.leaves).forEach(([blockId, nodeId]) => {
            leafNodeIds.add(String(nodeId));
            const nid = String(nodeId);
            if (!nodeToBlocks.has(nid)) {
                nodeToBlocks.set(nid, []);
            }
            nodeToBlocks.get(nid).push(blockId);
        });
    }
    // 如果没有拓扑数据，回退到无子节点判断
    if (leafNodeIds.size === 0 && topology && topology.nodes) {
        topology.nodes.forEach(n => {
            if (!n.children || n.children.length === 0) {
                leafNodeIds.add(String(n.id));
            }
        });
    }

    let html = `
        <div class="mem-struct-section">
            <h4>数组索引结构 (Array Indexing)</h4>
            <p class="mem-struct-desc">
                使用完全二叉树的数组表示法：
                <code>parent = (i-1)/2</code>，
                <code>left = 2i+1</code>，
                <code>right = 2i+2</code>
            </p>
    `;

    // 显示数组形式
    html += '<div class="array-representation">';
    html += '<div class="array-header">global_memory 数组:</div>';
    html += '<div class="array-indexes">';
    nodeIds.forEach((_, idx) => {
        html += `<span class="array-index">${idx}</span>`;
    });
    html += '</div>';
    html += '<div class="array-values">';
    nodeIds.forEach((id, idx) => {
        const count = memory[`node${id}.count`] ?? 0;
        const sense = memory[`node${id}.sense`] ?? 0;
        const isLeaf = leafNodeIds.has(id);
        let label;
        if (isLeaf) {
            const blocks = nodeToBlocks.get(id) || [];
            label = blocks.length > 0 ? `B${blocks.sort((a, b) => parseInt(a) - parseInt(b)).join(',')}` : `L${id}`;
        } else {
            label = `N${id}`;
        }
        html += `<span class="array-cell ${isLeaf ? 'cell-leaf' : ''}" title="node${id}: count=${count}, sense=${sense}">${label}</span>`;
    });
    html += '</div></div>';

    // 层级划分说明
    const maxDepth = Math.ceil(Math.log2(totalNodes + 1)) - 1;
    html += '<div class="level-legend">';
    html += '<div class="level-title">层级划分:</div>';
    for (let d = 0; d <= maxDepth; d++) {
        const start = Math.pow(2, d) - 1;
        const count = Math.pow(2, d);
        const end = Math.min(start + count, totalNodes);
        const levelNodeIds = nodeIds.slice(start, end);
        const hasLeaf = levelNodeIds.some(id => leafNodeIds.has(id));
        const allLeaf = levelNodeIds.every(id => leafNodeIds.has(id));
        const levelDesc = allLeaf ? '叶子节点 (Blocks)' : (hasLeaf ? '混合节点' : `内部节点 (degree=2)`);
        html += `<div class="level-row ${allLeaf ? 'level-leaf' : ''}">
            <span class="level-label">Level ${d}:</span>
            <span class="level-range">[${start}..${end-1}]</span>
            <span class="level-desc">${levelDesc}</span>
        </div>`;
    }
    html += '</div>';

    // 解释
    html += `
            <div class="struct-explanation">
                <h5>为什么数组能构成树？</h5>
                <ul>
                    <li>根节点索引: <code>0</code></li>
                    <li>节点 i 的父节点: <code>(i - 1) / 2</code> (向下取整)</li>
                    <li>节点 i 的左子节点: <code>2 * i + 1</code></li>
                    <li>节点 i 的右子节点: <code>2 * i + 2</code></li>
                </ul>
                <p>例如: node<sub>3</sub> 的父节点是 node<sub>(3-1)/2</sub> = node<sub>1</sub></p>
            </div>
        </div>
    `;

    els.memoryStructurePanel.innerHTML = html;
}

// --- 树形拓扑渲染 ---

let lastTopologyHtml = "";

function renderTopology(topology, blocksInfo) {
    if (!topology || !topology.nodes) return;
    
    // 构建快速查找字典
    const nodesMap = new Map();
    topology.nodes.forEach(n => nodesMap.set(String(n.id), { ...n, childrenData: [] }));
    
    // 构建树形结构 (自底向上连接)
    let rootNode = null;
    nodesMap.forEach((node) => {
        if (node.parent === null || node.parent === undefined) {
            rootNode = node;
        } else {
            const parentNode = nodesMap.get(String(node.parent));
            if (parentNode) {
                parentNode.childrenData.push(node);
            }
        }
    });
    
    if (!rootNode) return; // 找不到根节点

    // 构建叶子结点反向映射，支持一个 Node 映射多个 Block
    const nodeToBlocks = new Map();
    if (topology.leaves) {
        Object.entries(topology.leaves).forEach(([blockId, nodeId]) => {
            const nid = String(nodeId);
            if (!nodeToBlocks.has(nid)) {
                nodeToBlocks.set(nid, []);
            }
            nodeToBlocks.get(nid).push(String(blockId));
        });
    }

    // 将 Block 作为虚拟子节点附加，或者如果 1-to-1 直接转换为块叶子
    nodesMap.forEach((node, id) => {
        if (nodeToBlocks.has(id)) {
            const blockIds = nodeToBlocks.get(id);
            if (blockIds.length === 1 && node.childrenData.length === 0) {
                // 1-to-1 映射，当前 Node 直接作为终端 Block
                node._isBlockLeaf = true;
                node._blockId = blockIds[0];
            } else {
                // 1-to-N 映射 (如 TreeBarrier radix>1)，则将所有 Blocks 添加为当前 Node 的子节点
                blockIds.forEach(bId => {
                    node.childrenData.push({
                        id: `block_${bId}`,
                        _isBlockLeaf: true,
                        _blockId: bId,
                        childrenData: [],
                        count: 0,
                        limit: 0
                    });
                });
            }
        }
    });

    // 递归生成 HTML 树
    function buildHtml(node, parentNodeId = null) {
        const isLeaf = Boolean(node._isBlockLeaf);
        const blockId = isLeaf ? node._blockId : null;
        
        // 尝试去除 "node_" 前缀，否则如果原本是数字也支持
        let nodeIdStr = String(node.id).replace('node_', '');
        let childNodeAttr = isLeaf ? `block_${blockId}` : `node_${nodeIdStr}`;
        let nodeTitle = isLeaf ? `Block ${blockId}` : `Node ${nodeIdStr}`;
        let countText = isLeaf ? '' : `${node.count}/${node.limit}`;
        let extraClass = '';
        let nodeDataAttrs = '';
        
        // 存储节点 ID 用于链接高亮
        if (!isLeaf) {
            nodeDataAttrs += ` data-node-id="node_${nodeIdStr}"`;
        }
        
        // 叶子结点状态
        if (isLeaf && blocksInfo) {
            const blockState = blocksInfo.find(b => String(b.id) === String(blockId));
            if (blockState && blockState.at_barrier) {
                extraClass = 'ready';
                countText = 'Waiting';
                nodeDataAttrs += ` data-block-id="${blockId}"`;
            } else {
                extraClass = 'leaf';
            }
            nodeDataAttrs += ` data-leaf-node="node_${nodeIdStr}"`;
        } else if (!isLeaf && node.count >= node.limit && node.limit > 0) {
            extraClass = 'ready';
        }

        let html = `<li data-parent-link="${parentNodeId || ''}" data-child-node="${childNodeAttr}">
            <div class="node-box ${extraClass}"${nodeDataAttrs}>
                <span class="node-title">${nodeTitle}</span>
                ${countText ? `<span>${countText}</span>` : ''}
            </div>`;
            
        if (node.childrenData && node.childrenData.length > 0) {
            html += `<ul class="tree-level">`;
            // 对子节点排序确保稳定显示
            const sortedChildren = [...node.childrenData].sort((a, b) => {
                const aId = parseInt(String(a.id).replace(/[^\d]/g, '')) || 0;
                const bId = parseInt(String(b.id).replace(/[^\d]/g, '')) || 0;
                return aId - bId;
            });
            sortedChildren.forEach(child => {
                html += buildHtml(child, `node_${nodeIdStr}`);
            });
            html += `</ul>`;
        }
        
        html += `</li>`;
        return html;
    }

    const newHtml = `<div class="css-tree"><ul>${buildHtml(rootNode)}</ul></div>`;
    
    // 只在结构或数据显示变化时更新 DOM
    if (newHtml !== lastTopologyHtml) {
        els.topologyContainer.innerHTML = newHtml;
        lastTopologyHtml = newHtml;
    }
}

// --- 集中式栅栏星型拓扑 ---

let lastCentralizedHtml = "";

function renderCentralizedTopology(barrier, blocksInfo) {
    const count = barrier.count || 0;
    const limit = barrier.limit || 0;
    const sense = barrier.sense !== undefined ? barrier.sense : 0;

    let html = '<div class="css-tree centralized-star">';
    html += '<ul>';
    html += '<li>';

    // 中心节点: Counter
    const centerReady = count >= limit && limit > 0 ? 'ready' : '';
    html += `<div class="node-box center-node ${centerReady}" data-node-id="center">`;
    html += `<span class="node-title">Counter</span>`;
    html += `<span>${count}/${limit}</span>`;
    html += `<span class="node-sense">sense: ${sense}</span>`;
    html += '</div>';

    // 子节点: 所有 Block
    if (blocksInfo && blocksInfo.length > 0) {
        html += '<ul class="tree-level">';
        blocksInfo.forEach(block => {
            const isWaiting = block.at_barrier;
            const extraClass = isWaiting ? 'ready' : 'leaf';
            const statusText = isWaiting ? 'Waiting' : '运行中';
            html += '<li>';
            html += `<div class="node-box ${extraClass}" data-block-id="${block.id}">`;
            html += `<span class="node-title">Block ${block.id}</span>`;
            html += `<span>${statusText}</span>`;
            html += '</div>';
            html += '</li>';
        });
        html += '</ul>';
    }

    html += '</li></ul></div>';

    if (html !== lastCentralizedHtml) {
        els.topologyContainer.innerHTML = html;
        lastCentralizedHtml = html;
    }
}

// --- 日志 ---

function log(msg) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;

    els.log.prepend(entry);

    const maxLogEntries = 100;
    while (els.log.children.length > maxLogEntries) {
        els.log.removeChild(els.log.lastChild);
    }
}

// --- Event Listeners ---

els.btns.start.onclick = () => {
    postCommand('START');
    log('启动仿真...');
};

els.btns.pause.onclick = () => {
    postCommand('PAUSE');
    log('暂停仿真...');
};

els.btns.step.onclick = () => {
    postCommand('STEP');
    log('单步前进...');
};

els.btns.reset.onclick = () => {
    const barrierType = els.select.barrier.value;
    const mode = els.select.mode.value;
    const variance = parseFloat(els.workloadVariance.value);
    const numBlocks = parseInt(els.numBlocks.value) || 6;

    postCommand('RESET', {
        config: {
            barrier_type: barrierType,
            simulation_mode: mode,
            workload_variance: variance,
            num_blocks: numBlocks
        }
    });
    log(`重置为 ${barrierType} (${mode}), ${numBlocks}块...`);

    // 清空表格和缓存
    els.blockTableBody.innerHTML = '';
    blockRows.clear();
};

// 键盘快捷键
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

    switch(e.key.toLowerCase()) {
        case 's':
            if (!e.ctrlKey && !e.metaKey) {
                els.btns.start.click();
                e.preventDefault();
            }
            break;
        case 'p':
            if (!e.ctrlKey && !e.metaKey) {
                els.btns.pause.click();
                e.preventDefault();
            }
            break;
        case ' ':
            els.btns.step.click();
            e.preventDefault();
            break;
        case 'r':
            if (!e.ctrlKey && !e.metaKey) {
                els.btns.reset.click();
                e.preventDefault();
            }
            break;
    }
});

// 工作量方差滑块
els.workloadVariance.addEventListener('input', (e) => {
    els.varianceDisplay.textContent = e.target.value;
});

// 仿真模式切换
els.select.mode.addEventListener('change', (e) => {
    // 模式变更时无需额外处理
});

// --- 轮询 ---

let isPolling = false;
let lastPollTime = 0;
const pollInterval = 100;

function poll() {
    const now = Date.now();

    if (now - lastPollTime >= pollInterval) {
        lastPollTime = now;
        fetchState();
    }

    if (isPolling) {
        requestAnimationFrame(poll);
    }
}

document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        isPolling = false;
    } else {
        isPolling = true;
        lastPollTime = 0;
        requestAnimationFrame(poll);
    }
});

// 启动
isPolling = true;
requestAnimationFrame(poll);

log("前端已初始化。快捷键: [S]启动, [P]暂停, [空格]单步, [R]重置");
