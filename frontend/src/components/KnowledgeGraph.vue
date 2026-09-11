<template>
    <div class="graph-container">
        <h2>🧠 知识图谱</h2>

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
        </div>

        <!-- 图表容器 + 空数据遮罩 -->
        <div class="chart-wrapper">
            <div id="graph" class="chart-box"></div>
            <div v-if="!hasData" class="empty-state-overlay">
                <div class="empty-icon">📭</div>
                <p>暂无知识点数据，请先导入含有知识点的题目。</p>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated, nextTick } from 'vue';
import * as echarts from 'echarts';
import * as api from '@/api';

let chart: echarts.ECharts | null = null;
let observer: MutationObserver | null = null;

const repulsion = ref(300);
const showIsolated = ref(true);
const hasData = ref(false);
let rawNodes: any[] = [];
let rawEdges: any[] = [];

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

function buildChartOption() {
    const colors = getThemeColors();
    let nodes = Array.isArray(rawNodes) ? [...rawNodes] : [];
    let edges = Array.isArray(rawEdges) ? [...rawEdges] : [];

    // 过滤孤立点
    if (!showIsolated.value) {
        const connectedIds = new Set<string | number>();
        edges.forEach((e: any) => {
            if (e && e.source != null && e.target != null) {
                connectedIds.add(e.source);
                connectedIds.add(e.target);
            }
        });
        nodes = nodes.filter((n: any) => n && connectedIds.has(n.id));
        // 同时过滤掉指向已删除节点的边
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
                roam: true,
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
            // 清空图表
            if (chart) chart.clear();
            return;
        }

        hasData.value = true;
        await nextTick();

        // 容器现在应已可见，确保 chart 已初始化
        if (!chart) {
            const dom = document.getElementById('graph');
            if (dom) chart = echarts.init(dom);
        }

        renderChart();
    } catch (error) {
        console.error('加载知识图谱失败:', error);
        hasData.value = false;
    }
}

function renderChart() {
    if (!chart) return;
    // 若容器当前可见但尺寸异常，强制 resize
    chart.setOption(buildChartOption(), true);
    chart.resize();
}

function updateGraph() {
    if (chart && hasData.value) renderChart();
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

onMounted(async () => {
    await nextTick();
    // 容器始终存在于 DOM 中，直接初始化
    const dom = document.getElementById('graph');
    if (dom) {
        chart = echarts.init(dom);
    }
    await loadGraph();
    startThemeObserver();
    window.addEventListener('resize', () => chart?.resize());
});

onActivated(() => {
    loadGraph();
});

onUnmounted(() => {
    chart?.dispose();
    chart = null;
    observer?.disconnect();
    window.removeEventListener('resize', () => chart?.resize());
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

.graph-container h2 {
    margin-top: 0;
    margin-bottom: 16px;
}

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

/* ===== 关键：图表容器始终以完整尺寸存在 ===== */
.chart-wrapper {
    flex: 1;
    position: relative;
    min-height: 400px;
}

.chart-box {
    width: 100%;
    height: 100%;
    background: var(--bg-card);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
}

/* 空数据遮罩 */
.empty-state-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    background: var(--bg-card);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
}

.empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
}
</style>