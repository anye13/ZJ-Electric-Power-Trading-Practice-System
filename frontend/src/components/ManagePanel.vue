<template>
  <div class="manage-wrapper">
    <div class="manage-header">
      <h1>📋 题目管理</h1>
      <div class="manage-actions">
        <button class="btn btn-success" @click="$emit('add')">➕ 新增题目</button>
        <button class="btn btn-primary" @click="$emit('showImport')">📥 导入题库</button>
        <button @click="resetProgress" class="btn btn-warning">重置进度</button>
        <button class="btn btn-danger" @click="batchDelete" :disabled="selectedIds.length === 0">
          🗑️ 批量删除 ({{ selectedIds.length }})
        </button>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="manage-toolbar">
      <button class="btn btn-sm btn-primary" @click="showPaperManager = true">
        📄 查看试卷
      </button>
      <span class="current-paper-label">
        当前：<strong>{{ paperStore.selectedPaper?.title || '全部试卷' }}</strong>
      </span>

      <select v-model="filterType" @change="loadList(1)">
        <option value="">全部题型</option>
        <option value="single_choice">单选题</option>
        <option value="multiple_choice">多选题</option>
        <option value="true_false">判断题</option>
        <option value="fill_in_blank">填空题</option>
        <option value="calculation">计算题</option>
        <option value="essay">解答题</option>
      </select>

      <input type="text" v-model="search" placeholder="搜索内容或ID..." @input="loadList(1)" class="search-input" />

      <label><input type="checkbox" v-model="wrongOnly" @change="loadList(1)" /> 仅显示错题</label>
      <label><input type="checkbox" v-model="unansweredOnly" @change="loadList(1)" /> 仅显示未作答</label>

      <div class="per-page">
        <label>每页</label>
        <select v-model="perPage" @change="loadList(1)">
          <option :value="5">5</option>
          <option :value="10">10</option>
          <option :value="15">15</option>
          <option :value="20">20</option>
          <option :value="0">全部</option>
        </select>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-wrap">
      <table class="table table-striped">
        <thead>
          <tr>
            <th><input type="checkbox" @change="toggleAll" :checked="allChecked" /></th>
            <th>ID</th>
            <th>题型</th>
            <th>题目内容</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(q, index) in list" :key="q.id">
            <td><input type="checkbox" v-model="selectedIds" :value="q.id" /></td>
            <td>{{ getGlobalIndex(index) }}</td>
            <td>{{ typeMap[q.type] || q.type }}</td>
            <td class="ellipsis" :title="q.content">{{ q.content }}</td>
            <td>
              <span class="status-badge" :class="{
                'status-correct': q.status === '正确',
                'status-wrong': q.status === '错误',
                'status-unanswered': q.status === '未作答'
              }">{{ q.status }}</span>
            </td>
            <td>
              <button class="btn btn-sm btn-edit" @click="$emit('edit', q)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="deleteItem(q.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
      <button @click="loadList(page - 1)" :disabled="page <= 1">上一页</button>
      <span>第 {{ page }} / {{ pages }} 页</span>
      <button @click="loadList(page + 1)" :disabled="page >= pages">下一页</button>
      <span>（共 {{ total }} 条）</span>
    </div>

    <!-- 试卷管理模态窗 -->
    <PaperManagerModal v-model:visible="showPaperManager" @changed="onPaperManagerChanged" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import * as api from '@/api';
import type { Question } from '@/types';
import { usePaperStore } from '@/stores/paper';
import PaperManagerModal from './PaperManagerModal.vue';

const paperStore = usePaperStore();
const showPaperManager = ref(false);

const emit = defineEmits<{
  (e: 'showImport'): void;
  (e: 'edit', question: Question): void;
  (e: 'add'): void;
}>();

const list = ref<Question[]>([]);
const total = ref(0);
const page = ref(1);
const perPage = ref(10);
const search = ref('');
const selectedIds = ref<number[]>([]);
const filterType = ref('');
const wrongOnly = ref(false);
const unansweredOnly = ref(false);

const pages = computed(() => Math.ceil(total.value / (perPage.value || 1)));
const allChecked = computed(
  () => list.value.length > 0 && list.value.every(q => selectedIds.value.includes(q.id))
);

const typeMap: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_in_blank: '填空题',
  calculation: '计算题',
  essay: '解答题',
};

function getGlobalIndex(index: number): number {
  if (perPage.value === 0) return index + 1;
  return (page.value - 1) * perPage.value + index + 1;
}

async function loadList(p?: number) {
  if (p !== undefined) page.value = p;
  const paperId = paperStore.selectedPaperId ?? undefined;
  const res = await api.getQuestionList(
    page.value,
    perPage.value,
    search.value,
    wrongOnly.value,
    filterType.value,
    unansweredOnly.value,
    paperId
  );
  list.value = res.items;
  total.value = res.total;
  selectedIds.value = [];
}

function onPaperManagerChanged() {
  loadList(1);
}

async function deleteItem(id: number) {
  if (!confirm('确定删除此题？')) return;
  await api.deleteQuestion(id);
  await loadList(page.value);
}

async function batchDelete() {
  if (selectedIds.value.length === 0) return;
  if (!confirm(`确定删除选中的 ${selectedIds.value.length} 道题目吗？`)) return;
  await api.batchDeleteQuestions(selectedIds.value);
  selectedIds.value = [];
  await loadList(page.value);
}

function toggleAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  selectedIds.value = checked ? list.value.map(q => q.id) : [];
}

async function resetProgress() {
  if (confirm('确定重置所有题目的进度吗？（将清空所有已答标记）')) {
    await api.resetProgress();
    await loadList(page.value);
    alert('进度已重置');
  }
}

onMounted(async () => {
  await paperStore.ensureInit();
  loadList(1);
});

watch(
  () => paperStore.selectedPaperId,
  () => {
    loadList(1);
  }
);

defineExpose({ refresh: () => loadList(page.value) });
</script>

<style scoped>
.manage-wrapper {
  max-width: 1200px;
  margin: 0 auto;
}

.manage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.manage-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.manage-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.manage-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  background: var(--bg-card);
  padding: 12px 16px;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
}

.btn-success {
  background: var(--accent-green);
  color: #fff;
}

.btn-success:hover {
  background: #2ea043;
}

.search-input {
  flex: 1;
  min-width: 200px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 6px 12px;
}

.per-page {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 14px;
}

.per-page select {
  padding: 4px 8px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.table-wrap {
  background: var(--bg-card);
  border-radius: var(--radius);
  overflow-x: auto;
  padding: 4px 0;
  box-shadow: var(--shadow);
  border: 1px solid var(--border-color);
}

.ellipsis {
  max-width: 400px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  vertical-align: middle;
}

.table td {
  color: var(--text-primary);
  padding: 10px 12px;
}

.table th {
  color: var(--text-secondary);
  font-weight: 500;
  padding: 10px 12px;
}

.table td:first-child,
.table th:first-child {
  width: 40px;
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-correct {
  background: var(--accent-green);
  color: #fff;
}

.status-wrong {
  background: var(--accent-red);
  color: #fff;
}

.status-unanswered {
  background: var(--text-muted);
  color: var(--text-secondary);
}

.current-paper-label {
  color: var(--text-secondary);
  font-size: 13px;
}

.current-paper-label strong {
  color: var(--accent-blue);
}
</style>