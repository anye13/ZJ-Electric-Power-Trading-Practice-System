<template>
    <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal-content">
            <div class="modal-header">
                <h2>📄 试卷管理</h2>
                <button class="close-btn" @click="close">&times;</button>
            </div>
            <div class="modal-body">
                <!-- 新增试卷 -->
                <div class="add-row">
                    <input type="text" v-model="newPaperTitle" placeholder="请输入新试卷名称" class="paper-input"
                        @keyup.enter="createPaper" />
                    <button class="btn btn-success" @click="createPaper" :disabled="!newPaperTitle.trim()">
                        ➕ 新建
                    </button>
                </div>

                <!-- 试卷列表 -->
                <div class="paper-list">
                    <div v-for="p in papers" :key="p.id" class="paper-item"
                        :class="{ active: p.id === paperStore.selectedPaperId }">
                        <template v-if="editingId === p.id">
                            <input type="text" v-model="editingTitle" class="paper-input" @keyup.enter="saveEdit(p.id)"
                                @keyup.esc="cancelEdit" />
                            <div class="item-actions">
                                <button class="btn btn-sm btn-primary" @click="saveEdit(p.id)">保存</button>
                                <button class="btn btn-sm" @click="cancelEdit">取消</button>
                            </div>
                        </template>
                        <template v-else>
                            <div class="paper-info">
                                <div class="paper-title">
                                    {{ p.title }}
                                    <span v-if="p.id === paperStore.selectedPaperId" class="current-tag">当前</span>
                                </div>
                                <div class="paper-meta">
                                    共 {{ p.total_questions }} 题 · 创建于 {{ formatDate(p.created_at) }}
                                </div>
                            </div>
                            <div class="item-actions">
                                <button class="btn btn-sm btn-primary" @click="selectPaper(p.id)"
                                    :disabled="p.id === paperStore.selectedPaperId">
                                    {{ p.id === paperStore.selectedPaperId ? '已选' : '选择' }}
                                </button>
                                <button class="btn btn-sm btn-edit" @click="startEdit(p)">编辑</button>
                                <button class="btn btn-sm btn-danger" @click="deletePaper(p)">删除</button>
                            </div>
                        </template>
                    </div>
                    <div v-if="papers.length === 0" class="empty-state">
                        <div class="empty-icon">📭</div>
                        <p>暂无试卷，请先新建</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import * as api from '@/api';
import { usePaperStore } from '@/stores/paper';
import type { Paper } from '@/types';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{
    (e: 'update:visible', value: boolean): void;
    (e: 'changed'): void;
}>();

const paperStore = usePaperStore();
const papers = ref<Paper[]>([]);
const newPaperTitle = ref('');
const editingId = ref<number | null>(null);
const editingTitle = ref('');

async function loadPapers() {
    try {
        papers.value = await api.getPapers();
    } catch (e) {
        console.error('加载试卷失败', e);
    }
}

async function createPaper() {
    const title = newPaperTitle.value.trim();
    if (!title) return;
    try {
        await api.createPaper(title);
        newPaperTitle.value = '';
        await loadPapers();
        await paperStore.reloadPapers();
        emit('changed');
    } catch (e) {
        alert('新建失败');
    }
}

function startEdit(p: Paper) {
    editingId.value = p.id;
    editingTitle.value = p.title;
}

function cancelEdit() {
    editingId.value = null;
    editingTitle.value = '';
}

async function saveEdit(id: number) {
    const title = editingTitle.value.trim();
    if (!title) return;
    try {
        await api.updatePaper(id, title);
        cancelEdit();
        await loadPapers();
        await paperStore.reloadPapers();
        emit('changed');
    } catch (e) {
        alert('保存失败');
    }
}

async function deletePaper(p: Paper) {
    if (!confirm(`确定删除试卷「${p.title}」吗？\n该试卷下的所有题目都会被删除，且无法恢复！`)) return;
    try {
        await api.deletePaper(p.id);
        await loadPapers();
        await paperStore.reloadPapers();
        // 若删除的是当前选中试卷，切换为第一张或 null
        if (paperStore.selectedPaperId === p.id) {
            const firstId = papers.value.length > 0 ? papers.value[0].id : null;
            await paperStore.setPaper(firstId);
        }
        emit('changed');
    } catch (e) {
        alert('删除失败');
    }
}

async function selectPaper(id: number) {
    await paperStore.setPaper(id);
    emit('changed');
    // 不关闭模态窗，用户可继续操作
}

function formatDate(dateStr: string) {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('zh-CN');
    } catch {
        return dateStr.slice(0, 10);
    }
}

function close() {
    emit('update:visible', false);
}

// 打开时刷新
watch(
    () => props.visible,
    (val) => {
        if (val) {
            loadPapers();
            cancelEdit();
            newPaperTitle.value = '';
        }
    }
);
</script>

<style scoped>
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}

.modal-content {
    background: var(--bg-card);
    border-radius: var(--radius);
    width: 90%;
    max-width: 640px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border-color);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
    margin: 0;
    color: var(--text-primary);
}

.close-btn {
    background: none;
    border: none;
    font-size: 28px;
    cursor: pointer;
    color: var(--text-secondary);
}

.close-btn:hover {
    color: var(--text-primary);
}

.modal-body {
    padding: 20px 24px;
    overflow-y: auto;
    flex: 1;
}

.add-row {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
}

.paper-input {
    flex: 1;
    padding: 8px 12px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 14px;
}

.paper-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.paper-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    transition: var(--transition);
}

.paper-item.active {
    border-color: var(--accent-blue);
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.2);
}

.paper-info {
    flex: 1;
    min-width: 0;
}

.paper-title {
    font-weight: 600;
    color: var(--text-primary);
    font-size: 15px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.current-tag {
    background: var(--accent-blue);
    color: #fff;
    font-size: 11px;
    padding: 1px 8px;
    border-radius: 10px;
    font-weight: 500;
}

.paper-meta {
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 4px;
}

.item-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
}

.btn {
    padding: 4px 10px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    background: var(--bg-secondary);
    color: var(--text-primary);
    font-size: 13px;
    transition: var(--transition);
}

.btn:hover {
    background: var(--bg-hover);
}

.btn-primary {
    background: var(--accent-blue);
    color: #fff;
}

.btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-success {
    background: var(--accent-green);
    color: #fff;
}

.btn-edit {
    background: #d29922;
    color: #fff;
}

.btn-danger {
    background: var(--accent-red);
    color: #fff;
}

.btn-sm {
    padding: 3px 10px;
    font-size: 12px;
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-secondary);
}

.empty-icon {
    font-size: 48px;
    margin-bottom: 12px;
}
</style>