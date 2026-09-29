<template>
    <div class="dashboard">
        <div class="calendar-wrapper">
            <div class="calendar-header">
                <button @click="prevMonth" class="nav-btn">‹</button>
                <span class="month-title">{{ currentYear }} 年 {{ currentMonth }} 月</span>
                <button @click="nextMonth" class="nav-btn">›</button>
            </div>
            <div class="current-paper">
                当前试卷：{{ paperStore.selectedPaper?.title || '全部试卷' }}
            </div>
            <div class="calendar-grid">
                <div class="weekday" v-for="day in weekdays" :key="day">{{ day }}</div>
                <div v-for="(day, idx) in days" :key="idx" class="calendar-cell" :class="{
                    'empty': !day.date,
                    'has-data': day.total > 0,
                    'today': day.isToday,
                }" :style="{ backgroundColor: day.color }" @mouseenter="showTooltip($event, day)"
                    @mouseleave="hideTooltip" @mousemove="moveTooltip">
                    <span class="day-number">{{ day.day }}</span>
                    <span v-if="day.total > 0" class="day-count">{{ day.total }}</span>
                </div>
            </div>

            <!-- 图例 -->
            <div class="legend">
                <span class="legend-item">
                    <span class="legend-dot" style="background: rgba(88,166,255,0.25);"></span>少量
                </span>
                <span class="legend-item">
                    <span class="legend-dot" style="background: rgba(88,166,255,0.5);"></span>中等
                </span>
                <span class="legend-item">
                    <span class="legend-dot" style="background: rgba(88,166,255,0.75);"></span>较多
                </span>
            </div>
        </div>

        <!-- 悬浮提示 -->
        <Teleport to="body">
            <div v-if="tooltip.visible" class="tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
                <div class="tooltip-date">{{ tooltip.date }}</div>
                <div class="tooltip-row">
                    <span class="label">做题数：</span>
                    <span class="value">{{ tooltip.total }}</span>
                </div>
                <div class="tooltip-row">
                    <span class="label">错题数：</span>
                    <span class="value wrong">{{ tooltip.wrong }}</span>
                </div>
                <div class="tooltip-row">
                    <span class="label">正确率：</span>
                    <span class="value correct">{{ tooltip.accuracy }}%</span>
                </div>
            </div>
        </Teleport>
    </div>
</template>

<script setup lang="ts">
import { ref, onActivated, onMounted, computed, watch } from 'vue';
import * as api from '@/api';
import dayjs from 'dayjs';
import { usePaperStore } from '@/stores/paper';
const currentYear = ref(dayjs().year());
const currentMonth = ref(dayjs().month() + 1);
const dailyData = ref<Record<string, any>>({});
const paperStore = usePaperStore();
const tooltip = ref({
    visible: false,
    x: 0,
    y: 0,
    date: '',
    total: 0,
    wrong: 0,
    accuracy: 0,
});

const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

async function loadDaily(year: number, month: number) {
    try {
        // 传当前试卷
        const data = await api.getDailyStats(
            year,
            month,
            paperStore.selectedPaperId ?? undefined
        );
        dailyData.value = data || {};
    } catch (e) {
        console.error('加载每日数据失败:', e);
        dailyData.value = {};
    }
}

const days = computed(() => {
    const firstDay = dayjs(`${currentYear.value}-${currentMonth.value}-01`);
    const daysInMonth = firstDay.daysInMonth();
    const startWeekday = firstDay.day();
    const today = dayjs().format('YYYY-MM-DD');

    const result: any[] = [];
    for (let i = 0; i < startWeekday; i++) {
        result.push({ date: '', day: '', total: 0 });
    }
    for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = firstDay.date(d).format('YYYY-MM-DD');
        const stats = dailyData.value[dateStr] || { total: 0, wrong: 0, correct: 0, accuracy: 0 };
        const count = stats.total || 0;
        const intensity = Math.min(count / 10, 1);
        const color = count > 0 ? `rgba(88, 166, 255, ${0.15 + intensity * 0.65})` : 'transparent';
        result.push({
            date: dateStr,
            day: d,
            total: count,
            wrong: stats.wrong || 0,
            correct: stats.correct || 0,
            accuracy: stats.accuracy || 0,
            color,
            isToday: dateStr === today,
        });
    }
    const remaining = 7 - (result.length % 7);
    if (remaining < 7) {
        for (let i = 0; i < remaining; i++) {
            result.push({ date: '', day: '', total: 0 });
        }
    }
    return result;
});

function showTooltip(event: MouseEvent, day: any) {
    if (!day.date) return;
    tooltip.value = {
        visible: true,
        x: event.clientX + 14,
        y: event.clientY + 14,
        date: day.date,
        total: day.total || 0,
        wrong: day.wrong || 0,
        accuracy: day.accuracy || 0,
    };
}

function moveTooltip(event: MouseEvent) {
    if (tooltip.value.visible) {
        tooltip.value.x = event.clientX + 14;
        tooltip.value.y = event.clientY + 14;
    }
}

function hideTooltip() {
    tooltip.value.visible = false;
}

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
// 监听全局试卷变化
watch(
    () => paperStore.selectedPaperId,
    () => {
        loadDaily(currentYear.value, currentMonth.value);
    }
);
onMounted(async () => {
    await paperStore.ensureInit();
    loadDaily(currentYear.value, currentMonth.value);
});
onActivated(() => {
    loadDaily(currentYear.value, currentMonth.value);
});
</script>

<style scoped>
.dashboard {
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: calc(100vh - 80px);
    display: flex;
    justify-content: center;
    align-items: flex-start;
}

.calendar-wrapper {
    width: 100%;
    max-width: 800px;
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px;
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow);
}

.calendar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

.month-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}

.nav-btn {
    background: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    width: 36px;
    height: 36px;
    border-radius: 50%;
    font-size: 20px;
    cursor: pointer;
    transition: var(--transition);
    display: flex;
    align-items: center;
    justify-content: center;
}

.nav-btn:hover {
    background: var(--accent-blue);
    color: #fff;
    border-color: var(--accent-blue);
    transform: scale(1.1);
}

.calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
}

.weekday {
    font-weight: 500;
    color: var(--text-secondary);
    text-align: center;
    padding: 8px 0;
    font-size: 14px;
}

.calendar-cell {
    aspect-ratio: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    cursor: default;
    position: relative;
    background-color: transparent;
    transition: all 0.25s ease;
    border: 1px solid transparent;
}

.calendar-cell.has-data {
    cursor: pointer;
}

.calendar-cell.has-data:hover {
    transform: scale(1.08);
    box-shadow: 0 4px 12px rgba(88, 166, 255, 0.35);
    border-color: var(--accent-blue);
    z-index: 2;
}

.calendar-cell.today {
    border: 2px solid var(--accent-green);
    font-weight: 700;
}

.calendar-cell .day-number {
    font-size: 14px;
    color: var(--text-primary);
    line-height: 1;
}

.calendar-cell .day-count {
    font-size: 10px;
    color: var(--text-secondary);
    margin-top: 2px;
}

.calendar-cell.empty {
    visibility: hidden;
}

.legend {
    display: flex;
    gap: 20px;
    justify-content: flex-end;
    margin-top: 16px;
    font-size: 13px;
    color: var(--text-secondary);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
}

.legend-dot {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1px solid var(--border-color);
}

/* 悬浮提示 */
.tooltip {
    position: fixed;
    z-index: 9999;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 14px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
    pointer-events: none;
    min-width: 140px;
    font-size: 13px;
}

.tooltip-date {
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border-color);
}

.tooltip-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
}

.tooltip-row .label {
    color: var(--text-secondary);
}

.tooltip-row .value {
    color: var(--text-primary);
    font-weight: 500;
}

.tooltip-row .value.wrong {
    color: var(--accent-red);
}

.tooltip-row .value.correct {
    color: var(--accent-green);
}

.current-paper {
    text-align: center;
    color: var(--text-secondary);
    font-size: 13px;
    margin-bottom: 12px;
}
</style>