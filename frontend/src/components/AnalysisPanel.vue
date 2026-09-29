<template>
    <div class="analysis-panel">
        <h2>📊 数据分析</h2>
        <!-- 统计卡片 -->
        <div class="summary-cards">
            <div class="card">
                <div class="card-value">{{ totalQuestions }}</div>
                <div class="card-label">总题数</div>
            </div>
            <div class="card">
                <div class="card-value">{{ wrongTotal }}</div>
                <div class="card-label">错题总数</div>
            </div>
            <div class="card">
                <div class="card-value">{{ wrongRate }}%</div>
                <div class="card-label">错题率</div>
            </div>
            <div class="card">
                <div class="card-value">{{ todayWrong }}</div>
                <div class="card-label">今日错题</div>
            </div>
        </div>

        <!-- 图表区 -->
        <div class="charts-row">
            <div class="chart-box" ref="barChartRef"></div>
            <div class="chart-box" ref="pieChartRef"></div>
        </div>

        <!-- 最近错题列表 -->
        <div class="recent-wrong">
            <h3>最近错题</h3>
            <div v-if="recentWrongList.length === 0" class="empty">暂无错题记录</div>
            <table v-else class="table table-striped">
                <thead>
                    <tr>
                        <th>题号</th>
                        <th>题型</th>
                        <th>题目内容</th>
                        <th>错误次数</th>
                        <th>最后出错</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="item in recentWrongList" :key="item.id">
                        <td>{{ item.id }}</td>
                        <td>{{ typeMap[item.type] || item.type }}</td>
                        <td class="ellipsis" :title="item.content">{{ item.content }}</td>
                        <td>{{ item.wrong_count }}</td>
                        <td>{{ item.last_wrong_time }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, onActivated, computed, watch, nextTick } from 'vue';
import * as echarts from 'echarts';
import * as api from '@/api';
import { usePaperStore } from '@/stores/paper';
const barChartRef = ref<HTMLElement | null>(null);
const pieChartRef = ref<HTMLElement | null>(null);
let barChart: echarts.ECharts | null = null;
let pieChart: echarts.ECharts | null = null;
const selectedPaperId = ref<number | null>(null);
const totalQuestions = ref(0);
const wrongTotal = ref(0);
const todayWrong = ref(0);
const recentWrongList = ref<any[]>([]);
const paperStore = usePaperStore();
const wrongRate = computed(() => {
    if (totalQuestions.value === 0) return 0;
    return Math.round((wrongTotal.value / totalQuestions.value) * 100);
});
let resizeObserver: ResizeObserver | null = null;
let resizeTimer: number | null = null;
const typeMap: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    fill_in_blank: '填空题',
    calculation: '计算题',
    essay: "解析题"
};
async function loadStats() {
    const paperId = paperStore.selectedPaperId ?? undefined;
    const data = await api.getStats(paperId);
    totalQuestions.value = data.total_questions;
    wrongTotal.value = data.wrong_total;
    // 今日错题（从最近错题中统计今天）
    const recent = await api.getRecentWrong(50, paperId);
    recentWrongList.value = recent;
    const now = new Date();
    const todayStr = now.toISOString().slice(0, 10);
    todayWrong.value = recent.filter((item: any) => item.last_wrong_time?.startsWith(todayStr)).length;

    // 柱状图：各题型错题数
    if (barChart && data.type_stats.length) {
        barChart.setOption({
            tooltip: { trigger: 'axis' },
            xAxis: {
                type: 'category',
                data: data.type_stats.map((s: any) => typeMap[s.type] || s.type),
                axisLabel: { color: '#8b949e' }
            },
            yAxis: {
                type: 'value',
                name: '错题数',
                nameTextStyle: { color: '#8b949e' },
                axisLabel: { color: '#8b949e' }
            },
            series: [{
                type: 'bar',
                data: data.type_stats.map((s: any) => s.wrong_count),
                itemStyle: { color: '#f85149' }
            }]
        });
    }

    // 饼图：各题型错题占比
    if (pieChart && data.type_stats.length) {
        pieChart.setOption({
            tooltip: { trigger: 'item' },
            legend: {
                orient: 'vertical',
                left: 'left',
                textStyle: { color: '#e6edf3' }
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                data: data.type_stats.map((s: any) => ({
                    name: typeMap[s.type] || s.type,
                    value: s.wrong_count
                })),
                label: {
                    color: '#e6edf3',
                    formatter: '{b}\n{d}%'
                }
            }]
        });
    }
    // setOption 之后让图表按当前容器重新布局
    barChart?.resize();
    pieChart?.resize();
}
function resizeCharts() {
    // debounce：容器布局变化时不会疯狂调用
    if (resizeTimer !== null) window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
        barChart?.resize();
        pieChart?.resize();
    }, 120);
}

function setupResizeObserver() {
    if (typeof ResizeObserver === 'undefined') return;
    resizeObserver = new ResizeObserver(() => resizeCharts());
    if (barChartRef.value) resizeObserver.observe(barChartRef.value);
    if (pieChartRef.value) resizeObserver.observe(pieChartRef.value);
}
onMounted(async () => {
    await paperStore.ensureInit();
    await nextTick();   // 等 DOM 布局稳定后再 init，避免拿到 0 宽

    if (barChartRef.value) barChart = echarts.init(barChartRef.value);
    if (pieChartRef.value) pieChart = echarts.init(pieChartRef.value);

    setupResizeObserver();
    await loadStats();

    // 首次渲染后强制 resize 一次（防止 keep-alive 里初始化尺寸不对）
    resizeCharts();
});
onActivated(() => {
    // 从缓存恢复时容器尺寸可能已变
    nextTick(() => resizeCharts());
});
onUnmounted(() => {
    if (resizeTimer !== null) window.clearTimeout(resizeTimer);
    resizeObserver?.disconnect();
    resizeObserver = null;
    barChart?.dispose();
    pieChart?.dispose();
    barChart = null;
    pieChart = null;
});
watch(
    () => paperStore.selectedPaperId,
    () => {
        loadStats();
        nextTick(() => resizeCharts());
    }
);
</script>

<style scoped>
.analysis-panel {
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
}

.analysis-panel h2 {
    margin-bottom: 24px;
    font-weight: 600;
}

.summary-cards {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 24px;
}

.card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 16px 24px;
    min-width: 100px;
    text-align: center;
    border: 1px solid var(--border-color);
}

.card-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
}

.card-label {
    font-size: 14px;
    color: var(--text-secondary);
    margin-top: 4px;
}

.charts-row {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    margin-bottom: 24px;
    min-width: 0;
}

.chart-box {
    flex: 1 1 320px;
    /* 有空间就 320px 起，不够就换行 */
    min-width: 0;
    /* 关键：不要 300px 硬下限 */
    height: 300px;
    /* 高度写在样式里，而不是 inline */
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 12px;
    border: 1px solid var(--border-color);
    box-sizing: border-box;
}

.recent-wrong {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 16px;
    border: 1px solid var(--border-color);
}

.recent-wrong h3 {
    margin-bottom: 12px;
    font-weight: 500;
}

.empty {
    text-align: center;
    color: var(--text-secondary);
    padding: 20px;
}

.ellipsis {
    max-width: 200px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: inline-block;
    vertical-align: middle;
}

.table td {
    padding: 8px 10px;
    color: var(--text-primary);
    font-size: 13px;
}

.table th {
    padding: 8px 10px;
    color: var(--text-secondary);
    font-size: 13px;
}

@media (max-width: 768px) {
    .charts-row {
        flex-direction: column;
        gap: 12px;
    }

    .chart-box {
        flex: none;
        /* 关键：纵向时不要按 flex 分配高度 */
        width: 100%;
        height: 260px;
        /* 固定高度，避免 0 高度 */
    }

    .analysis-panel {
        padding: 12px;
    }

    .analysis-panel h2 {
        font-size: 20px;
        margin-bottom: 16px;
    }

    .summary-cards {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
    }

    .card {
        padding: 12px 8px;
        min-width: 0;
    }

    .card-value {
        font-size: 22px;
    }

    .card-label {
        font-size: 12px;
    }

    .charts-row {
        flex-direction: column;
        gap: 12px;
        margin-bottom: 16px;
    }

    .chart-box {
        min-width: 0;
        /* 关键：去掉 300px 硬下限 */
        width: 100%;
        height: 260px !important;
        /* 覆盖模板 inline 的 300px */
        padding: 8px;
    }

    .recent-wrong {
        padding: 12px;
        overflow-x: auto;
    }

    .recent-wrong h3 {
        font-size: 15px;
    }

    .ellipsis {
        max-width: 160px;
    }
}
</style>