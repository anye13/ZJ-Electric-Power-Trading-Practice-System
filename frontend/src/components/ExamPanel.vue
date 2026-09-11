<template>
  <div class="exam-wrapper">
    <!-- 错误提示 -->
    <div v-if="store.errorMessage" class="error-banner">{{ store.errorMessage }}</div>
    <!-- ===== 顶部切换栏（始终显示） ===== -->
    <div class="exam-header">
      <div class="exam-title">
        <h1>{{ store.title }}</h1>
      </div>
      <div class="exam-controls">
        <!-- 试卷选择器 -->
        <select v-model="selectedPaperId" @change="onPaperChange" class="paper-selector">
          <option :value="null">全部试卷</option>
          <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.title }}</option>
        </select>
        <span class="badge">当前 {{ store.totalDisplay }} 题</span>
        <span class="mode-badge">{{ store.filterWrong ? '错题集' : '未作答' }}</span>
      </div>
    </div>

    <!-- ===== 主内容 ===== -->
    <div class="exam-body">
      <div class="question-panel">
        <!-- 空状态：错题库无题 -->
        <div v-if="store.filterWrong && store.totalDisplay === 0" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无错题</p>
        </div>

        <!-- 空状态：无题时显示（无论是否加载完成） -->
        <div v-if="store.totalDisplay === 0 && store.totalAll > 0" class="empty-state">
          <div class="empty-icon">{{ store.filterWrong ? '📭' : '🎉' }}</div>
          <p>{{ store.filterWrong ? '暂无错题' : '所有题目均已答完！' }}</p>
        </div>

        <!-- 加载中：无题目且未达到空状态 -->
        <div v-else-if="!store.question" class="loading">加载题目中...</div>
        <!-- 有题目时正常渲染 -->
        <template v-else>
          <!-- 顶部区域：题目 + 选项 (70%) -->
          <div class="top-section">
            <div class="question-header">
              <span class="qid">第 {{ currentDisplayNumber }} 题 / 共 {{ store.totalDisplay }} 题</span>
              <span class="qtype">{{ store.typeName }}</span>
              <span v-if="store.question.is_wrong" class="wrong-badge">❌ 错题</span>
            </div>
            <div class="question-content" v-html="store.renderedContent"></div>

            <div class="options-area">
              <!-- 选择型题目 -->
              <div v-for="(opt, idx) in store.optionsList" :key="idx" class="option-item">
                <input v-if="store.inputType === 'checkbox'" type="checkbox" :name="'answer'" :value="opt.value"
                  v-model="store.selectedAnswer" :id="'opt-' + idx" />
                <input v-else type="radio" :name="'answer'" :value="opt.value" v-model="store.selectedAnswer"
                  :id="'opt-' + idx" />
                <label :for="'opt-' + idx">{{ opt.label }}</label>
              </div>

              <!-- 文本输入型 -->
              <div v-if="store.isTextInput" class="text-input-wrap">
                <textarea v-if="store.question.type === 'essay'" v-model="store.textAnswer" placeholder="请输入解答..."
                  class="text-input" rows="6"></textarea>
                <input v-else type="text" v-model="store.textAnswer" placeholder="请输入答案..." class="text-input" />
              </div>
            </div>
          </div>

          <!-- 操作按钮 (中间) -->
          <div class="action-bar">
            <button @click="handlePrev" class="btn" :disabled="currentDisplayIndex <= 0">上一题</button>
            <button @click="handleNext" class="btn"
              :disabled="currentDisplayIndex < 0 || currentDisplayIndex >= displayOrder.length - 1">下一题</button>
            <button @click="store.submitAnswer" class="btn btn-primary">提交答案</button>
            <button @click="handleChop" class="btn btn-warning">⚡ 斩题</button>
            <button v-if="currentDisplayIndex === displayOrder.length - 1" @click="showRefreshModal = true"
              class="btn">获取新题</button>
          </div>

          <!-- 底部区域：提交结果 (30%) -->
          <div class="bottom-section" ref="bottomSection">
            <div v-if="store.submitResult" class="result-box">
              <div class="result-badge" :class="store.submitResult.correct ? 'correct' : 'wrong'">
                {{ store.submitResult.message }}
              </div>
              <div class="correct-answer">
                <strong>正确答案：</strong>{{ store.question.correct_answer }}
              </div>
              <div v-if="store.question.explanation" class="explanation-box"
                v-html="formatMath(store.question.explanation)"></div>
            </div>
            <div v-else class="result-placeholder">提交答案后，此处将显示结果和解析</div>
          </div>
        </template>

      </div>

      <!-- 答题卡 -->
      <div class="answer-sheet">
        <h3>答题卡</h3>
        <div class="sheet-content">
          <div v-for="group in groupedSheet" :key="group.type" class="sheet-group">
            <h4>{{ typeMap[group.type] || group.type }}</h4>
            <div class="sheet-items">
              <span v-for="item in group.items" :key="item.pos" class="sheet-item" :class="{
                'is-wrong': item.is_wrong,
                'submitted': item.submitted && !item.is_wrong,
                'current': item.pos === store.currentPos,
              }" @click="store.jumpTo(item.pos)">
                {{ item.displayNumber }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 刷新模态窗 ===== -->
    <div v-if="showRefreshModal" class="modal-overlay">
      <div class="modal-content">
        <h2>🔄 重新获取题目</h2>
        <p>
          {{ store.filterWrong ? '错题库已无更多题目，是否重新从错题表中获取？' : '您已到达列表末尾，是否从未作答题目中重新抽取 ' + (store.practiceLimit || 20) +
            '题？'
          }}
        </p>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="confirmRefresh">重新获取</button>
          <button class="btn" @click="showRefreshModal = false">取消</button>
        </div>
      </div>
    </div>

    <!-- 全部完成模态窗（独立于刷新模态窗） -->
    <div v-if="showAllDoneModal" class="modal-overlay">
      <div class="modal-content">
        <h2>🎉 恭喜完成所有题目！</h2>
        <p>所有题目均已作答，是否重新开始？</p>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="resetAndReload">重新开始</button>
          <button class="btn" @click="showAllDoneModal = false">稍后</button>
        </div>
      </div>
    </div>

    <!-- ===== 模式选择模态窗 ===== -->
    <div v-if="showModeSelect" class="modal-overlay">
      <div class="modal-content">
        <h2>📚 选择练习模式</h2>
        <p>您希望从哪种题库开始练习？</p>
        <div class="modal-actions">
          <button class="btn btn-primary" @click="selectMode(false)">📝 未作答</button>
          <button class="btn btn-danger" @click="selectMode(true)">❌ 错题集</button>
        </div>
        <div class="modal-actions" style="margin-top: 8px;">
          <button class="btn" @click="closeModeSelect">稍后设置</button>
        </div>
        <p class="hint">选择后自动应用，也可在侧边栏设置中更改</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onActivated, ref, watch, computed } from 'vue';
import { useExamStore } from '@/stores/exam';
import * as api from '@/api';
import type { Paper, SheetItem } from '@/types';
const showRefreshModal = ref(false);
const showAllDoneModal = ref(false);
defineOptions({ name: 'ExamPanel' });
const showModeSelect = ref(false);
const store = useExamStore();
const papers = ref<Paper[]>([]);
const selectedPaperId = ref<number | null>(null);
const typeMap: Record<string, string> = {
  single_choice: '单选题',
  multiple_choice: '多选题',
  true_false: '判断题',
  fill_in_blank: '填空题',
  calculation: '计算题',
  essay: '解答题',
};
const typeOrder = [
  'single_choice',
  'multiple_choice',
  'true_false',
  'fill_in_blank',
  'calculation',
  'essay',
];
const modeSelectDismissed = ref(false);
// 按题型分组并全局连续编号
const orderedSheetGroups = computed(() => {
  const groups: Record<string, SheetItem[]> = {};
  // 先按题型分组
  store.sheetData.items.forEach(item => {
    if (!groups[item.type]) groups[item.type] = [];
    groups[item.type].push(item);
  });

  // 按题型顺序输出，同时给每个题目分配连续编号
  let counter = 1;
  const result: Array<{ type: string; items: Array<SheetItem & { displayNumber: number }> }> = [];

  typeOrder.forEach(type => {
    if (groups[type] && groups[type].length > 0) {
      // 组内按 pos 升序排列
      const sorted = [...groups[type]].sort((a, b) => a.pos - b.pos);
      const items = sorted.map(item => ({
        ...item,
        displayNumber: counter++,
      }));
      result.push({ type, items });
    }
  });

  return result;
});
// 按题型分组后的展示顺序（数组元素是 pos）
const displayOrder = computed<number[]>(() => {
  const groups: Record<string, SheetItem[]> = {};
  store.sheetData.items.forEach(item => {
    if (!groups[item.type]) groups[item.type] = [];
    groups[item.type].push(item);
  });

  const order: number[] = [];
  typeOrder.forEach(type => {
    if (groups[type] && groups[type].length > 0) {
      const sorted = [...groups[type]].sort((a, b) => a.pos - b.pos);
      sorted.forEach(item => order.push(item.pos));
    }
  });
  return order;
});
// 当前题目在展示顺序中的索引
const currentDisplayIndex = computed<number>(() => {
  return displayOrder.value.indexOf(store.currentPos);
});
const groupedSheet = computed(() => {
  const groups: Record<string, SheetItem[]> = {};
  store.sheetData.items.forEach(item => {
    if (!groups[item.type]) groups[item.type] = [];
    groups[item.type].push(item);
  });

  let counter = 1;
  const result: Array<{ type: string; items: Array<SheetItem & { displayNumber: number }> }> = [];
  typeOrder.forEach(type => {
    if (groups[type] && groups[type].length > 0) {
      const sorted = [...groups[type]].sort((a, b) => a.pos - b.pos);
      const items = sorted.map(item => ({
        ...item,
        displayNumber: counter++,
      }));
      result.push({ type, items });
    }
  });
  return result;
});
const currentDisplayNumber = computed<number>(() => {
  const idx = displayOrder.value.indexOf(store.currentPos);
  return idx >= 0 ? idx + 1 : 1;
});
// 统一公式转换函数
function formatMath(text: string): string {
  if (!text) return '';
  return text
    .replace(/\$\$(.*?)\$\$/g, (_, p1) => `\\(${p1}\\)`)   // 块级 → 行内
    .replace(/\$(.*?)\$/g, (_, p1) => `\\(${p1}\\)`);       // 行内 → 行内
}
// 选择模式
async function selectMode(useWrong: boolean) {
  showModeSelect.value = false;
  modeSelectDismissed.value = true;
  store.filterWrong = useWrong;
  await store.updateSettings({ limit: 20 });
  store.currentPos = 0;
  await store.loadQuestion();

  localStorage.setItem('userMode', useWrong ? 'wrong' : 'all');

  // 只提示一次，不强制重开模态窗
  if (store.totalDisplay === 0) {
    alert(useWrong
      ? '当前错题集为空，可前往管理界面添加题目'
      : '当前没有未作答题目，可前往管理界面添加题目'
    );
  }
}
// 关闭模态窗：默认未作答模式，允许用户自由切换页面
function closeModeSelect() {
  showModeSelect.value = false;
  modeSelectDismissed.value = true;
  localStorage.setItem('userMode', 'all');
  store.filterWrong = false;
  store.updateSettings({ limit: 20 });
  store.loadQuestion();
}
// 检查模式：不强制弹窗，让用户自行处理
async function checkModeSelection() {
  if (modeSelectDismissed.value) return;
  const saved = localStorage.getItem('userMode');
  if (saved === 'wrong' || saved === 'all') {
    store.filterWrong = saved === 'wrong';
    await store.updateSettings({ limit: 20 });
    await store.loadQuestion();
    // 无题也不再强制弹窗，界面会显示空状态
  } else {
    showModeSelect.value = true;
  }
}
async function loadPapers() {
  try {
    papers.value = await api.getPapers();
  } catch (e) {
    console.error('加载试卷失败', e);
  }
}
async function onPaperChange() {
  await store.updateSettings({ paper_id: selectedPaperId.value });
  // 重置当前题目
  store.currentPos = 0;
  await store.loadQuestion();
}
// 按显示顺序导航
async function handlePrev() {
  const idx = currentDisplayIndex.value;
  if (idx > 0) {
    await store.jumpTo(displayOrder.value[idx - 1]);
  }
}

async function handleNext() {
  const idx = currentDisplayIndex.value;
  if (idx >= 0 && idx + 1 < displayOrder.value.length) {
    await store.jumpTo(displayOrder.value[idx + 1]);
  }
}

async function confirmRefresh() {
  showRefreshModal.value = false;
  try {
    // 清空前端答案（但保留后端进度）
    store.userAnswers = {};
    localStorage.removeItem('userAnswers');
    // 重新获取题目
    const data = await api.refreshQuestions();
    // 更新 store 状态
    store.question = data;
    store.currentPos = data.current_pos;
    store.totalDisplay = data.total_display;
    store.totalAll = data.total_all;
    // 重置当前题目的输入
    store.selectedAnswer = null;
    store.textAnswer = '';
    store.submitResult = null;
    await store.loadSheet(); // loadSheet 会重新构建答题卡，此时 userAnswers 为空，所以全部未答
  } catch (e: any) {
    console.error('刷新题目失败', e);
    if (e.response && e.response.status === 404) {
      alert('暂无错题');
    } else {
      alert('刷新失败，请重试');
    }
  }
}

async function resetAndReload() {
  await api.resetProgress();
  showAllDoneModal.value = false;
  await store.loadQuestion();
}

async function handleChop() {
  if (!store.question) return;
  if (!confirm('确定要斩掉此题吗？（将强制标记为正确）')) return;
  try {
    await api.chopQuestion(store.question.id);
    await handleNext();
  } catch (e) {
    console.error('斩题失败', e);
    alert('斩题失败，请重试');
  }
}

onMounted(async () => {
  await loadPapers();
  // 从用户设置读取当前 paper_id
  try {
    const settings = await api.getUserSettings();
    selectedPaperId.value = settings.paper_id ?? null;
  } catch { }
  checkModeSelection();
});

onActivated(() => {
  store.loadQuestion();
});

watch(() => [store.totalDisplay, store.filterWrong], ([newTotal, isWrong]) => {
  if (!isWrong && newTotal === 0 && store.totalAll > 0) {
    showAllDoneModal.value = true;
  } else {
    showAllDoneModal.value = false;
  }
});
</script>

<style scoped>
.exam-wrapper {
  max-width: 1400px;
  margin: 0 auto;
}

/* ----- 顶部栏 ----- */
.exam-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: var(--bg-card);
  padding: 16px 24px;
  border-radius: var(--radius);
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}

.exam-title h1 {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}

.exam-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
  color: var(--text-secondary);
}

.switch-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-blue);
}

/* ----- 主区域 flex ----- */
.exam-body {
  display: flex;
  gap: 24px;
  height: calc(100vh - 200px);
  /* 固定高度，根据顶部栏和边距调整 */
  min-height: 400px;
  /* 最小高度保证可用 */
}

.question-panel {
  flex: 1;
  background: var(--bg-card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  /* 防止整个面板滚动 */
}

.top-section {
  flex: 7;
  /* 占70% */
  overflow-y: auto;
  padding: 20px 24px 12px 24px;
}

.bottom-section {
  flex: 3;
  /* 占30% */
  overflow-y: auto;
  padding: 12px 24px 20px 24px;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
  /* 与题目区域区分 */
}

.answer-sheet {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 16px;
  box-shadow: var(--shadow);
  overflow-y: auto;
  /* 答题卡内部滚动 */
  height: 100%;
}

/* ----- 题目区 ----- */
.question-header {
  display: flex;
  justify-content: space-between;
  font-size: 16px;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.qid {
  font-weight: 500;
}

.qtype {
  background: var(--bg-secondary);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
}

.question-content {
  font-size: 16px;
  line-height: 1.8;
  margin-bottom: 20px;
  color: var(--text-primary);
}

.options-area {
  margin-bottom: 20px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  transition: var(--transition);
  cursor: pointer;
}

.option-item label {
  cursor: pointer;
  flex: 1;
}

.option-item:hover {
  background: var(--bg-hover);
}

.option-item input[type="radio"],
.option-item input[type="checkbox"] {
  accent-color: var(--accent-blue);
  width: 16px;
  height: 16px;
}

.text-input-wrap {
  margin-top: 8px;
}

.text-input {
  width: 100%;
  max-width: 400px;
}

/* 结果 */
.result-box {
  background: var(--bg-secondary);
  border-radius: var(--radius);
  padding: 16px;
  margin: 12px 0;
}

.result-badge {
  font-weight: 600;
  font-size: 16px;
  margin-bottom: 6px;
}

.result-badge.correct {
  color: var(--accent-green);
}

.result-badge.wrong {
  color: var(--accent-red);
}

.correct-answer {
  color: var(--text-secondary);
  font-size: 14px;
}

.explanation-box {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 14px;
}

/* 按钮栏 */
.action-bar {
  flex-shrink: 0;
  padding: 8px 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-card);
}

/* ----- 答题卡 ----- */
.answer-sheet h3 {
  margin: 0 0 12px 0;
  text-align: center;
  font-weight: 500;
  font-size: 16px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.sheet-group {
  margin-bottom: 12px;
}

.sheet-group h4 {
  font-size: 12px;
  margin: 6px 0 4px;
  color: var(--text-secondary);
  border-left: 3px solid var(--accent-blue);
  padding-left: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sheet-items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sheet-item {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  transition: var(--transition);
}

.sheet-item:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.sheet-item.current {
  border: 2px solid var(--accent-blue);
  box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.25);
}

.sheet-item.submitted-correct {
  background: var(--accent-green);
  border-color: var(--accent-green);
  color: #fff;
}

.sheet-item.submitted-wrong {
  background: var(--accent-red);
  border-color: var(--accent-red);
  color: #fff;
}

.sheet-item.not-submitted {
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

/* 加载 */
.loading {
  text-align: center;
  padding: 60px 0;
  color: var(--text-secondary);
  font-size: 18px;
}

.wrong-badge {
  background: var(--accent-red);
  color: #fff;
  padding: 0 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-left: 10px;
}

.sheet-item.is-wrong {
  background: var(--accent-red);
  border-color: var(--accent-red);
  color: #fff;
}

.mode-badge {
  background: var(--bg-secondary);
  padding: 2px 12px;
  border-radius: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.mode-label {
  position: relative;
  cursor: pointer;
  padding: 4px 16px;
  border-radius: 16px;
  font-size: 14px;
  color: var(--text-secondary);
  transition: var(--transition);
  user-select: none;
}

.mode-label input[type="radio"] {
  display: none;
}

.mode-label.active {
  background: var(--accent-blue);
  color: #fff;
}

.mode-label:not(.active):hover {
  color: var(--text-primary);
}

.badge {
  margin-left: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.sheet-item.submitted {
  background: var(--accent-green);
  color: #fff;
  border-color: var(--accent-green);
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
  padding: 30px;
  border-radius: var(--radius);
  max-width: 400px;
  text-align: center;
}

.modal-content h2 {
  margin-top: 0;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 20px;
}

.btn-warning {
  background: #d29922;
  color: #fff;
}

.btn-warning:hover {
  background: #bb8009;
}

.result-placeholder {
  color: var(--text-secondary);
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

.paper-selector {
  padding: 4px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
</style>