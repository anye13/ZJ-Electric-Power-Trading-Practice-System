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
            <div class="chart-box" ref="barChartRef" style="height:300px;"></div>
            <div class="chart-box" ref="pieChartRef" style="height:300px;"></div>
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
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
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
}

onMounted(async () => {
    await paperStore.ensureInit();
    if (barChartRef.value) barChart = echarts.init(barChartRef.value);
    if (pieChartRef.value) pieChart = echarts.init(pieChartRef.value);
    loadStats();
    window.addEventListener('resize', () => {
        barChart?.resize();
        pieChart?.resize();
    });
});

onUnmounted(() => {
    barChart?.dispose();
    pieChart?.dispose();
});
watch(
    () => paperStore.selectedPaperId,
    () => loadStats()
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
}

.chart-box {
    flex: 1;
    min-width: 300px;
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 12px;
    border: 1px solid var(--border-color);
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
</style>