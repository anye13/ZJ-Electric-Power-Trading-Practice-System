<template>
    <div class="graph-container">

        <!-- 控制面板 -->
        <div class="controls">
            <div class="control-group">
                <label>排斥力：</label>
                <input type="range" v-model.number="repulsion" min="50" max="1000" step="10" @input="updateGraph" />
                <span>{{ repulsion }}</span>
            </div>
            <div class="control-group">
                <label><input type="checkbox" v-model="showIsolated" @change="updateGraph" /> 显示孤立点</label>
            </div>
            <div class="control-group">
                <button class="btn" @click="resetView">🔄 重置视图</button>
            </div>
        </div>

        <!-- 视口容器（缩放面板相对它定位） -->
        <div class="graph-viewport">
            <!-- 滚动容器 -->
            <div ref="scrollWrapper" class="graph-scroll-wrapper">
                <!-- 占位符：撑开滚动条 -->
                <div class="graph-spacer" :style="{ width: baseWidth * zoom + 'px', height: baseHeight * zoom + 'px' }">
                </div>

                <!-- 缩放层 -->
                <div class="graph-inner" :style="{
                    width: baseWidth + 'px',
                    height: baseHeight + 'px',
                    transform: `scale(${zoom})`,
                    transformOrigin: '0 0',
                }">
                    <div id="graph" ref="graphEl" class="graph-el"></div>
                </div>
            </div>

            <!-- 空状态遮罩 -->
            <div v-if="!hasData" class="empty-state-overlay">
                <div class="empty-icon">📭</div>
                <p>暂无知识点数据，请先导入含有知识点的题目。</p>
            </div>

            <!-- 左下角缩放控件（固定在视口左下角，不随滚动条跑） -->
            <div class="zoom-panel">
                <span class="zoom-value">{{ Math.round(zoom * 100) }}%</span>
                <input class="zoom-slider" type="range" v-model.number="zoomPercent" min="30" max="300" step="5"
                    @input="onZoomSliderChange" />
                <button class="zoom-btn" @click="setZoom(1)">100%</button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated, nextTick } from 'vue';
import * as echarts from 'echarts';
import * as api from '@/api';
let graphObserver: ResizeObserver | null = null;
let chart: echarts.ECharts | null = null;
let observer: MutationObserver | null = null;
const emit = defineEmits<{ (e: 'start-walk', id: number): void }>();
const repulsion = ref(300);
const showIsolated = ref(true);
const hasData = ref(false);

const scrollWrapper = ref<HTMLElement | null>(null);
const graphEl = ref<HTMLElement | null>(null);

const zoom = ref(1);
const zoomPercent = ref(100);

const baseWidth = ref(1600);
const baseHeight = ref(1000);

let rawNodes: any[] = [];
let rawEdges: any[] = [];
function observeGraphResize() {
    if (typeof ResizeObserver === 'undefined') return;
    const el = scrollWrapper.value;
    if (!el) return;
    graphObserver = new ResizeObserver(() => {
        chart?.resize();
    });
    graphObserver.observe(el);
}
function getThemeColors() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    return {
        text: isDark ? '#e6edf3' : '#1f2328',
        subText: isDark ? '#8b949e' : '#57606a',
        border: isDark ? '#30363d' : '#d0d7de',
        cardBg: isDark ? '#1c2333' : '#ffffff',
        edgeColor: isDark ? '#58a6ff' : '#0969da',
        edgeLabelColor: isDark ? '#e6edf3' : '#1f2328',
    };
}

function computeBaseSize() {
    const n = rawNodes.length;
    baseWidth.value = Math.max(1400, 400 + n * 30);
    baseHeight.value = Math.max(900, 300 + n * 22);
}

function buildChartOption() {
    const colors = getThemeColors();
    let nodes = Array.isArray(rawNodes) ? [...rawNodes] : [];
    let edges = Array.isArray(rawEdges) ? [...rawEdges] : [];

    if (!showIsolated.value) {
        const connectedIds = new Set<string | number>();
        edges.forEach((e: any) => {
            if (e && e.source != null && e.target != null) {
                connectedIds.add(e.source);
                connectedIds.add(e.target);
            }
        });
        nodes = nodes.filter((n: any) => n && connectedIds.has(n.id));
        const validIds = new Set(nodes.map((n: any) => n.id));
        edges = edges.filter((e: any) => e && validIds.has(e.source) && validIds.has(e.target));
    }

    const chartNodes = nodes.map((n: any) => ({
        id: n.id,
        name: n.name || String(n.id),
        value: typeof n.value === 'number' ? n.value : 0,
        symbolSize: 20 + Math.min(40, (n.value || 0) * 2),
        itemStyle: {
            color:
                n.wrong > 0
                    ? `rgba(255, 80, 80, ${Math.min(1, n.wrong / Math.max(n.value || 1, 1))})`
                    : '#58a6ff',
        },
        label: { show: true, color: colors.text, fontSize: 12 },
    }));

    const chartEdges = edges.map((e: any) => ({
        source: e.source,
        target: e.target,
        weight: typeof e.weight === 'number' ? e.weight : 1,
        lineStyle: {
            color: colors.edgeColor,
            width: Math.max(2, (e.weight || 1) / 2),
            opacity: 0.8,
        },
        label: {
            show: true,
            color: colors.edgeLabelColor,
            fontSize: 10,
            formatter: (p: any) => p.data.weight,
        },
    }));

    return {
        title: {
            text: '知识点共现关系',
            textStyle: { color: colors.text, fontSize: 16 },
        },
        tooltip: {
            trigger: 'item',
            textStyle: { color: colors.text },
            backgroundColor: colors.cardBg,
            borderColor: colors.border,
        },
        series: [
            {
                type: 'graph',
                layout: 'force',
                force: {
                    repulsion: repulsion.value,
                    edgeLength: 150,
                    layoutAnimation: true,
                },
                data: chartNodes,
                edges: chartEdges,
                roam: false,
                draggable: true,
                edgeSymbol: ['none', 'arrow'],
                edgeSymbolSize: [0, 6],
                label: { show: true, color: colors.text },
                edgeLabel: {
                    show: true,
                    color: colors.edgeLabelColor,
                    fontSize: 10,
                },
                lineStyle: { color: colors.edgeColor },
                emphasis: { focus: 'adjacency', lineStyle: { width: 3 } },
            },
        ],
    };
}

async function loadGraph() {
    try {
        const data = await api.getKnowledgeGraph();
        rawNodes = Array.isArray(data?.nodes) ? data.nodes : [];
        rawEdges = Array.isArray(data?.edges) ? data.edges : [];

        if (rawNodes.length === 0) {
            hasData.value = false;
            if (chart) chart.clear();
            return;
        }

        hasData.value = true;
        computeBaseSize();
        await nextTick();

        if (!chart && graphEl.value) {
            chart = echarts.init(graphEl.value);
            setupZoomEvents();
        } else if (chart) {
            chart.resize();
        }

        renderChart();
        // 加载完成后自动居中
        await nextTick();
        centerView();
    } catch (error) {
        console.error('加载知识图谱失败:', error);
        hasData.value = false;
    }
}

function renderChart() {
    if (!chart) return;
    chart.setOption(buildChartOption(), true);
    chart.resize();
}

function updateGraph() {
    if (chart && hasData.value) renderChart();
}

// ========== 缩放 ==========
function setZoom(value: number) {
    const v = Math.max(0.3, Math.min(3, value));
    zoom.value = Number(v.toFixed(2));
    zoomPercent.value = Math.round(v * 100);
}

function onZoomSliderChange() {
    setZoom(zoomPercent.value / 100);
}

/** 将视图滚动到画布中心 */
async function centerView() {
    await nextTick();
    const wrapper = scrollWrapper.value;
    if (!wrapper) return;
    const contentW = baseWidth.value * zoom.value;
    const contentH = baseHeight.value * zoom.value;
    const targetScrollLeft = (contentW - wrapper.clientWidth) / 2;
    const targetScrollTop = (contentH - wrapper.clientHeight) / 2;
    // 平滑滚动到中心
    wrapper.scrollTo({
        left: Math.max(0, targetScrollLeft),
        top: Math.max(0, targetScrollTop),
        behavior: 'auto', // 首次加载直接跳转，不用动画
    });
}

function setupZoomEvents() {
    const wrapper = scrollWrapper.value;
    if (!wrapper) return;

    wrapper.addEventListener(
        'wheel',
        (e: WheelEvent) => {
            if (!e.ctrlKey) return;
            e.preventDefault();
            const delta = -e.deltaY;
            const factor = delta > 0 ? 1.1 : 0.9;
            setZoom(zoom.value * factor);
        },
        { passive: false }
    );
}

async function resetView() {
    setZoom(1);
    renderChart();
    // 重置后自动居中
    await nextTick();
    centerView();
}

function startThemeObserver() {
    observer = new MutationObserver(() => {
        if (chart && hasData.value) renderChart();
    });
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme'],
    });
}

function handleResize() {
    if (chart) chart.resize();
}

// 在 onMounted 里 init 之后、loadGraph 之前，绑定点击
onMounted(async () => {
    await nextTick();
    if (graphEl.value) {
        chart = echarts.init(graphEl.value);
        setupZoomEvents();
        chart.on('click', (params: any) => {
            if (params.dataType === 'node' && params.data?.id != null) {
                emit('start-walk', params.data.id);
            }
        });
    }
    await loadGraph();
    observeGraphResize();
    startThemeObserver();
});

onActivated(() => {
    loadGraph();
    nextTick(() => chart?.resize());
});

onUnmounted(() => {
    graphObserver?.disconnect();
    graphObserver = null;
    chart?.dispose();
    chart = null;
    observer?.disconnect();
});
</script>

<style scoped>
.graph-container {
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
    height: calc(100vh - 100px);
    display: flex;
    flex-direction: column;
}

/* 控制面板 */
.controls {
    display: flex;
    gap: 30px;
    margin-bottom: 16px;
    padding: 12px 16px;
    background: var(--bg-card);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
    flex-wrap: wrap;
    align-items: center;
}

.control-group {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-secondary);
    font-size: 14px;
}

.control-group input[type="range"] {
    width: 150px;
    accent-color: var(--accent-blue);
}

.control-group input[type="checkbox"] {
    accent-color: var(--accent-blue);
    width: 16px;
    height: 16px;
}

.btn {
    padding: 6px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.btn:hover {
    background: var(--bg-hover);
}

/* ===== 视口容器：缩放面板相对它定位 ===== */
.graph-viewport {
    flex: 1;
    position: relative;
    overflow: hidden;
    /* 保证绝对定位的 zoom-panel 被约束在内 */
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    background: var(--bg-card);
    min-height: 400px;
}

/* 滚动容器 */
.graph-scroll-wrapper {
    width: 100%;
    height: 100%;
    overflow: auto;
    position: relative;
}

/* 占位符：撑开滚动条 */
.graph-spacer {
    pointer-events: none;
}

/* 缩放层 */
.graph-inner {
    position: absolute;
    top: 0;
    left: 0;
}

.graph-el {
    width: 100%;
    height: 100%;
}

/* 空状态遮罩 */
.empty-state-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    background: var(--bg-card);
    pointer-events: none;
}

.empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
}

/* ===== 左下角缩放控件：相对视口定位，固定在左下角 ===== */
.zoom-panel {
    position: absolute;
    left: 16px;
    bottom: 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    box-shadow: var(--shadow);
    z-index: 10;
}

.zoom-value {
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 600;
    min-width: 40px;
    text-align: center;
}

.zoom-slider {
    width: 120px;
    accent-color: var(--accent-blue);
    cursor: pointer;
}

.zoom-btn {
    padding: 2px 8px;
    font-size: 12px;
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    cursor: pointer;
}

.zoom-btn:hover {
    background: var(--bg-hover);
}

@media (max-width: 768px) {
    .graph-container {
        padding: 10px;
        height: calc(100vh - 120px);
    }

    .graph-container h2 {
        font-size: 18px;
        margin-bottom: 10px;
    }

    .controls {
        flex-direction: column;
        align-items: stretch;
        gap: 8px;
        padding: 10px;
        margin-bottom: 10px;
    }

    .control-group {
        justify-content: space-between;
        gap: 6px;
    }

    .control-group input[type="range"] {
        flex: 1;
        width: auto;
        min-width: 0;
    }

    .graph-viewport {
        min-height: 320px;
    }

    /* 缩放面板简化：去掉滑条，只留百分比和 100% 按钮 */
    .zoom-panel {
        left: 8px;
        bottom: 8px;
        padding: 6px 10px;
        gap: 6px;
    }

    .zoom-slider {
        display: none;
    }

    .zoom-value {
        font-size: 12px;
        min-width: 36px;
    }

    .zoom-btn {
        font-size: 11px;
    }
}
</style>