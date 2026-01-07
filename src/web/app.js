const API_BASE = '/api';

const els = {
    status: document.getElementById('connection-status'),
    tick: document.getElementById('tick-display'),
    barrierType: document.getElementById('barrier-type-display'),
    simState: document.getElementById('sim-state-display'),
    grid: document.getElementById('grid-container'),
    log: document.getElementById('log-content'),
    btns: {
        start: document.getElementById('btn-start'),
        pause: document.getElementById('btn-pause'),
        step: document.getElementById('btn-step'),
        reset: document.getElementById('btn-reset'),
    },
    select: {
        barrier: document.getElementById('select-barrier')
    }
};

let isConnected = false;
let lastTick = -1;

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
        
        // 同时获取性能指标（如果数据中包含则直接使用，否则单独获取）
        if (data.metrics) {
            updateMetrics(data.metrics);
        } else {
            fetchMetrics(); // 单独获取
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
        els.status.textContent = status ? "Connected" : "Disconnected";
        els.status.className = status ? "status-online" : "status-offline";
    }
}

function updateUI(state) {
    els.tick.textContent = `Tick: ${state.tick}`;
    els.simState.textContent = `State: ${state.simulation_state}`;
    
    // Barrier info might be in the barrier object or derived
    const bType = state.barrier ? state.barrier.type : "UNKNOWN";
    els.barrierType.textContent = `Barrier: ${bType}`;
    
    renderBlocks(state.blocks);
}

function renderBlocks(blocks) {
    // Diffing logic could be better, but complete re-render is fine for < 100 blocks
    els.grid.innerHTML = ''; 
    
    blocks.forEach(block => {
        const card = document.createElement('div');
        card.className = `block-card ${block.state.toLowerCase()}`;
        
        // Determine progress (randomized or just 100% if done)
        // If block has no progress field, assume 0
        const progress = block.progress || 0;
        
        card.innerHTML = `
            <div class="block-id">Block ${block.id}</div>
            <div class="block-state">${block.state}</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            ${block.at_barrier ? '<div style="font-size:0.8rem; margin-top:5px">🛑 Waiting</div>' : ''}
        `;
        els.grid.appendChild(card);
    });
}

function updateMetrics(metrics) {
    // 更新性能指标显示
    const safeProp = (obj, prop, def = '0') => (obj && obj[prop] !== undefined) ? obj[prop] : def;
    
    document.getElementById('metric-sync-count').textContent = safeProp(metrics, 'sync_count');
    document.getElementById('metric-avg-latency').textContent = safeProp(metrics, 'avg_latency') + ' ticks';
    document.getElementById('metric-avg-wait').textContent = safeProp(metrics, 'avg_wait_time') + ' ticks';
    document.getElementById('metric-contention').textContent = safeProp(metrics, 'contention_count');
    document.getElementById('metric-throughput').textContent = safeProp(metrics, 'throughput') + ' /s';
}

function log(msg) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    els.log.prepend(entry);
}

// --- Event Listeners ---

els.btns.start.onclick = () => postCommand('START');
els.btns.pause.onclick = () => postCommand('PAUSE');
els.btns.step.onclick = () => postCommand('STEP');

els.btns.reset.onclick = () => {
    const barrierType = els.select.barrier.value;
    postCommand('RESET', {
        config: {
            barrier_type: barrierType
        }
    });
    log(`Resetting to ${barrierType}...`);
};

// --- Loop ---

setInterval(fetchState, 100); // Poll every 100ms
log("Frontend initialized.");
