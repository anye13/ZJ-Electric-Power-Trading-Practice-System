import { defineStore } from 'pinia';
import { ref } from 'vue';
import * as api from '@/api';

export const useSrsStore = defineStore('srs', () => {
    const dueCards = ref<any[]>([]);
    const stats = ref({ total: 0, due: 0, today_reviewed: 0, mastered: 0 });
    const loading = ref(false);

    async function loadDue(paperId?: number) {
        loading.value = true;
        try {
            dueCards.value = await api.getSrsDue(paperId);
        } finally {
            loading.value = false;
        }
    }

    async function loadStats(paperId?: number) {
        stats.value = await api.getSrsStats(paperId);
    }

    async function review(cardId: number, quality: number) {
        await api.reviewSrsCard(cardId, quality);
        // 从待复习列表中移除
        dueCards.value = dueCards.value.filter(c => c.card_id !== cardId);
        // 更新统计
        await loadStats();
    }

    return { dueCards, stats, loading, loadDue, loadStats, review };
});