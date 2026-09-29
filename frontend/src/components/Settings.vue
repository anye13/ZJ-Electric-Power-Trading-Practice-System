<template>
    <div class="settings-container">
        <h2>⚙️ 设置</h2>
        <!-- 数据库配置 -->
        <div class="settings-card">
            <h3>🗄️ 数据库配置</h3>
            <p class="desc">
                修改后会自动测试连接并保存到后端目录下的 <code>db_config.json</code>。
                默认值来自 <code>config.py</code>，保存后立即生效。
            </p>

            <div class="db-grid">
                <div class="db-field">
                    <label>主机</label>
                    <input type="text" v-model="dbForm.host" placeholder="localhost" />
                </div>
                <div class="db-field">
                    <label>端口</label>
                    <input type="number" v-model.number="dbForm.port" placeholder="3306" min="1" max="65535" />
                </div>
                <div class="db-field">
                    <label>用户名</label>
                    <input type="text" v-model="dbForm.user" placeholder="root" />
                </div>
                <div class="db-field">
                    <label>密码</label>
                    <input type="password" v-model="dbForm.password"
                        :placeholder="dbMeta.has_password ? '不修改请留空' : '请输入密码'" />
                </div>
                <div class="db-field db-field-wide">
                    <label>数据库名</label>
                    <input type="text" v-model="dbForm.database" placeholder="exam_db" />
                </div>
            </div>

            <div class="db-actions">
                <button class="btn" @click="handleTestDb" :disabled="dbTesting">
                    {{ dbTesting ? '测试中...' : '🔌 测试连接' }}
                </button>
                <button class="btn btn-primary" @click="handleSaveDb" :disabled="dbSaving">
                    {{ dbSaving ? '保存中...' : '💾 保存配置' }}
                </button>
            </div>

            <div v-if="dbTestMsg" class="db-msg" :class="dbTestOk ? 'db-ok' : 'db-err'">
                {{ dbTestMsg }}
            </div>

            <p class="config-path" v-if="dbMeta.config_file">
                配置文件：<code>{{ dbMeta.config_file }}</code>
            </p>
        </div>
        <!-- AI 接口配置 -->
        <div class="settings-card">
            <h3>🤖 AI 接口配置</h3>
            <p class="desc">
                可配置多个 AI Provider（智谱 GLM / OpenAI 兼容），选择其中一个作为当前使用。
                设置保存在后端 <code>ai_config.json</code>。
            </p>

            <!-- Provider 列表 -->
            <div class="ai-list">
                <div v-for="p in aiConfig.providers" :key="p.id" class="ai-item"
                    :class="{ active: p.id === aiConfig.active_id }">
                    <div class="ai-item-info">
                        <div class="ai-name">
                            {{ p.name }}
                            <span v-if="p.id === aiConfig.active_id" class="current-tag">当前</span>
                        </div>
                        <div class="ai-meta">
                            {{ providerTypeName(p.provider) }} · {{ p.model }}
                        </div>
                        <div class="ai-key">
                            Key：{{ p.has_api_key ? p.api_key_masked : '未配置' }}
                        </div>
                    </div>
                    <div class="ai-item-actions">
                        <button class="btn btn-sm btn-primary" :disabled="p.id === aiConfig.active_id"
                            @click="handleSetActive(p.id)">
                            {{ p.id === aiConfig.active_id ? '已启用' : '启用' }}
                        </button>
                        <button class="btn btn-sm" @click="handleTestProvider(p.id)">测试</button>
                        <button class="btn btn-sm btn-edit" @click="openEditAi(p)">编辑</button>
                        <button class="btn btn-sm btn-danger" @click="handleDeleteAi(p)">删除</button>
                    </div>
                </div>
                <div v-if="aiConfig.providers.length === 0" class="empty-state">
                    尚未配置任何 AI Provider，请先添加
                </div>
            </div>

            <button v-if="!aiFormVisible" class="btn btn-success" @click="openAddAi">
                ➕ 添加 Provider
            </button>

            <!-- 新增/编辑表单 -->
            <div v-if="aiFormVisible" class="ai-form">
                <h4>{{ aiEditingId ? '编辑 Provider' : '新增 Provider' }}</h4>
                <div class="db-grid">
                    <div class="db-field">
                        <label>名称</label>
                        <input type="text" v-model="aiForm.name" placeholder="例如：智谱 GLM" />
                    </div>
                    <div class="db-field">
                        <label>类型</label>
                        <select v-model="aiForm.provider">
                            <option value="zhipu">智谱 GLM</option>
                            <option value="openai">OpenAI 兼容</option>
                        </select>
                    </div>
                    <div class="db-field db-field-wide">
                        <label>API Key</label>
                        <input type="password" v-model="aiForm.api_key"
                            :placeholder="aiEditingId ? '不修改请留空' : '请输入 API Key'" />
                    </div>
                    <div class="db-field">
                        <label>模型名</label>
                        <input type="text" v-model="aiForm.model" placeholder="glm-4.7-flash" />
                    </div>
                    <div class="db-field">
                        <label>Base URL（OpenAI 兼容时填）</label>
                        <input type="text" v-model="aiForm.base_url" placeholder="https://api.deepseek.com/v1" />
                    </div>
                    <div class="db-field">
                        <label>重试次数</label>
                        <input type="number" v-model.number="aiForm.retry_count" min="0" max="20" />
                    </div>
                    <div class="db-field">
                        <label>初始延迟（秒）</label>
                        <input type="number" v-model.number="aiForm.retry_delay" min="0" max="60" />
                    </div>
                </div>

                <div class="db-actions">
                    <button class="btn btn-primary" @click="handleSaveAi" :disabled="aiSaving">
                        {{ aiSaving ? '保存中...' : '保存' }}
                    </button>
                    <button class="btn" @click="cancelAiForm" :disabled="aiSaving">取消</button>
                </div>

                <div v-if="aiMessage" class="db-msg" :class="aiMessageOk ? 'db-ok' : 'db-err'">
                    {{ aiMessage }}
                </div>
            </div>
        </div>
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
                <button class="btn" @click="runCleanNow" :disabled="cleaning">
                    {{ cleaning ? '清理中...' : '🧹 立即清理' }}
                </button>
            </div>
            <div v-if="cleanDaysSaved" class="save-success">✅ 已保存，将在下次定时清理时生效</div>
            <div v-if="cleanMsg" class="save-success">{{ cleanMsg }}</div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useExamStore } from '@/stores/exam';
import * as api from '@/api';
import type { AiConfig } from '@/api';
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
const cleaning = ref(false);
const cleanMsg = ref('');
const aiConfig = ref<AiConfig>({ active_id: null, providers: [] });
const aiFormVisible = ref(false);
const aiEditingId = ref<string | null>(null);
const aiForm = ref({
    name: '',
    provider: 'zhipu',
    api_key: '',
    model: 'glm-4.7-flash',
    base_url: '',
    retry_count: 7,
    retry_delay: 2,
});
const aiSaving = ref(false);
const aiMessage = ref('');
const aiMessageOk = ref(false);
function providerTypeName(t: string) {
    return t === 'zhipu' ? '智谱 GLM' : t === 'openai' ? 'OpenAI 兼容' : t;
}

async function loadAiConfig() {
    try {
        aiConfig.value = await api.getAiConfig();
    } catch (e) {
        console.error('加载 AI 配置失败', e);
    }
}

function openAddAi() {
    aiEditingId.value = null;
    aiForm.value = {
        name: '',
        provider: 'zhipu',
        api_key: '',
        model: 'glm-4.7-flash',
        base_url: '',
        retry_count: 7,
        retry_delay: 2,
    };
    aiMessage.value = '';
    aiFormVisible.value = true;
}

function openEditAi(p: any) {
    aiEditingId.value = p.id;
    aiForm.value = {
        name: p.name || '',
        provider: p.provider || 'zhipu',
        api_key: '', // 留空表示不修改
        model: p.model || '',
        base_url: p.base_url || '',
        retry_count: p.retry_count ?? 7,
        retry_delay: p.retry_delay ?? 2,
    };
    aiMessage.value = '';
    aiFormVisible.value = true;
}

function cancelAiForm() {
    aiFormVisible.value = false;
    aiEditingId.value = null;
    aiMessage.value = '';
}

async function handleSaveAi() {
    aiSaving.value = true;
    aiMessage.value = '';
    try {
        const payload: any = { ...aiForm.value };
        if (aiEditingId.value) {
            // 编辑：密码留空不覆盖
            if (!payload.api_key) delete payload.api_key;
            await api.updateAiProvider(aiEditingId.value, payload);
            aiMessage.value = '✅ 已更新';
        } else {
            if (!payload.api_key) {
                aiMessageOk.value = false;
                aiMessage.value = '❌ 新增时必须填写 API Key';
                aiSaving.value = false;
                return;
            }
            await api.addAiProvider(payload);
            aiMessage.value = '✅ 已添加';
        }
        aiMessageOk.value = true;
        await loadAiConfig();
        setTimeout(() => {
            aiFormVisible.value = false;
            aiMessage.value = '';
        }, 800);
    } catch (e: any) {
        aiMessageOk.value = false;
        aiMessage.value = `❌ ${e.response?.data?.error || e.message}`;
    } finally {
        aiSaving.value = false;
    }
}

async function handleSetActive(id: string) {
    try {
        await api.setActiveAiProvider(id);
        await loadAiConfig();
    } catch (e: any) {
        alert(`切换失败：${e.response?.data?.error || e.message}`);
    }
}

async function handleTestProvider(id: string) {
    try {
        const res = await api.testAiProvider(id);
        if (res.success) {
            alert(`✅ 测试成功\n返回：${res.reply || '(空)'}`);
        } else {
            alert(`❌ 测试失败：${res.error}`);
        }
    } catch (e: any) {
        alert(`❌ 测试失败：${e.response?.data?.error || e.message}`);
    }
}

async function handleDeleteAi(p: any) {
    if (!confirm(`确定删除 Provider「${p.name}」？`)) return;
    try {
        await api.deleteAiProvider(p.id);
        await loadAiConfig();
    } catch (e: any) {
        alert(`删除失败：${e.response?.data?.error || e.message}`);
    }
}
// ========== 数据库配置 ==========
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
    await loadAiConfig();
});
// ========== 数据库配置 ==========
const dbForm = ref({
    host: '',
    user: '',
    password: '',
    database: '',
    port: 3306,
});
const dbMeta = ref<{ has_password?: boolean; config_file?: string }>({});
const dbTesting = ref(false);
const dbSaving = ref(false);
const dbTestMsg = ref('');
const dbTestOk = ref(false);
async function runCleanNow() {
    if (!confirm(`确定按 ${cleanDays.value} 天阈值立即清理吗？\n超时的已答题目将恢复为未作答状态。`)) return;
    cleaning.value = true;
    cleanMsg.value = '';
    try {
        await api.cleanProgress(cleanDays.value);
        cleanMsg.value = `✅ 已按 ${cleanDays.value} 天阈值清理完毕`;
        setTimeout(() => { cleanMsg.value = ''; }, 3000);
    } catch (e: any) {
        cleanMsg.value = `❌ 清理失败：${e.response?.data?.error || e.message}`;
    } finally {
        cleaning.value = false;
    }
}
async function loadDbConfig() {
    try {
        const cfg = await api.getDbConfig();
        dbMeta.value = {
            has_password: cfg.has_password,
            config_file: cfg.config_file,
        };
        dbForm.value = {
            host: cfg.host || '',
            user: cfg.user || '',
            password: '', // 不回显密码，留空表示不修改
            database: cfg.database || '',
            port: cfg.port || 3306,
        };
    } catch (e) {
        console.error('加载数据库配置失败', e);
    }
}

function buildDbPayload() {
    const payload: any = {
        host: dbForm.value.host,
        user: dbForm.value.user,
        database: dbForm.value.database,
        port: dbForm.value.port,
    };
    // 只有用户输入了新密码才带上
    if (dbForm.value.password && dbForm.value.password.length > 0) {
        payload.password = dbForm.value.password;
    }
    return payload;
}

async function handleTestDb() {
    dbTesting.value = true;
    dbTestMsg.value = '';
    try {
        const res = await api.testDbConfig(buildDbPayload());
        dbTestOk.value = !!res.success;
        dbTestMsg.value = res.success ? '✅ 连接成功' : `❌ ${res.error || '连接失败'}`;
    } catch (e: any) {
        dbTestOk.value = false;
        const err = e.response?.data?.error || e.message || '连接失败';
        dbTestMsg.value = `❌ ${err}`;
    } finally {
        dbTesting.value = false;
    }
}

async function handleSaveDb() {
    if (!confirm('确定保存并应用新的数据库配置？\n保存后会立即尝试重新连接并重载题库。')) return;
    dbSaving.value = true;
    dbTestMsg.value = '';
    try {
        const res = await api.saveDbConfig(buildDbPayload());
        dbTestOk.value = true;
        dbTestMsg.value = `✅ ${res.message || '保存成功'}`;
        // 密码框重置（下次再改需重新输入）
        dbForm.value.password = '';
        await loadDbConfig();
    } catch (e: any) {
        dbTestOk.value = false;
        const err = e.response?.data?.error || e.message || '保存失败';
        dbTestMsg.value = `❌ ${err}`;
    } finally {
        dbSaving.value = false;
    }
}
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

.db-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px 16px;
    margin: 12px 0;
    min-width: 0;
}

.db-field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
    /* 关键 1：允许收缩 */
}

.db-field-wide {
    grid-column: 1 / -1;
}

.db-field label {
    font-size: 13px;
    color: var(--text-secondary);
}

.db-field input {
    width: 100%;
    /* 关键 2：撑满格子 */
    min-width: 0;
    /* 关键 3：允许收缩，不撑破 */
    box-sizing: border-box;
    padding: 6px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 14px;
}

.db-actions {
    display: flex;
    gap: 12px;
    margin-top: 12px;
}

.db-msg {
    margin-top: 12px;
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 13px;
}

.db-ok {
    background: rgba(63, 185, 80, 0.12);
    color: var(--accent-green);
    border-left: 3px solid var(--accent-green);
}

.db-err {
    background: rgba(248, 81, 73, 0.12);
    color: var(--accent-red);
    border-left: 3px solid var(--accent-red);
}

.config-path {
    margin-top: 10px;
    font-size: 12px;
    color: var(--text-secondary);
    word-break: break-all;
}

.config-path code {
    background: var(--bg-secondary);
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 12px;
}

@media (max-width: 768px) {

    /* 数据库配置卡片降为单列 */
    .db-grid {
        grid-template-columns: 1fr;
        gap: 10px;
    }

    .db-field-wide {
        grid-column: auto;
    }

    .db-field input {
        font-size: 14px;
        /* 防止 iOS 自动放大 */
        padding: 8px 10px;
    }

    .db-actions {
        flex-direction: column;
        gap: 8px;
    }

    .db-actions .btn {
        width: 100%;
    }

    .config-path {
        font-size: 11px;
        word-break: break-all;
    }

    .settings-container {
        margin: 16px auto;
        padding: 0 12px;
    }

    .settings-container h2 {
        font-size: 22px;
        margin-bottom: 16px;
    }

    .settings-card {
        padding: 16px;
        margin-bottom: 16px;
    }

    .settings-card h3 {
        font-size: 16px;
    }

    .settings-card .desc {
        font-size: 13px;
    }

    .mode-options {
        flex-direction: column;
        gap: 10px;
    }

    .mode-option {
        min-width: 0;
        flex-direction: row;
        align-items: center;
        gap: 12px;
        padding: 14px;
        text-align: left;
    }

    .mode-option .mode-icon {
        font-size: 22px;
    }

    .mode-option .mode-name {
        font-size: 15px;
    }

    .mode-option .mode-desc {
        font-size: 12px;
    }

    .paper-setting,
    .limit-setting,
    .clean-setting {
        flex-direction: column;
        align-items: stretch;
        gap: 10px;
    }

    .paper-setting select,
    .limit-setting input[type="number"],
    .clean-setting input[type="number"] {
        width: 100%;
    }

    .limit-setting .unit,
    .clean-setting span {
        display: none;
        /* 有 label 就够了 */
    }

    .limit-setting .btn,
    .clean-setting .btn,
    .paper-setting .btn {
        width: 100%;
    }
}

/* ========== AI 配置 ========== */
.ai-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 12px 0;
}

.ai-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    min-width: 0;
}

.ai-item.active {
    border-color: var(--accent-blue);
    box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.15);
}

.ai-item-info {
    flex: 1;
    min-width: 0;
}

.ai-name {
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
}

.ai-meta {
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 2px;
}

.ai-key {
    color: var(--text-muted);
    font-size: 11px;
    margin-top: 2px;
    word-break: break-all;
}

.ai-item-actions {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    flex-shrink: 0;
}

.ai-form {
    margin-top: 16px;
    padding: 16px;
    background: var(--bg-secondary);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
    min-width: 0;
}

.ai-form h4 {
    margin: 0 0 12px 0;
    color: var(--text-primary);
}

/* 移动端适配 */
@media (max-width: 768px) {
    .ai-item {
        flex-direction: column;
        align-items: stretch;
    }

    .ai-item-actions {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 6px;
    }

    .ai-item-actions .btn {
        width: 100%;
    }

    .ai-form {
        padding: 12px;
    }
}
</style>