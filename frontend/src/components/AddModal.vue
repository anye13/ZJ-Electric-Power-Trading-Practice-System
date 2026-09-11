<template>
    <div v-if="visible" class="modal-overlay" @click.self="close">
        <div class="modal-content">
            <div class="modal-header">
                <h2>➕ 新增题目</h2>
                <button class="close-btn" @click="close">&times;</button>
            </div>
            <div class="modal-body">
                <form @submit.prevent="submitAdd">
                    <div class="form-group">
                        <label>所属试卷：</label>
                        <select v-model="form.paper_id">
                            <option v-for="p in papers" :key="p.id" :value="p.id">{{ p.title }}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>知识点：</label>
                        <select v-model="form.knowledge_ids" multiple style="height: auto;">
                            <option v-for="kp in allKnowledgePoints" :key="kp.id" :value="kp.id">{{ kp.name }}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>题型：</label>
                        <select v-model="form.type">
                            <option value="single_choice">单选题</option>
                            <option value="multiple_choice">多选题</option>
                            <option value="true_false">判断题</option>
                            <option value="fill_in_blank">填空题</option>
                            <option value="calculation">计算题</option>
                            <option value="essay">解答题</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>题目内容：</label>
                        <textarea v-model="form.content" rows="4" required></textarea>
                    </div>

                    <!-- 选项（仅选择题显示） -->
                    <div v-if="['single_choice', 'multiple_choice', 'true_false'].includes(form.type)"
                        class="form-group">
                        <label>选项：</label>
                        <div v-for="(opt, idx) in ['A', 'B', 'C', 'D']" :key="idx" class="option-row">
                            <span class="option-label">{{ opt }}</span>
                            <input type="text" v-model="form.options[idx]" :placeholder="`选项 ${opt}`" />
                        </div>
                    </div>

                    <!-- 答案（根据题型动态） -->
                    <div class="form-group">
                        <label>答案：</label>
                        <!-- 单选题：下拉选择 A-D -->
                        <select v-if="form.type === 'single_choice'" v-model="form.answer">
                            <option value="">请选择</option>
                            <option v-for="opt in 'ABCD'" :key="opt" :value="opt">{{ opt }}</option>
                        </select>
                        <!-- 多选题：四个复选框 -->
                        <div v-else-if="form.type === 'multiple_choice'" class="checkbox-group">
                            <label v-for="opt in 'ABCD'" :key="opt" class="checkbox-label">
                                <input type="checkbox" :value="opt" v-model="form.answer" />
                                {{ opt }}
                            </label>
                        </div>
                        <!-- 判断题：正确/错误单选 -->
                        <div v-else-if="form.type === 'true_false'" class="radio-group">
                            <label><input type="radio" value="true" v-model="form.answer" /> 正确</label>
                            <label><input type="radio" value="false" v-model="form.answer" /> 错误</label>
                        </div>
                        <!-- 填空/计算/解答：文本输入 -->
                        <input v-else type="text" v-model="form.answer" placeholder="请输入答案" />
                    </div>

                    <div class="form-group">
                        <label>解析：</label>
                        <textarea v-model="form.explanation" rows="3"></textarea>
                    </div>

                    <div class="form-group">
                        <label>步骤（每行一个）：</label>
                        <textarea v-model="stepsText" rows="3" placeholder="例如：&#10;步骤1：...&#10;步骤2：..."></textarea>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary" :disabled="saving">
                            {{ saving ? '添加中...' : '添加' }}
                        </button>
                        <button type="button" class="btn" @click="close">取消</button>
                    </div>
                    <div v-if="error" class="error-info">{{ error }}</div>
                </form>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue';
import * as api from '@/api';
import type { Paper, KnowledgePoint } from '@/types';

const props = defineProps<{ visible: boolean }>();
const emit = defineEmits<{
    (e: 'update:visible', value: boolean): void;
    (e: 'added'): void;
}>();

const papers = ref<Paper[]>([]);
const allKnowledgePoints = ref<KnowledgePoint[]>([]);

const form = reactive({
    type: 'single_choice',
    content: '',
    options: ['', '', '', ''],
    answer: '' as any,
    explanation: '',
    paper_id: null as number | null,
    knowledge_ids: [] as number[],   // 新增
});

const stepsText = ref('');
const saving = ref(false);
const error = ref('');

async function loadPapers() {
    try {
        papers.value = await api.getPapers();
        if (papers.value.length > 0 && form.paper_id === null) {
            form.paper_id = papers.value[0].id;
        }
    } catch (e) {
        console.error('加载试卷失败', e);
    }
}

async function loadKnowledgePoints() {
    try {
        allKnowledgePoints.value = await api.getKnowledgePoints();
    } catch (e) {
        console.error('加载知识点失败', e);
    }
}

// 提交
const submitAdd = async () => {
    try {
        if (!form.content.trim()) { error.value = '请输入题目内容'; return; }
        if (['single_choice', 'multiple_choice', 'true_false'].includes(form.type)) {
            if (form.options.some(o => !o.trim())) { error.value = '请填写所有选项'; return; }
        }
        if (form.type === 'single_choice' && !form.answer) { error.value = '请选择正确答案'; return; }
        if (form.type === 'multiple_choice' && (!Array.isArray(form.answer) || form.answer.length === 0)) { error.value = '请至少选择一个正确答案'; return; }
        if (form.type === 'true_false' && !form.answer) { error.value = '请选择正确或错误'; return; }
        if (['fill_in_blank', 'calculation', 'essay'].includes(form.type) && !form.answer.trim()) { error.value = '请输入答案'; return; }

        const payload: any = {
            type: form.type,
            content: form.content,
            options: form.options.filter(o => o.trim() !== ''),
            answer: form.answer,
            explanation: form.explanation,
            steps: stepsText.value.split('\n').filter(s => s.trim() !== ''),
            paper_id: form.paper_id || 1,
            knowledge_ids: form.knowledge_ids,  // 传递知识点ID
        };

        saving.value = true;
        await api.createQuestion(payload);
        emit('added');
        close();
    } catch (e: any) {
        error.value = e.message || '添加失败';
    } finally {
        saving.value = false;
    }
};

const close = () => {
    emit('update:visible', false);
    form.type = 'single_choice';
    form.content = '';
    form.options = ['', '', '', ''];
    form.answer = '';
    form.explanation = '';
    form.paper_id = null;
    form.knowledge_ids = [];
    stepsText.value = '';
    error.value = '';
    saving.value = false;
};

// 关键：使用 immediate watch
watch(() => props.visible, (val) => {
    if (val) {
        loadPapers();
        loadKnowledgePoints();
    }
}, { immediate: true });

// 兜底：挂载时也加载一次
onMounted(() => {
    if (props.visible) {
        loadPapers();
        loadKnowledgePoints();
    }
});
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
    z-index: 1000;
}

.modal-content {
    background: var(--bg-card);
    border-radius: var(--radius);
    max-width: 600px;
    width: 90%;
    height: 80vh;
    /* 固定高度 */
    max-height: 80vh;
    /* 确保不超出屏幕 */
    overflow-y: auto;
    /* 内容溢出时滚动 */
    padding: 24px;
    border: 1px solid var(--border-color);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
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

.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    font-weight: 500;
    margin-bottom: 4px;
    color: var(--text-secondary);
}

.form-group textarea,
.form-group select,
.form-group input[type="text"] {
    width: 100%;
    padding: 6px 10px;
    background: var(--bg-input);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: 6px;
}

.option-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}

.option-label {
    width: 20px;
    font-weight: 600;
    color: var(--text-secondary);
}

.option-row input[type="text"] {
    flex: 1;
}

.checkbox-group,
.radio-group {
    display: flex;
    gap: 16px;
}

.checkbox-group label,
.radio-group label {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
}

.form-actions {
    display: flex;
    gap: 10px;
    margin-top: 16px;
}

.btn {
    padding: 6px 16px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.btn-primary {
    background: var(--accent-blue);
    color: #fff;
}

.btn-primary:disabled {
    opacity: 0.5;
}

.error-info {
    margin-top: 8px;
    color: var(--accent-red);
}
</style>