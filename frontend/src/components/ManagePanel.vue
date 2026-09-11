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

    <div class="manage-toolbar">
      <select v-model="filterType" @change="loadList(1)">
        <option value="">全部题型</option>
        <option value="single_choice">单选题</option>
        <option value="multiple_choice">多选题</option>
        <option value="true_false">判断题</option>
        <option value="fill_in_blank">填空题</option>
        <option value="calculation">计算题</option>
        <option value="essay">解答题</option>
      </select>
      <!-- 试卷选择 -->
      <select v-model="selectedPaper" @change="onPaperChange">
        <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.title }}</option>
      </select>
      <button class="btn btn-sm btn-primary" @click="showCreatePaper = true">+ 新建试卷</button>
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

    <div class="pagination">
      <button @click="loadList(page - 1)" :disabled="page <= 1">上一页</button>
      <span>第 {{ page }} / {{ pages }} 页</span>
      <button @click="loadList(page + 1)" :disabled="page >= pages">下一页</button>
      <span>（共 {{ total }} 条）</span>
    </div>
  </div>
  <!-- ===== 新建试卷模态窗 ===== -->
  <div v-if="showCreatePaper" class="modal-overlay" @click.self="showCreatePaper = false">
    <div class="modal-content" style="max-width: 400px;">
      <h3>📄 新建试卷</h3>
      <input type="text" v-model="newPaperTitle" placeholder="请输入试卷名称" class="paper-input" @keyup.enter="createPaper" />
      <div class="modal-actions">
        <button class="btn btn-primary" @click="createPaper">创建</button>
        <button class="btn" @click="showCreatePaper = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import * as api from '@/api';
import type { Question, Paper } from '@/types';

const emit = defineEmits<{
  (e: 'showImport'): void;
  (e: 'edit', question: Question): void;
  (e: 'add'): void;
}>();
const papers = ref<Paper[]>([]);
const selectedPaper = ref<number | null>(null);
const showCreatePaper = ref(false);
const newPaperTitle = ref('');
const list = ref<Question[]>([]);
const total = ref(0);
const page = ref(1);
const perPage = ref(10);
const search = ref('');
const selectedIds = ref<number[]>([]);
const filterType = ref('');
const pages = computed(() => Math.ceil(total.value / (perPage.value || 1)));
const allChecked = computed(() => {
  return list.value.length > 0 && list.value.every(q => selectedIds.value.includes(q.id));
});
const unansweredOnly = ref(false);
const typeMap: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_in_blank: '填空题',
  calculation: '计算题',
  essay: '解答题',
};
const wrongOnly = ref(false);
// 计算全局索引（从1开始）
function getGlobalIndex(index: number): number {
  if (perPage.value === 0) {
    return index + 1;
  }
  return (page.value - 1) * perPage.value + index + 1;
}
async function loadPapers() {
  papers.value = await api.getPapers();
  if (papers.value.length > 0) {
    selectedPaper.value = papers.value[0].id;
  }
  loadList(1);
}

async function createPaper() {
  if (!newPaperTitle.value.trim()) return;
  await api.createPaper(newPaperTitle.value);
  newPaperTitle.value = '';
  showCreatePaper.value = false;
  await loadPapers();
}

async function deletePaper(id: number) {
  if (!confirm('确定删除此试卷吗？将同时删除其所有题目！')) return;
  await api.deletePaper(id);
  await loadPapers();
}
async function loadList(p?: number) {
  if (p !== undefined) page.value = p;
  const paperId = selectedPaper.value ?? undefined;
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
function onPaperChange() {
  loadList(1);
}
function toggleAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked;
  if (checked) {
    selectedIds.value = list.value.map(q => q.id);
  } else {
    selectedIds.value = [];
  }
}
async function resetProgress() {
  if (confirm('确定重置所有题目的进度吗？（将清空所有已答标记）')) {
    await api.resetProgress();
    // 刷新列表
    await loadList(page.value);
    // 可添加成功提示
    alert('进度已重置');
  }
}
onMounted(() => {
  loadPapers(); // 先加载试卷，再加载题目
});

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

.manage-toolbar .btn-sm {
  padding: 2px 10px;
  font-size: 12px;
}

.table td:first-child,
.table th:first-child {
  width: 40px;
  text-align: center;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 18px;
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
  padding: 24px;
  border: 1px solid var(--border-color);
  width: 90%;
  max-width: 400px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.paper-input {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}
</style>