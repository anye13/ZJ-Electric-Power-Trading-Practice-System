<template>
    <div class="dashboard">
        <h2>📊 学习看板</h2>

        <!-- 统计卡片 -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{{ totalQuestions }}</div>
                <div class="stat-label">总题数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ answeredCount }}</div>
                <div class="stat-label">已答题目</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ accuracy }}%</div>
                <div class="stat-label">正确率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ streak }}</div>
                <div class="stat-label">连续打卡天数</div>
            </div>
        </div>

        <!-- 日历 -->
        <div class="calendar-wrapper">
            <div class="calendar-header">
                <button @click="prevMonth">‹</button>
                <span>{{ currentYear }} 年 {{ currentMonth }} 月</span>
                <button @click="nextMonth">›</button>
            </div>
            <div class="calendar-grid">
                <div class="weekday" v-for="day in weekdays" :key="day">{{ day }}</div>
                <div v-for="day in days" :key="day.date" class="calendar-cell" :class="{
                    'empty': !day.date,
                    'has-data': day.count > 0,
                    'current-month': day.currentMonth,
                }" :style="{ backgroundColor: day.color }" @click="showDayDetail(day)">
                    <span class="day-number">{{ day.day }}</span>
                    <span v-if="day.count" class="day-count">{{ day.count }}</span>
                </div>
            </div>
        </div>

        <!-- 每日详情弹窗（简单） -->
        <div v-if="selectedDay" class="modal-overlay" @click.self="selectedDay = null">
            <div class="modal-content">
                <h3>{{ selectedDay.date }}</h3>
                <p>做题数量：{{ selectedDay.count }}</p>
                <button class="btn" @click="selectedDay = null">关闭</button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import * as api from '@/api';
import dayjs from 'dayjs';

const totalQuestions = ref(0);
const answeredCount = ref(0);
const accuracy = ref(0);
const streak = ref(0);

const currentYear = ref(dayjs().year());
const currentMonth = ref(dayjs().month() + 1);
const dailyData = ref<Record<string, number>>({});
const selectedDay = ref<{ date: string; count: number } | null>(null);

const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

// 加载统计信息
async function loadStats() {
    const stats = await api.getStats();
    totalQuestions.value = stats.total_questions || 0;
    // 计算已答题目数量（从 progress 获取，但简化：从 dailyData 汇总）
    // 更好的方式是从 progress 直接获取，但为了简化，我们从 dailyData 汇总
    // 但 dailyData 需要先加载，所以我们在 loadDaily 中一并处理
}

// 加载每日数据
async function loadDaily(year: number, month: number) {
    const data = await api.getDailyStats(year, month);
    dailyData.value = data;

    // 更新统计
    const total = Object.values(data).reduce((a, b) => a + b, 0);
    answeredCount.value = total;
    // 正确率 = 总题数 / 已答？但题目总数可能大于已答，所以我们用已答/总题数？但总题数包括未答，所以正确率应该是已答中正确的比例，但这里没有正确数。所以暂时用 (总题数 - 未答) / 总题数，但未答未知。因此我们直接显示总题数和已答数，正确率留空或从其他 API 获取。
    // 这里简单用 stats 中的正确率（但 stats 中只有错题数，不是正确率）
    // 我们改从 stats 获取总题数和错题数，推断正确率？但错题数可能不完整。
    // 为了演示，我们暂时把正确率设为 0
    // 更好的方式：从后端获取已答正确数，但目前没有。我们可计算 progress 中总数为已答，错题数从 wrong_questions 获取，正确 = 已答 - 错题。
    // 我们来调用 getStats 并补充：
    const stats = await api.getStats();
    const wrongTotal = stats.wrong_total || 0;
    const correct = total - wrongTotal;
    accuracy.value = total > 0 ? Math.round((correct / total) * 100) : 0;

    // 连续打卡：简单统计连续天数
    let streakDays = 0;
    const today = dayjs();
    for (let i = 0; i < 365; i++) {
        const d = today.subtract(i, 'day').format('YYYY-MM-DD');
        if (dailyData.value[d]) {
            streakDays++;
        } else {
            break;
        }
    }
    streak.value = streakDays;
}

// 生成日历网格
const days = computed(() => {
    const firstDay = dayjs(`${currentYear.value}-${currentMonth.value}-01`);
    const daysInMonth = firstDay.daysInMonth();
    const startWeekday = firstDay.day(); // 0=周日

    const result = [];
    // 填充空白
    for (let i = 0; i < startWeekday; i++) {
        result.push({ date: '', day: '', count: 0, currentMonth: false });
    }
    // 填充日期
    for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = firstDay.date(d).format('YYYY-MM-DD');
        const count = dailyData.value[dateStr] || 0;
        const maxCount = 10; // 最大颜色深度
        const intensity = Math.min(count / maxCount, 1);
        const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
        const baseColor = isDark ? '#1c2333' : '#ffffff';
        const activeColor = isDark ? '#58a6ff' : '#0969da';
        const color = count > 0 ? `rgba(88, 166, 255, ${0.3 + intensity * 0.6})` : 'transparent';
        result.push({
            date: dateStr,
            day: d,
            count,
            currentMonth: true,
            color,
        });
    }
    // 补全尾部空白
    const remaining = 7 - (result.length % 7);
    if (remaining < 7) {
        for (let i = 0; i < remaining; i++) {
            result.push({ date: '', day: '', count: 0, currentMonth: false });
        }
    }
    return result;
});

function prevMonth() {
    const d = dayjs(`${currentYear.value}-${currentMonth.value}-01`).subtract(1, 'month');
    currentYear.value = d.year();
    currentMonth.value = d.month() + 1;
    loadDaily(currentYear.value, currentMonth.value);
}

function nextMonth() {
    const d = dayjs(`${currentYear.value}-${currentMonth.value}-01`).add(1, 'month');
    currentYear.value = d.year();
    currentMonth.value = d.month() + 1;
    loadDaily(currentYear.value, currentMonth.value);
}

function showDayDetail(day: any) {
    if (day.count > 0) {
        selectedDay.value = { date: day.date, count: day.count };
    }
}

onMounted(() => {
    loadStats();
    loadDaily(currentYear.value, currentMonth.value);
});
</script>

<style scoped>
.dashboard {
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
    height: calc(100vh - 80px);
    overflow-y: auto;
}

.stats-row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 24px;
}

.stat-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 16px 24px;
    min-width: 100px;
    flex: 1;
    border: 1px solid var(--border-color);
    text-align: center;
}

.stat-value {
    font-size: 28px;
    font-weight: 700;
}

.stat-label {
    font-size: 14px;
    color: var(--text-secondary);
    margin-top: 4px;
}

.calendar-wrapper {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 16px;
    border: 1px solid var(--border-color);
}

.calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.calendar-header button {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
}

.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}

.weekday {
    font-weight: 500;
    color: var(--text-secondary);
    text-align: center;
    padding: 8px 0;
}

.calendar-cell {
    aspect-ratio: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    cursor: default;
    position: relative;
    background-color: transparent;
    transition: background-color 0.2s;
}

.calendar-cell.has-data {
    cursor: pointer;
}

.calendar-cell .day-number {
    font-size: 14px;
    color: var(--text-primary);
}

.calendar-cell .day-count {
    font-size: 10px;
    color: var(--text-secondary);
    margin-top: 2px;
}

.calendar-cell.empty {
    visibility: hidden;
}

.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: var(--bg-card);
    padding: 24px;
    border-radius: var(--radius);
    max-width: 400px;
    width: 90%;
}
</style>