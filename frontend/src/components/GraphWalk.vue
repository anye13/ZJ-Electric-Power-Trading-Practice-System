<template>
    <div class="graph-walk">
        <p class="subtitle">
            从核心概念出发，沿推荐路线复习
            <span class="paper-hint">
                （当前试卷：{{ paperStore.selectedPaper?.title || '全部试卷' }}）
            </span>
        </p>

        <div class="walk-container">
            <!-- 起点选择 -->
            <div class="start-point">
                <div class="start-row">
                    <label>起点知识点：</label>
                    <select v-model="startId" @change="loadStart" :disabled="knowledgePoints.length === 0">
                        <option :value="null">请选择</option>
                        <option v-for="kp in knowledgePoints" :key="kp.id" :value="kp.id">
                            {{ kp.name }}
                        </option>
                    </select>
                    <span v-if="knowledgePoints.length === 0" class="empty-hint">
                        当前试卷暂无可漫游的知识点（共现次数低于 {{ minCooccur }} 次）
                    </span>
                </div>
                <div class="start-row">
                    <label>共现次数下限：</label>
                    <input type="number" v-model.number="minCooccur" min="1" max="20" class="min-input"
                        @change="onMinCooccurChange" />
                    <span class="hint-text">
                        数值越大，起点越“核心”（共现多的知识点）
                    </span>
                </div>
            </div>

            <!-- 漫游路径 -->
            <div v-if="path.length > 0" class="path">
                <div v-for="(node, idx) in path" :key="idx" class="path-node"
                    :class="{ active: idx === path.length - 1 }">
                    <div class="node-name">{{ node.name }}</div>
                    <div v-if="idx < path.length - 1" class="arrow">→</div>
                </div>
            </div>

            <!-- 推荐下一站 -->
            <div v-if="recommendations.length > 0" class="recommend">
                <h3>🎯 推荐下一站</h3>
                <div class="recommend-list">
                    <div v-for="r in recommendations" :key="r.id" class="recommend-item" @click="walkTo(r)">
                        <div class="rec-main">
                            <span class="name">{{ r.name }}</span>
                            <span class="score">推荐指数 {{ r.score }}</span>
                        </div>
                        <div class="rec-reason">{{ r.reason }}</div>
                    </div>
                </div>
            </div>
            <div v-else-if="path.length > 0 && !loadingRecommend" class="no-related">
                已到达路径末端，没有更多推荐
            </div>

            <!-- 路径操作 -->
            <div v-if="path.length > 0" class="path-actions">
                <button class="btn" @click="resetWalk">🔄 重新开始</button>
                <button class="btn btn-primary" @click="practicePath">✍️ 练习路径中的题目</button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import * as api from '@/api';
import { usePaperStore } from '@/stores/paper';

const paperStore = usePaperStore();
const minCooccur = ref<number>(1);   // 默认 1
const knowledgePoints = ref<Array<{ id: number; name: string }>>([]);
const startId = ref<number | null>(null);
const path = ref<Array<{ id: number; name: string }>>([]);
const recommendations = ref<Array<{
    id: number; name: string; cooccur: number;
    wrong_count: number; total: number; wrong_rate: number;
    score: number; reason: string;
}>>([]);
const loadingRecommend = ref(false);

async function loadKnowledgePoints() {
    try {
        const data = await api.getKnowledgePointsByPaper(
            paperStore.selectedPaperId ?? undefined,
            true,                    // walkable
            minCooccur.value         // 共现下限
        );
        knowledgePoints.value = Array.isArray(data) ? data : [];
    } catch (e) {
        console.error('加载知识点失败', e);
        knowledgePoints.value = [];
    }
}

async function loadStart() {
    if (!startId.value) {
        path.value = [];
        recommendations.value = [];
        return;
    }
    const kp = knowledgePoints.value.find(k => k.id === startId.value);
    if (!kp) return;
    path.value = [{ id: kp.id, name: kp.name }];
    await loadRecommend(kp.id);
}

/** 加载“推荐下一站”，过滤掉已在路径中的节点 */
async function loadRecommend(knowledgeId: number) {
    loadingRecommend.value = true;
    try {
        const data = await api.getRecommendedNext(
            knowledgeId,
            paperStore.selectedPaperId ?? undefined,
            6
        );
        const inPath = new Set(path.value.map(n => n.id));
        recommendations.value = (Array.isArray(data) ? data : []).filter(
            r => !inPath.has(r.id)
        );
    } catch (e) {
        recommendations.value = [];
    } finally {
        loadingRecommend.value = false;
    }
}
/** 修改共现下限后重新拉取列表，并重置漫游 */
async function onMinCooccurChange() {
    if (minCooccur.value < 1) minCooccur.value = 1;
    if (minCooccur.value > 20) minCooccur.value = 20;
    resetWalk();
    localStorage.setItem('graphWalkMinCooccur', String(minCooccur.value));
    await loadKnowledgePoints();
}
/** 从图谱跳转过来时调用 */
async function startFrom(knowledgeId: number) {
    if (knowledgePoints.value.length === 0) {
        await loadKnowledgePoints();
    }

    // 判断是否在可漫游列表里
    const exists = knowledgePoints.value.some(k => k.id === knowledgeId);
    if (!exists) {
        // 说明该知识点是末端（无共现关系），临时加进去并提示
        try {
            // 从全量知识点里找名字（后端返回是 {id, name} 列表）
            const all = await api.getKnowledgePoints(); // 已有的接口
            const kp = all.find((k: any) => k.id === knowledgeId);
            if (kp) {
                knowledgePoints.value = [
                    ...knowledgePoints.value,
                    { id: kp.id, name: kp.name + '（末端）' },
                ];
                // 给用户一个轻提示（不影响使用）
                console.warn(`知识点「${kp.name}」为末端节点，没有推荐下一站`);
            }
        } catch (e) {
            console.error('加载知识点名称失败', e);
        }
    }

    startId.value = knowledgeId;
    await loadStart();
}

async function walkTo(node: { id: number; name: string }) {
    const idx = path.value.findIndex(n => n.id === node.id);
    if (idx >= 0) {
        path.value = path.value.slice(0, idx + 1);
    } else {
        path.value.push({ id: node.id, name: node.name });
    }
    await loadRecommend(node.id);
}

function resetWalk() {
    path.value = [];
    recommendations.value = [];
    startId.value = null;
}

function practicePath() {
    alert('即将根据漫游路径生成练习题（此功能可后续扩展）');
}

async function handlePaperChange() {
    resetWalk();
    await loadKnowledgePoints();
}

onMounted(async () => {
    await paperStore.ensureInit();
    const saved = localStorage.getItem('graphWalkMinCooccur');
    if (saved) minCooccur.value = parseInt(saved) || 1;
    await loadKnowledgePoints();
});

watch(
    () => paperStore.selectedPaperId,
    () => handlePaperChange()
);

defineExpose({ startFrom });
</script>

<style scoped>
.graph-walk {
    padding: 4px 0;
}

.subtitle {
    color: var(--text-secondary);
    margin-bottom: 24px;
}

.paper-hint {
    color: var(--accent-blue);
    font-weight: 500;
}

.walk-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 24px;
}

.start-point {
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.start-row label {
    color: var(--text-secondary);
    min-width: 100px;
}

.start-row select {
    padding: 8px 16px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    min-width: 200px;
}

.start-row select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.min-input {
    width: 80px;
    padding: 6px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
}

.hint-text {
    font-size: 12px;
    color: var(--text-secondary);
}

.empty-hint {
    color: var(--accent-red);
    font-size: 13px;
}

.start-point label {
    color: var(--text-secondary);
}

.start-point select {
    padding: 8px 16px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    min-width: 200px;
}

.start-point select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.empty-hint {
    color: var(--accent-red);
    font-size: 13px;
}

/* 路径 */
.path {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-bottom: 24px;
    padding: 16px;
    background: var(--bg-secondary);
    border-radius: var(--radius);
    min-height: 60px;
}

.path-node {
    display: flex;
    align-items: center;
    gap: 8px;
}

.node-name {
    background: var(--bg-card);
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    font-size: 14px;
}

.path-node.active .node-name {
    background: var(--accent-blue);
    color: #fff;
    border-color: var(--accent-blue);
    font-weight: 600;
}

.arrow {
    color: var(--text-secondary);
    font-weight: bold;
}

/* 推荐下一站 */
.recommend h3 {
    font-size: 16px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.recommend-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 12px;
}

.recommend-item {
    padding: 14px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    cursor: pointer;
    transition: var(--transition);
}

.recommend-item:hover {
    background: var(--bg-hover);
    border-color: var(--accent-blue);
    transform: translateY(-2px);
}

.rec-main {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}

.rec-main .name {
    color: var(--text-primary);
    font-weight: 600;
    font-size: 15px;
}

.rec-main .score {
    font-size: 12px;
    color: var(--accent-blue);
    background: rgba(88, 166, 255, 0.12);
    padding: 2px 8px;
    border-radius: 10px;
}

.rec-reason {
    font-size: 12px;
    color: var(--text-secondary);
}

.no-related {
    color: var(--text-secondary);
    text-align: center;
    padding: 16px;
}

/* 操作按钮 */
.path-actions {
    display: flex;
    gap: 12px;
    margin-top: 24px;
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.btn-primary {
    background: var(--accent-blue);
    color: #fff;
}
</style>