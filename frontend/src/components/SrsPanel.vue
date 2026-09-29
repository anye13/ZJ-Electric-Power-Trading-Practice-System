<template>
    <div class="srs-panel">
        <h2>🔁 间隔重复复习</h2>

        <!-- 统计卡片 -->
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-value">{{ stats.due }}</div>
                <div class="stat-label">待复习</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.today_reviewed }}</div>
                <div class="stat-label">今日已复习</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.mastered }}</div>
                <div class="stat-label">已掌握</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ stats.total }}</div>
                <div class="stat-label">总卡片</div>
            </div>
        </div>

        <!-- 卡片区 -->
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="currentCard" class="card-area">
            <div class="card-header">
                <span class="card-index">
                    {{ reviewedCount + 1 }} / {{ totalCards }}
                </span>
                <span class="card-type">{{ typeMap[currentCard.type] }}</span>
            </div>

            <div class="question-content" v-html="formatMath(currentCard.content)"></div>

            <!-- 选项 -->
            <div class="options-area">
                <div v-for="(opt, idx) in optionsList" :key="idx" class="option-item">
                    <input v-if="inputType === 'checkbox'" type="checkbox" :value="opt.value"
                        v-model="selectedAnswer" />
                    <input v-else type="radio" :value="opt.value" v-model="selectedAnswer" />
                    <label>{{ opt.label }}</label>
                </div>
                <input v-if="isTextInput" type="text" v-model="textAnswer" class="text-input" placeholder="请输入答案..." />
            </div>

            <!-- 操作 -->
            <div class="actions">
                <button v-if="!revealed" class="btn btn-primary" @click="revealAnswer">
                    显示答案
                </button>
                <template v-else>
                    <div class="answer-box">
                        <div class="correct-answer">
                            <strong>正确答案：</strong>{{ currentCard.answer }}
                        </div>
                        <div v-if="currentCard.explanation" class="explanation">
                            <strong>解析：</strong>{{ currentCard.explanation }}
                        </div>
                    </div>
                    <div class="quality-buttons">
                        <p>请评价你的掌握程度：</p>
                        <button class="btn btn-danger" @click="rate(1)">😰 完全忘记</button>
                        <button class="btn btn-warning" @click="rate(3)">😐 勉强记得</button>
                        <button class="btn btn-primary" @click="rate(4)">🙂 基本掌握</button>
                        <button class="btn btn-success" @click="rate(5)">😎 完全掌握</button>
                    </div>
                </template>
            </div>
        </div>

        <div v-else class="empty-state">
            <div class="empty-icon">🎉</div>
            <p>今日复习任务已完成！</p>
            <p class="hint">明天再来吧~</p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useSrsStore } from '@/stores/srs';
import { usePaperStore } from '@/stores/paper';
import dayjs from 'dayjs';

const srsStore = useSrsStore();
const paperStore = usePaperStore();

const currentIndex = ref(0);
const revealed = ref(false);
const selectedAnswer = ref<any>(null);
const textAnswer = ref('');
const reviewedCount = ref(0);

const typeMap: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    fill_in_blank: '填空题',
    calculation: '计算题',
    essay: '解答题',
};

const currentCard = computed(() => srsStore.dueCards[currentIndex.value] || null);
const totalCards = computed(() => srsStore.dueCards.length);

const optionsList = computed(() => {
    if (!currentCard.value) return [];
    const q = currentCard.value;
    if (q.type === 'true_false') {
        return [{ value: true, label: '正确' }, { value: false, label: '错误' }];
    }
    if (q.type === 'single_choice' || q.type === 'multiple_choice') {
        return q.options.map((opt: string, idx: number) => ({
            value: String.fromCharCode(65 + idx),
            label: opt,
        }));
    }
    return [];
});

const inputType = computed(() => {
    if (!currentCard.value) return 'radio';
    return currentCard.value.type === 'multiple_choice' ? 'checkbox' : 'radio';
});

const isTextInput = computed(() => {
    if (!currentCard.value) return false;
    return ['fill_in_blank', 'calculation', 'essay'].includes(currentCard.value.type);
});

function formatMath(text: string): string {
    if (!text) return '';
    return text
        .replace(/\$\$(.*?)\$\$/g, (_, p1) => `\\(${p1}\\)`)
        .replace(/\$(.*?)\$/g, (_, p1) => `\\(${p1}\\)`);
}

function revealAnswer() {
    revealed.value = true;
}

async function rate(quality: number) {
    if (!currentCard.value) return;
    await srsStore.review(currentCard.value.card_id, quality);
    reviewedCount.value++;
    revealed.value = false;
    selectedAnswer.value = null;
    textAnswer.value = '';
    currentIndex.value = 0;  // 始终从队首开始（因为移除后列表变了）
}

onMounted(async () => {
    await paperStore.ensureInit();
    await srsStore.loadStats(paperStore.selectedPaperId ?? undefined);
    await srsStore.loadDue(paperStore.selectedPaperId ?? undefined);
});

watch(
    () => paperStore.selectedPaperId,
    async () => {
        currentIndex.value = 0;
        reviewedCount.value = 0;
        await srsStore.loadStats(paperStore.selectedPaperId ?? undefined);
        await srsStore.loadDue(paperStore.selectedPaperId ?? undefined);
    }
);
</script>

<style scoped>
.srs-panel {
    padding: 20px;
    max-width: 900px;
    margin: 0 auto;
}

.stats-row {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    flex-wrap: wrap;
}

.stat-card {
    flex: 1;
    min-width: 100px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 16px;
    text-align: center;
}

.stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
}

.stat-label {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
}

.card-area {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 24px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    color: var(--text-secondary);
    margin-bottom: 16px;
    font-size: 14px;
}

.card-type {
    background: var(--bg-secondary);
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
}

.question-content {
    font-size: 16px;
    line-height: 1.8;
    margin-bottom: 20px;
    color: var(--text-primary);
}

.option-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    margin-bottom: 6px;
    border-radius: 6px;
    cursor: pointer;
}

.option-item:hover {
    background: var(--bg-hover);
}

.text-input {
    width: 100%;
    padding: 8px;
    margin-top: 8px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
}

.actions {
    margin-top: 24px;
}

.answer-box {
    background: var(--bg-secondary);
    padding: 16px;
    border-radius: var(--radius);
    margin-bottom: 16px;
}

.correct-answer {
    color: var(--accent-green);
    font-weight: 600;
    margin-bottom: 8px;
}

.explanation {
    color: var(--text-secondary);
    font-size: 14px;
}

.quality-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
}

.quality-buttons p {
    width: 100%;
    color: var(--text-secondary);
    margin-bottom: 8px;
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.btn-primary {
    background: var(--accent-blue);
    color: #fff;
}

.btn-success {
    background: var(--accent-green);
    color: #fff;
}

.btn-warning {
    background: #d29922;
    color: #fff;
}

.btn-danger {
    background: var(--accent-red);
    color: #fff;
}

.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-secondary);
}

.empty-icon {
    font-size: 64px;
    margin-bottom: 16px;
}

.hint {
    font-size: 14px;
    margin-top: 8px;
}

.loading {
    text-align: center;
    padding: 60px;
    color: var(--text-secondary);
}
</style>