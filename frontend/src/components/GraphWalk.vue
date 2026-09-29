<template>
    <div class="graph-walk">
        <h2>🧭 知识图谱漫游</h2>
        <p class="subtitle">从核心概念出发，沿关系链复习</p>

        <div class="walk-container">
            <!-- 起点选择 -->
            <div class="start-point">
                <label>起点知识点：</label>
                <select v-model="startId" @change="loadStart">
                    <option :value="null">请选择</option>
                    <option v-for="kp in knowledgePoints" :key="kp.id" :value="kp.id">
                        {{ kp.name }}
                    </option>
                </select>
            </div>

            <!-- 漫游路径 -->
            <div v-if="path.length > 0" class="path">
                <div v-for="(node, idx) in path" :key="idx" class="path-node"
                    :class="{ active: idx === path.length - 1 }">
                    <div class="node-name">{{ node.name }}</div>
                    <div v-if="idx < path.length - 1" class="arrow">→</div>
                </div>
            </div>

            <!-- 关联推荐 -->
            <div v-if="related.length > 0" class="related">
                <h3>🔗 相关知识点</h3>
                <div class="related-list">
                    <div v-for="r in related" :key="r.id" class="related-item" @click="walkTo(r)">
                        <span class="name">{{ r.name }}</span>
                        <span class="weight">共现 {{ r.weight }} 次</span>
                    </div>
                </div>
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
const knowledgePoints = ref<any[]>([]);
const startId = ref<number | null>(null);
const path = ref<any[]>([]);
const related = ref<any[]>([]);

async function loadKnowledgePoints() {
    try {
        knowledgePoints.value = await api.getKnowledgePoints();
    } catch (e) {
        console.error('加载知识点失败', e);
    }
}

async function loadStart() {
    if (!startId.value) {
        path.value = [];
        related.value = [];
        return;
    }
    const kp = knowledgePoints.value.find(k => k.id === startId.value);
    if (!kp) return;
    path.value = [{ id: kp.id, name: kp.name }];
    await loadRelated(kp.id);
}

async function walkTo(node: any) {
    // 若已在路径中，回退到该节点位置
    const idx = path.value.findIndex(n => n.id === node.id);
    if (idx >= 0) {
        path.value = path.value.slice(0, idx + 1);
    } else {
        path.value.push({ id: node.id, name: node.name });
    }
    await loadRelated(node.id);
}

async function loadRelated(knowledgeId: number) {
    try {
        related.value = await api.getRelatedKnowledge(
            knowledgeId,
            paperStore.selectedPaperId ?? undefined
        );
    } catch (e) {
        related.value = [];
    }
}

function resetWalk() {
    path.value = [];
    related.value = [];
    startId.value = null;
}

function practicePath() {
    // 简单实现：提示用户跳转到相应题目
    alert('即将根据漫游路径生成练习题（此功能可后续扩展）');
}

onMounted(async () => {
    await paperStore.ensureInit();
    await loadKnowledgePoints();
});

watch(
    () => paperStore.selectedPaperId,
    () => {
        if (startId.value) loadStart();
    }
);
</script>

<style scoped>
.graph-walk {
    padding: 20px;
    max-width: 1000px;
    margin: 0 auto;
}

h2 {
    margin-top: 0;
}

.subtitle {
    color: var(--text-secondary);
    margin-bottom: 24px;
}

.walk-container {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 24px;
}

.start-point {
    margin-bottom: 24px;
}

.start-point label {
    margin-right: 8px;
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

.related h3 {
    font-size: 16px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.related-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
}

.related-item {
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    cursor: pointer;
    transition: var(--transition);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.related-item:hover {
    background: var(--bg-hover);
    border-color: var(--accent-blue);
    transform: translateY(-2px);
}

.related-item .name {
    color: var(--text-primary);
    font-weight: 500;
}

.related-item .weight {
    color: var(--text-secondary);
    font-size: 12px;
}

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