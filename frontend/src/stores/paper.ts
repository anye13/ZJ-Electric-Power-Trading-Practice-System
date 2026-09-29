import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import * as api from '@/api';
import type { Paper } from '@/types';

export const usePaperStore = defineStore('paper', () => {
    const papers = ref<Paper[]>([]);
    const selectedPaperId = ref<number | null>(null);
    let initPromise: Promise<void> | null = null;

    const selectedPaper = computed(() =>
        papers.value.find(p => p.id === selectedPaperId.value) || null
    );

    async function loadPapers() {
        try {
            papers.value = await api.getPapers();
        } catch (e) {
            console.error('加载试卷失败', e);
        }
    }

    async function init() {
        await loadPapers();
        try {
            const settings = await api.getUserSettings();
            selectedPaperId.value = settings.paper_id ?? null;
        } catch (e) {
            console.error('加载用户设置失败', e);
        }
    }

    /** 只在首次真正请求，后续子组件调用返回同一 Promise */
    function ensureInit(): Promise<void> {
        if (!initPromise) {
            initPromise = init();
        }
        return initPromise;
    }

    /** 切换试卷：更新本地状态并同步到后端 */
    async function setPaper(id: number | null) {
        selectedPaperId.value = id;
        try {
            await api.updateSettings({ paper_id: id });
        } catch (e) {
            console.error('同步试卷设置失败', e);
        }
    }

    /** 外部新增/删除试卷后刷新列表 */
    async function reloadPapers() {
        await loadPapers();
    }

    return {
        papers,
        selectedPaperId,
        selectedPaper,
        ensureInit,
        setPaper,
        reloadPapers,
    };
});