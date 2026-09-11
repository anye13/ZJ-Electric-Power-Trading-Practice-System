<template>
    <div class="settings-container">
        <h2>⚙️ 设置</h2>
        <div class="settings-card">
            <h3>练习试卷</h3>
            <div class="paper-setting">
                <select v-model="selectedPaperId">
                    <option :value="null">全部试卷</option>
                    <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.title }}</option>
                </select>
                <button class="btn btn-primary" @click="savePaper">保存试卷</button>
            </div>
            <div v-if="paperSaved" class="save-success">✅ 已保存</div>
        </div>
        <div class="settings-card">
            <h3>📌 练习模式</h3>
            <p class="desc">选择您希望练习的题目范围</p>
            <div class="mode-options">
                <label class="mode-option" :class="{ active: !selectedMode }">
                    <input type="radio" v-model="selectedMode" :value="false" />
                    <span class="mode-icon">📝</span>
                    <span class="mode-name">未作答</span>
                    <span class="mode-desc">仅显示未答过的题目</span>
                </label>
                <label class="mode-option" :class="{ active: selectedMode }">
                    <input type="radio" v-model="selectedMode" :value="true" />
                    <span class="mode-icon">❌</span>
                    <span class="mode-name">错题集</span>
                    <span class="mode-desc">仅显示答错的题目</span>
                </label>
            </div>
            <div class="current-mode">
                当前模式：<strong>{{ selectedMode ? '错题集' : '未作答' }}</strong>
            </div>
            <button class="btn btn-primary" @click="saveSettings">💾 保存模式</button>
            <div v-if="saved" class="save-success">✅ 设置已保存</div>
        </div>

        <div class="settings-card">
            <h3>📊 每次获取题目数量</h3>
            <p class="desc">设置每次练习从题库中抽取的题目数量</p>
            <div class="limit-setting">
                <input type="number" v-model.number="limit" min="1" max="999" />
                <span class="unit">题</span>
                <button class="btn btn-primary" @click="saveLimit">💾 保存数量</button>
            </div>
            <div v-if="limitSaved" class="save-success">✅ 已保存</div>
        </div>
        <div class="settings-card">
            <h3>自动清理设置</h3>
            <p>超过以下天数的已答题目将被自动清除，恢复为未作答状态。</p>
            <div class="clean-setting">
                <input type="number" v-model.number="cleanDays" min="1" max="365" />
                <span>天</span>
                <button class="btn btn-primary" @click="saveCleanDays">保存</button>
            </div>
            <div v-if="cleanDaysSaved" class="save-success">✅ 已保存，将在下次定时清理时生效</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useExamStore } from '@/stores/exam';
import * as api from '@/api';
import type { Paper } from '@/types';
const store = useExamStore();
const limit = ref(20);
const limitSaved = ref(false);
const selectedMode = ref(false);
const saved = ref(false);
const cleanDays = ref(7);
const cleanDaysSaved = ref(false);
const papers = ref<Paper[]>([]);
const selectedPaperId = ref<number | null>(null);
const paperSaved = ref(false);
onMounted(async () => {
    // 加载模式
    const stored = localStorage.getItem('userMode');
    if (stored === 'wrong') selectedMode.value = true;
    else if (stored === 'all') selectedMode.value = false;
    else selectedMode.value = store.filterWrong;

    // 加载题目数量
    limit.value = store.practiceLimit || 20;

    // 加载清理天数
    try {
        const settings = await api.getUserSettings();
        cleanDays.value = settings.clean_days || 7;
    } catch {
        cleanDays.value = 7;
    }
    loadPapers();
});
async function loadPapers() {
    try {
        papers.value = await api.getPapers();
        // 读取当前设置
        const settings = await api.getUserSettings();
        selectedPaperId.value = settings.paper_id ?? null;
    } catch (e) {
        console.error('加载试卷失败', e);
    }
}

async function savePaper() {
    await store.updateSettings({ paper_id: selectedPaperId.value });
    paperSaved.value = true;
    setTimeout(() => { paperSaved.value = false; }, 3000);
}
async function saveSettings() {
    store.filterWrong = selectedMode.value;
    await store.updateSettings({ limit: 20 });
    localStorage.setItem('userMode', selectedMode.value ? 'wrong' : 'all');
    saved.value = true;
    setTimeout(() => { saved.value = false; }, 3000);
}

async function saveLimit() {
    if (limit.value < 1) limit.value = 1;
    await store.updateSettings({ limit: limit.value });
    limitSaved.value = true;
    setTimeout(() => { limitSaved.value = false; }, 3000);
}

async function saveCleanDays() {
    if (cleanDays.value < 1) cleanDays.value = 1;
    await api.setCleanDays(cleanDays.value);
    cleanDaysSaved.value = true;
    setTimeout(() => { cleanDaysSaved.value = false; }, 3000);
}
</script>

<style scoped>
.settings-container {
    max-width: 700px;
    margin: 40px auto;
    padding: 0 20px;
}

.settings-container h2 {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 24px;
    border-bottom: 2px solid var(--border-color);
    padding-bottom: 12px;
}

.settings-card {
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 24px 28px;
    margin-bottom: 24px;
    border: 1px solid var(--border-color);
    box-shadow: var(--shadow);
    transition: border-color 0.2s;
}

.settings-card:hover {
    border-color: var(--accent-blue);
}

.settings-card h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 4px 0;
}

.settings-card .desc {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0 0 16px 0;
}

.mode-options {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 16px;
}

.mode-option {
    flex: 1;
    min-width: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 16px 20px;
    border-radius: var(--radius);
    border: 2px solid var(--border-color);
    cursor: pointer;
    transition: all 0.25s ease;
    background: var(--bg-secondary);
    text-align: center;
}

.mode-option:hover {
    border-color: var(--accent-blue);
    background: var(--bg-hover);
}

.mode-option.active {
    border-color: var(--accent-blue);
    background: var(--bg-hover);
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.15);
}

.mode-option input[type="radio"] {
    display: none;
}

.mode-option .mode-icon {
    font-size: 28px;
    line-height: 1.2;
}

.mode-option .mode-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
}

.mode-option .mode-desc {
    font-size: 13px;
    color: var(--text-secondary);
}

.current-mode {
    font-size: 15px;
    color: var(--text-secondary);
    margin: 8px 0 16px;
}

.current-mode strong {
    color: var(--text-primary);
}

.limit-setting {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin: 12px 0;
}

.limit-setting input[type="number"] {
    width: 100px;
    padding: 8px 12px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 16px;
    transition: border-color 0.2s;
}

.limit-setting input[type="number"]:focus {
    border-color: var(--accent-blue);
    outline: none;
    box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
}

.limit-setting .unit {
    font-size: 16px;
    color: var(--text-secondary);
}

.btn {
    padding: 8px 20px;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 14px;
}

.btn-primary {
    background: var(--accent-blue);
    color: #fff;
}

.btn-primary:hover {
    background: #1f6feb;
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(88, 166, 255, 0.25);
}

.save-success {
    margin-top: 12px;
    padding: 8px 14px;
    background: rgba(63, 185, 80, 0.12);
    border-radius: 6px;
    color: var(--accent-green);
    font-weight: 500;
}

.clean-setting {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 12px 0;
}

.clean-setting input[type="number"] {
    width: 80px;
    padding: 6px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
}

.paper-setting {
    display: flex;
    gap: 12px;
    align-items: center;
    margin: 12px 0;
}

.paper-setting select {
    flex: 1;
    padding: 6px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
}
</style>