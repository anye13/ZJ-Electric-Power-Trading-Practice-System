import { defineStore } from 'pinia';
import { ref, computed, nextTick } from 'vue';
import * as api from '@/api';
import type { DisplayQuestion, SheetData, SheetItem } from '@/types';

export const useExamStore = defineStore('exam', () => {
    const title = ref('');
    const currentPos = ref(0);
    const totalDisplay = ref(0);
    const totalAll = ref(0);
    const filterWrong = ref(false);
    const randomOrder = ref(false);
    const question = ref<DisplayQuestion | null>(null);
    const sheetData = ref<SheetData>({ total: 0, items: [], current_pos: 0 });
    const selectedAnswer = ref<any>(null);
    const textAnswer = ref('');
    const errorMessage = ref('');
    const submitResult = ref<{ correct: boolean; message: string } | null>(null);
    const practiceLimit = ref(20);
    // 保存所有题目的用户答案 { [questionId]: answer }
    const userAnswers = ref<Record<number, any>>({});
    let settingsLoaded = false;
    const paperId = ref<number | null>(null);
    // ===== Getters =====
    const typeName = computed(() => {
        if (!question.value) return '';
        const map: Record<string, string> = {
            single_choice: '单选题',
            multiple_choice: '多选题',
            true_false: '判断题',
            fill_in_blank: '填空题',
            calculation: '计算题',
            essay: '解答题',
        };
        return map[question.value.type] || question.value.type;
    });

    const optionsList = computed(() => {
        if (!question.value) return [];
        const q = question.value;
        if (q.type === 'true_false') {
            return [
                { value: true, label: '正确' },
                { value: false, label: '错误' }
            ];
        }
        if (q.type === 'single_choice' || q.type === 'multiple_choice') {
            return q.options.map((opt, idx) => ({
                value: String.fromCharCode(65 + idx),
                label: opt
            }));
        }
        return [];
    });

    const inputType = computed(() => {
        if (!question.value) return 'radio';
        return question.value.type === 'multiple_choice' ? 'checkbox' : 'radio';
    });

    const isTextInput = computed(() => {
        if (!question.value) return false;
        return ['fill_in_blank', 'calculation', 'essay'].includes(question.value.type);
    });

    const renderedContent = computed(() => {
        const q = question.value;
        if (!q || typeof q.content !== 'string') return '';
        return q.content
            .replace(/\$\$(.*?)\$\$/g, (_, p1) => `\\(${p1}\\)`)
            .replace(/\$(.*?)\$/g, (_, p1) => `\\(${p1}\\)`);
    });

    const sheetGroups = computed(() => {
        const groups: Record<string, SheetItem[]> = {};
        sheetData.value.items.forEach(item => {
            if (!groups[item.type]) groups[item.type] = [];
            groups[item.type].push(item);
        });
        return groups;
    });

    // ===== 本地存储 =====
    function loadUserAnswers() {
        const stored = localStorage.getItem('userAnswers');
        if (stored) {
            try { userAnswers.value = JSON.parse(stored); } catch { }
        }
    }
    function saveUserAnswers() {
        localStorage.setItem('userAnswers', JSON.stringify(userAnswers.value));
    }

    // ===== Actions =====
    async function loadQuestion() {
        if (!settingsLoaded) {
            await loadSettings();
            settingsLoaded = true;
        }
        try {
            loadUserAnswers();
            const data = await api.getCurrentQuestion();
            // 处理空状态（无题目）
            if (data.total_display === 0 && data.total_all > 0) {
                question.value = null;
                currentPos.value = 0;
                totalDisplay.value = 0;
                totalAll.value = data.total_all;
                errorMessage.value = '';
                submitResult.value = null;
                sheetData.value = { total: 0, items: [], current_pos: 0 };
                return;
            }
            question.value = data;
            currentPos.value = data.current_pos;
            totalDisplay.value = data.total_display;
            totalAll.value = data.total_all;

            // 从保存的答案中恢复当前题目的答案
            const currentId = data.id;
            const saved = userAnswers.value[currentId];
            if (saved !== undefined) {
                if (data.type === 'multiple_choice') {
                    selectedAnswer.value = Array.isArray(saved) ? saved : [];
                } else if (data.type === 'true_false') {
                    selectedAnswer.value = saved === true || saved === 'true' ? true : false;
                } else {
                    selectedAnswer.value = saved;
                }
                if (['fill_in_blank', 'calculation', 'essay'].includes(data.type)) {
                    textAnswer.value = typeof saved === 'string' ? saved : '';
                }
            } else {
                // 无保存答案，根据题型重置
                if (data.type === 'multiple_choice') {
                    selectedAnswer.value = [];
                } else {
                    selectedAnswer.value = null;
                }
                textAnswer.value = '';
            }

            errorMessage.value = '';
            submitResult.value = null;
            await loadSheet();
        } catch (e: any) {
            if (e.response && e.response.status === 404 && filterWrong.value) {
                question.value = null;
                totalDisplay.value = 0;
                totalAll.value = 0;
                errorMessage.value = '';
                sheetData.value = { total: 0, items: [], current_pos: 0 };
                return;
            }
            if (e.response && e.response.data && e.response.data.error) {
                const msg = e.response.data.error;
                errorMessage.value = msg === '没有符合条件的题目' ? '暂无错题' : msg;
            } else {
                errorMessage.value = '无法连接服务器，请检查后端是否运行。';
            }
            question.value = null;
        }
    }

    async function loadSheet() {
        const data = await api.getAnswerSheet();
        data.items.forEach(item => {
            item.submitted = userAnswers.value[item.id] !== undefined;
        });
        sheetData.value = data;
        // 统一在此处渲染公式，避免重复
        await nextTick();
        if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
            try {
                await window.MathJax.typesetPromise();
            } catch (e) {
                console.warn('MathJax 渲染失败', e);
            }
        }
    }
    async function loadSettings() {
        try {
            const settings = await api.getUserSettings();
            filterWrong.value = settings.filter_wrong;
            randomOrder.value = settings.random_order;
            practiceLimit.value = settings.practice_limit || 20;
            paperId.value = settings.paper_id ?? null;
        } catch (e) {
            console.warn('加载设置失败', e);
        }
    }

    async function updateSettings(extra?: { limit?: number; paper_id?: number | null }) {
        const payload: any = {
            filter_wrong: filterWrong.value,
            random_order: randomOrder.value,
        };
        if (extra?.limit !== undefined) {
            payload.limit = extra.limit;
        }
        if (extra?.paper_id !== undefined) {   // ← 关键
            payload.paper_id = extra.paper_id;
        }
        const response = await api.updateSettings(payload);
        // 若响应返回 paper_id，同步到本地状态
        if (response.paper_id !== undefined) {
            // 可选：store 中若有 paperId 状态可以更新
        }
        await loadQuestion();
    }


    async function submitAnswer() {
        if (!question.value) return;
        const q = question.value;
        let answer: any = null;
        if (q.type === 'single_choice' || q.type === 'true_false') {
            answer = selectedAnswer.value;
            if (answer === null || answer === undefined) {
                alert('请选择一个选项');
                return;
            }
        } else if (q.type === 'multiple_choice') {
            if (!Array.isArray(selectedAnswer.value) || selectedAnswer.value.length === 0) {
                alert('请至少选择一个选项');
                return;
            }
            answer = selectedAnswer.value;
        } else if (q.type === 'fill_in_blank' || q.type === 'calculation' || q.type === 'essay') {
            if (!textAnswer.value.trim()) {
                alert('请输入答案');
                return;
            }
            answer = textAnswer.value.trim();
        } else {
            alert('未知题型');
            return;
        }

        const result = await api.submitAnswer(q.id, answer);

        // 保存用户答案（无论对错）
        userAnswers.value[q.id] = answer;
        saveUserAnswers();

        submitResult.value = {
            correct: result.correct,
            message: result.correct ? '✅ 回答正确' : '❌ 回答错误'
        };

        if (question.value) {
            question.value.is_wrong = result.is_wrong;
        }

        await loadSheet();

        if (result.all_done) {
            // watch 会触发
        }
    }

    async function navigate(direction: 'prev' | 'next') {
        const response = await api.navigate(direction);
        if (response.is_last) {
            return response;
        }
        question.value = response;
        currentPos.value = response.current_pos;
        totalDisplay.value = response.total_display;
        totalAll.value = response.total_all;

        const currentId = response.id;
        const saved = userAnswers.value[currentId];
        if (saved !== undefined) {
            if (response.type === 'multiple_choice') {
                selectedAnswer.value = Array.isArray(saved) ? saved : [];
            } else if (response.type === 'true_false') {
                selectedAnswer.value = saved === true || saved === 'true' ? true : false;
            } else {
                selectedAnswer.value = saved;
            }
            if (['fill_in_blank', 'calculation', 'essay'].includes(response.type)) {
                textAnswer.value = typeof saved === 'string' ? saved : '';
            }
        } else {
            if (response.type === 'multiple_choice') {
                selectedAnswer.value = [];
            } else {
                selectedAnswer.value = null;
            }
            textAnswer.value = '';
        }

        submitResult.value = null;
        await loadSheet();  // loadSheet 会触发 MathJax 渲染
        return response;
    }

    async function jumpTo(pos: number) {
        const data = await api.jumpTo(pos);
        question.value = data;
        currentPos.value = data.current_pos;
        totalDisplay.value = data.total_display;
        totalAll.value = data.total_all;

        const currentId = data.id;
        const saved = userAnswers.value[currentId];
        if (saved !== undefined) {
            if (data.type === 'multiple_choice') {
                selectedAnswer.value = Array.isArray(saved) ? saved : [];
            } else if (data.type === 'true_false') {
                selectedAnswer.value = saved === true || saved === 'true' ? true : false;
            } else {
                selectedAnswer.value = saved;
            }
            if (['fill_in_blank', 'calculation', 'essay'].includes(data.type)) {
                textAnswer.value = typeof saved === 'string' ? saved : '';
            }
        } else {
            if (data.type === 'multiple_choice') {
                selectedAnswer.value = [];
            } else {
                selectedAnswer.value = null;
            }
            textAnswer.value = '';
        }

        submitResult.value = null;
        await loadSheet();
    }

    async function resetAll() {
        if (confirm('确定重置所有错题记录？')) {
            await api.resetAll();
            userAnswers.value = {};
            saveUserAnswers();
            await loadQuestion();
        }
    }

    async function reloadQuestions() {
        if (confirm('刷新题库？')) {
            await api.reloadQuestions();
            await loadQuestion();
        }
    }

    loadUserAnswers();

    return {
        title,
        currentPos,
        totalDisplay,
        totalAll,
        filterWrong,
        randomOrder,
        question,
        sheetData,
        selectedAnswer,
        textAnswer,
        errorMessage,
        submitResult,
        userAnswers,
        typeName,
        optionsList,
        inputType,
        isTextInput,
        renderedContent,
        sheetGroups,
        loadQuestion,
        loadSheet,
        updateSettings,
        submitAnswer,
        navigate,
        jumpTo,
        resetAll,
        reloadQuestions,
    };
});