<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-content">
      <div class="modal-header">
        <h2>📥 导入题库</h2>
        <button class="close-btn" @click="close">&times;</button>
      </div>
      <div class="modal-body">
        <p>上传 JSON 文件，将<strong>追加</strong>新题目（自动去重），ID 由系统自动生成。</p>
        <form @submit.prevent="submitImport">
          <!-- 试卷选择 -->
          <div class="form-group">
            <label>导入到试卷：</label>
            <select v-model="selectedPaperId" required>
              <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.title }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>选择文件：</label>
            <input type="file" ref="fileInput" accept=".json" required />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary" :disabled="loading">
              {{ loading ? '导入中...' : '导入' }}
            </button>
            <button type="button" class="btn" @click="close">取消</button>
          </div>
        </form>
        <div v-if="result" class="result-info">
          <p>✅ 新增 {{ result.added }} 道，跳过 {{ result.skipped }} 道（已存在）。</p>
        </div>
        <div v-if="error" class="error-info">
          <p>❌ {{ error }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import * as api from '@/api';
import type { Paper } from '@/types';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'imported'): void;
}>();

const fileInput = ref<HTMLInputElement | null>(null);
const loading = ref(false);
const result = ref<{ added: number; skipped: number } | null>(null);
const error = ref<string | null>(null);

// 试卷列表和当前选中
const papers = ref<Paper[]>([]);
const selectedPaperId = ref<number | null>(null);

async function loadPapers() {
  try {
    papers.value = await api.getPapers();
    if (papers.value.length > 0 && selectedPaperId.value === null) {
      selectedPaperId.value = papers.value[0].id;
    }
  } catch (e) {
    console.error('加载试卷失败', e);
  }
}

const close = () => {
  emit('update:visible', false);
  loading.value = false;
  result.value = null;
  error.value = null;
  if (fileInput.value) fileInput.value.value = '';
};

const submitImport = async () => {
  const file = fileInput.value?.files?.[0];
  if (!file) return;
  if (!selectedPaperId.value) {
    error.value = '请选择目标试卷';
    return;
  }
  loading.value = true;
  result.value = null;
  error.value = null;
  try {
    const text = await file.text();
    const data = JSON.parse(text);
    // 将 paper_id 合并到请求体
    data.paper_id = selectedPaperId.value;
    const res = await api.importQuestions(data);
    result.value = res;
    emit('imported');
    setTimeout(() => close(), 1500);
  } catch (e: any) {
    error.value = e.message || '导入失败';
  } finally {
    loading.value = false;
  }
};

watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadPapers();
    } else {
      loading.value = false;
      result.value = null;
      error.value = null;
      if (fileInput.value) fileInput.value.value = '';
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
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-card);
  border-radius: var(--radius);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow);
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
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: var(--transition);
}

.close-btn:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 24px;
  color: var(--text-primary);
}

.modal-body p {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--text-secondary);
}

.form-group input[type="file"] {
  display: block;
  width: 100%;
  padding: 8px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.result-info {
  margin-top: 16px;
  padding: 10px 14px;
  background: rgba(63, 185, 80, 0.15);
  border-radius: var(--radius);
  color: var(--accent-green);
  border-left: 3px solid var(--accent-green);
}

.error-info {
  margin-top: 16px;
  padding: 10px 14px;
  background: rgba(248, 81, 73, 0.15);
  border-radius: var(--radius);
  color: var(--accent-red);
  border-left: 3px solid var(--accent-red);
}

.btn {
  padding: 6px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: var(--transition);
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.btn:hover {
  background: var(--bg-hover);
}

.btn-primary {
  background: var(--accent-blue);
  color: #fff;
}

.btn-primary:hover {
  background: #1f6feb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .modal-body {
    padding: 16px;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .form-actions .btn {
    width: 100%;
  }
}
</style>