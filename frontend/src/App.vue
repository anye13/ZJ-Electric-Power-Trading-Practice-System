<template>
  <div id="app">
    <header class="top-header">
      <!-- 移动端汉堡按钮 -->
      <button class="menu-toggle" @click="toggleSidebar" aria-label="菜单">
        <span></span><span></span><span></span>
      </button>

      <h1 class="app-title">📚 全国电力市场规则题库</h1>

      <!-- 试卷选择：桌面端才显示 -->
      <div class="header-center desktop-only">
        <label>📄 试卷：</label>
        <select :value="paperStore.selectedPaperId ?? ''" @change="onPaperChange" class="paper-selector">
          <option value="">全部试卷</option>
          <option v-for="p in paperStore.papers" :key="p.id" :value="p.id">
            {{ p.title }}
          </option>
        </select>
      </div>

      <span class="clock desktop-only">{{ now }}</span>

      <button class="chat-toggle" @click="toggleChat">💬 AI</button>
    </header>

    <!-- 侧边栏遮罩 -->
    <transition name="fade">
      <div v-if="sidebarOpen" class="sidebar-mask" @click="closeSidebar"></div>
    </transition>

    <div class="main-body">
      <nav class="sidebar" :class="{ open: sidebarOpen }">
        <!-- 移动端试卷选择（桌面端隐藏） -->
        <div class="sidebar-paper">
          <label>📄 试卷</label>
          <select :value="paperStore.selectedPaperId ?? ''" @change="onPaperChange" class="paper-selector-mobile">
            <option value="">全部试卷</option>
            <option v-for="p in paperStore.papers" :key="p.id" :value="p.id">
              {{ p.title }}
            </option>
          </select>
        </div>

        <ul>
          <li><router-link to="/" active-class="active">🏠 首页</router-link></li>
          <li><router-link to="/exam" active-class="active">✍️ 做题界面</router-link></li>
          <li><router-link to="/analysis" active-class="active">📊 数据统计</router-link></li>
          <li><router-link to="/wrong-analysis" active-class="active">📉 错题分析</router-link></li>
          <li><router-link to="/knowledge" active-class="active">🧠 知识图谱</router-link></li>
          <li><router-link to="/manage" active-class="active">📋 管理界面</router-link></li>
          <li><router-link to="/settings" active-class="active">⚙️ 设置</router-link></li>
        </ul>

        <div class="theme-toggle">
          <button @click="toggleTheme" class="theme-btn">
            {{ isDark ? '☀️ 亮色模式' : '🌙 暗色模式' }}
          </button>
        </div>
      </nav>

      <div class="content-area">
        <router-view v-slot="{ Component }">
          <keep-alive include="ExamPanel">
            <component :is="Component" @showImport="showImport = true" @edit="openEdit" @add="openAdd"
              ref="contentRef" />
          </keep-alive>
        </router-view>
      </div>
    </div>

    <ImportModal v-model:visible="showImport" @imported="onImported" />
    <EditModal v-model:visible="showEdit" :question="editingQuestion" @saved="onEditSaved" />
    <AIChatSidebar v-model:visible="showChat" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import ImportModal from './components/ImportModal.vue';
import EditModal from './components/EditModal.vue';
import type { Question } from './types';
import { useExamStore } from './stores/exam';
import AIChatSidebar from './components/AIChatSidebar.vue';
import { usePaperStore } from './stores/paper';
const now = ref(new Date().toLocaleString('zh-CN'));
let timer: number;
const showImport = ref(false);
const showEdit = ref(false);
const editingQuestion = ref<Question | null>(null);
const contentRef = ref<any>(null);
const route = useRoute();
const store = useExamStore();
const showChat = ref(false);
const isDark = ref(true); // 暗黑模式开关
const toggleChat = () => (showChat.value = !showChat.value);
const paperStore = usePaperStore();
// ========== 移动端侧边栏 ==========
const sidebarOpen = ref(false);
function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value; }
function closeSidebar() { sidebarOpen.value = false; }
function toggleTheme() {
  isDark.value = !isDark.value;
  updateTheme();
}
function updateTheme() {
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light');
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
}
function openEdit(q: Question) {
  editingQuestion.value = q;
  showEdit.value = true;
}

function openAdd() {
  editingQuestion.value = null; // null 表示新增
  showEdit.value = true;
}

function onImported() {
  showImport.value = false;
  if (route.path === '/manage') contentRef.value?.refresh?.();
}

function onEditSaved() {
  showEdit.value = false;
  editingQuestion.value = null;
  if (route.path === '/manage') contentRef.value?.refresh?.();
}
onMounted(async () => {
  timer = window.setInterval(() => {
    now.value = new Date().toLocaleString('zh-CN');
  }, 1000);
  const saved = localStorage.getItem('theme');
  isDark.value = saved !== 'light';
  updateTheme();
  // 全局只初始化一次
  await paperStore.ensureInit();
  // 做题状态初始化
  store.loadQuestion();
});
/** 切换试卷 */
async function onPaperChange(e: Event) {
  const val = (e.target as HTMLSelectElement).value;
  const id = val === '' ? null : parseInt(val);
  await paperStore.setPaper(id);
}
onUnmounted(() => clearInterval(timer));
// 路由切换时自动收起
watch(() => route.path, () => { sidebarOpen.value = false; });
// 路由切换时重置设置（可选）
watch(() => route.path, (newPath) => {
  // 仅当进入 /wrong 时强制错题模式（但侧边栏已移除 /wrong 路由，可忽略）
  if (newPath === '/wrong') {
    store.filterWrong = true;
    store.updateSettings();
  }
  // 离开时不做任何操作，保留用户选择
}, { immediate: true });
</script>

<style scoped>
#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* ===== 顶部栏 ===== */
.top-header {
  background: var(--bg-card);
  padding: 12px 25px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-center label {
  color: var(--text-secondary);
  font-size: 14px;
}

.paper-selector {
  padding: 4px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  min-width: 160px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.top-header h1 {
  margin: 0;
  font-size: 22px;
  color: var(--text-primary);
}

.clock {
  font-size: 16px;
  color: var(--text-secondary);
}

/* ===== 主体 flex ===== */
.main-body {
  display: flex;
  flex: 1;
  min-height: 0;
  margin-top: 0;
  gap: 0;
  background: var(--bg-primary);
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
  overflow-y: auto;
  padding: 15px 0;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}

.sidebar ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.sidebar li a {
  display: block;
  padding: 12px 20px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 16px;
  border-left: 3px solid transparent;
  transition: var(--transition);
}

.sidebar li a:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.sidebar li a.active {
  background: var(--bg-hover);
  border-left-color: var(--accent-blue);
  color: var(--text-primary);
  font-weight: 500;
}

.theme-toggle {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
}

.theme-btn {
  width: 100%;
  padding: 8px 12px;
  background: var(--bg-hover);
  color: var(--text-primary);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: var(--transition);
}

.theme-btn:hover {
  background: var(--border-color);
}

/* ===== 内容区 ===== */
.content-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: var(--bg-primary);
}

/* ===== 模态窗覆盖 ===== */
:deep(.modal-overlay) {
  background-color: rgba(0, 0, 0, 0.7);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chat-toggle {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  padding: 4px 12px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: var(--transition);
}

.chat-toggle:hover {
  background: var(--bg-hover);
}

/* 汉堡按钮：桌面端隐藏 */
.menu-toggle {
  display: none;
  flex-direction: column;
  gap: 5px;
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  border-radius: 6px;
}

.menu-toggle span {
  display: block;
  width: 22px;
  height: 2px;
  background: var(--text-primary);
  border-radius: 2px;
}

.menu-toggle:active {
  background: var(--bg-hover);
}

/* 侧边栏中的移动端试卷选择：桌面端隐藏 */
.sidebar-paper {
  display: none;
  padding: 12px 16px 4px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 8px;
}

.sidebar-paper label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.paper-selector-mobile {
  width: 100%;
  padding: 6px 10px;
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
}

/* 淡入淡出过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ========== 移动端适配 ========== */
@media (max-width: 768px) {
  .top-header {
    padding: 10px 12px;
    gap: 8px;
  }

  .menu-toggle {
    display: flex;
  }

  .desktop-only {
    display: none !important;
  }

  .app-title {
    flex: 1;
    font-size: 15px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-align: center;
    margin: 0;
  }

  .chat-toggle {
    padding: 5px 10px;
    font-size: 13px;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    width: 260px;
    max-width: 80vw;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    z-index: 200;
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.4);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar-mask {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 199;
  }

  .sidebar-paper {
    display: block;
  }

  .content-area {
    padding: 12px;
  }

  /* 侧边栏条目略高一点，便于手指点击 */
  .sidebar li a {
    padding: 14px 20px;
    font-size: 15px;
  }
}
</style>