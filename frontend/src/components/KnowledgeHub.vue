<template>
    <div class="knowledge-hub">
        <div class="hub-header">
            <h2>🧠 知识图谱</h2>
            <div class="hub-tabs">
                <button :class="['hub-tab', { active: activeTab === 'graph' }]" @click="switchTab('graph')">
                    🌐 全局图谱
                </button>
                <button :class="['hub-tab', { active: activeTab === 'walk' }]" @click="switchTab('walk')">
                    🧭 漫游复习
                </button>
            </div>
        </div>
        <div class="hub-content">
            <KnowledgeGraph v-show="activeTab === 'graph'" @start-walk="handleStartWalk" />
            <GraphWalk v-show="activeTab === 'walk'" ref="walkRef" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import KnowledgeGraph from './KnowledgeGraph.vue';
import GraphWalk from './GraphWalk.vue';

const activeTab = ref<'graph' | 'walk'>('graph');
const walkRef = ref<InstanceType<typeof GraphWalk> | null>(null);

function switchTab(tab: 'graph' | 'walk') {
    activeTab.value = tab;
    // 从漫游切回图谱时，触发 resize 让 echarts 重新布局
    if (tab === 'graph') {
        nextTick(() => window.dispatchEvent(new Event('resize')));
    }
}

/** 图谱里点击节点 → 切到漫游 tab 并从该点开始 */
async function handleStartWalk(id: number) {
    activeTab.value = 'walk';
    await nextTick();
    walkRef.value?.startFrom(id);
}
</script>

<style scoped>
.knowledge-hub {
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
}

.hub-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 16px;
}

.hub-header h2 {
    margin: 0;
    font-weight: 600;
}

.hub-tabs {
    display: flex;
    gap: 6px;
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 4px;
}

.hub-tab {
    padding: 6px 16px;
    border: none;
    background: transparent;
    color: var(--text-secondary);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: var(--transition);
}

.hub-tab:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
}

.hub-tab.active {
    background: var(--accent-blue);
    color: #fff;
}

.hub-content {
    position: relative;
}

@media (max-width: 768px) {
    .knowledge-hub {
        padding: 10px;
    }

    .hub-header {
        flex-direction: column;
        align-items: stretch;
        gap: 10px;
        margin-bottom: 12px;
    }

    .hub-header h2 {
        font-size: 18px;
        text-align: center;
    }

    .hub-tabs {
        width: 100%;
        justify-content: center;
    }

    .hub-tab {
        flex: 1;
        text-align: center;
        padding: 8px 8px;
        font-size: 13px;
    }
}
</style>