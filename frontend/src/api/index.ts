import axios from 'axios';
import type { Question, DisplayQuestion, SheetData, PageResult, ImportResult } from '@/types';

const api = axios.create({
    baseURL: '/api',
    timeout: 10000,
});
// 请求拦截器 - 打印请求信息
api.interceptors.request.use(
    (config) => {
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 响应拦截器 - 打印响应信息
api.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        return Promise.reject(error);
    }
);
// 定义返回类型
interface SubmitResponse {
    correct: boolean;
    correct_answer: any;
    explanation: string;
    steps: string[];
    is_wrong: boolean;
    all_done: boolean;   // 新增
}

// ========== 做题相关 ==========
export const getCurrentQuestion = () => api.get('/questions').then(res => res.data);

export const submitAnswer = (questionId: number, answer: any): Promise<SubmitResponse> =>
    api.post('/submit', { index: questionId, answer }).then(res => res.data);

export const navigate = (direction: 'prev' | 'next') =>
    api.post('/navigate', { direction }).then(res => res.data);
export const refreshQuestions = () =>
    api.post('/refresh').then(res => res.data);
// 修改 updateSettings 为接受对象参数
export const updateSettings = (data: {
    filter_wrong?: boolean;
    random_order?: boolean;
    limit?: number;
    paper_id?: number | null;
}) => api.post('/settings', data).then(res => res.data);

export const resetAll = () => api.post('/reset_all').then(res => res.data);
export const resetCorrect = () => api.post('/reset_correct').then(res => res.data);
export const reloadQuestions = () => api.post('/reload').then(res => res.data);
export const getReport = () => api.get('/report').then(res => res.data.report);
export const downloadWrong = () => api.get('/wrong_questions', { responseType: 'blob' });

// 答题卡
export const getAnswerSheet = (): Promise<SheetData> =>
    api.get('/answer_sheet').then(res => res.data);

export const jumpTo = (pos: number) =>
    api.post('/jump', { pos }).then(res => res.data);

// ========== 管理相关 ==========
export const getQuestionList = (
    page: number,
    perPage: number,
    search: string,
    wrongOnly: boolean = false,
    type: string = '',
    unansweredOnly: boolean = false,
    paperId?: number
): Promise<PageResult<Question>> =>
    api.get('/manage/list', {
        params: { page, per_page: perPage, search, wrong_only: wrongOnly, type, unanswered_only: unansweredOnly, paper_id: paperId }
    }).then(res => res.data);
export const getDailyStats = (year?: number, month?: number, paperId?: number | null) =>
    api.get('/daily_stats', {
        params: { year, month, paper_id: paperId ?? undefined }
    }).then(res => res.data);
export const importQuestions = (data: { paper_info: any; questions: any[] }): Promise<ImportResult> =>
    api.post('/import', data).then(res => res.data);

export const updateQuestion = (qid: number, data: Partial<Question>) =>
    api.put(`/manage/edit/${qid}`, data).then(res => res.data);

export const deleteQuestion = (qid: number) =>
    api.delete(`/manage/delete/${qid}`).then(res => res.data);
// ========== 新增 ==========
export const createQuestion = (data: Partial<Question>) =>
    api.post('/manage/create', data).then(res => res.data);

// ========== 批量删除 ==========
export const batchDeleteQuestions = (ids: number[]) =>
    api.post('/manage/batch_delete', { ids }).then(res => res.data);
export const getStats = (paperId?: number) =>
    api.get('/stats', { params: { paper_id: paperId } }).then(res => res.data);
export const saveProgress = (questionId: number, answer: any) =>
    api.post('/progress', { index: questionId, answer }).then(res => res.data);
export const getRecentWrong = (limit: number = 10, paperId?: number) =>
    api.get('/recent_wrong', { params: { limit, paper_id: paperId } }).then(res => res.data);
export const resetProgress = () => api.post('/reset_progress').then(res => res.data);
export const chopQuestion = (questionId: number) =>
    api.post('/chop_question', { index: questionId }).then(res => res.data);
export const chat = (message: string) =>
    api.post('/chat', { message }).then(res => res.data);
export const getWrongReport = (paperId?: number) =>
    api.get('/wrong_report', { params: { paper_id: paperId } }).then(res => res.data);
export const getUserSettings = () => api.get('/user_settings').then(res => res.data);
export const setCleanDays = (days: number) => api.post('/set_clean_days', { days }).then(res => res.data);
export const getPapers = () => api.get('/papers').then(res => res.data);
export const createPaper = (title: string) => api.post('/papers', { title }).then(res => res.data);
export const updatePaper = (id: number, title: string) => api.put(`/papers/${id}`, { title }).then(res => res.data);
export const deletePaper = (id: number) => api.delete(`/papers/${id}`).then(res => res.data);
// 知识点
export const getKnowledgePoints = () => api.get('/knowledge_points').then(res => res.data);
export const createKnowledgePoint = (name: string, description?: string) => api.post('/knowledge_points', { name, description }).then(res => res.data);
export const updateKnowledgePoint = (id: number, name: string, description?: string) => api.put(`/knowledge_points/${id}`, { name, description }).then(res => res.data);
export const deleteKnowledgePoint = (id: number) => api.delete(`/knowledge_points/${id}`).then(res => res.data);
export const getKnowledgeGraph = (paperId?: number) =>
    api.get('/knowledge_graph', { params: { paper_id: paperId } }).then(res => res.data);
// ========== 间隔重复 ==========
export const getSrsDue = (paperId?: number) =>
    api.get('/srs/due', { params: { paper_id: paperId } }).then(res => res.data);

export const reviewSrsCard = (cardId: number, quality: number) =>
    api.post('/srs/review', { card_id: cardId, quality }).then(res => res.data);

export const getSrsStats = (paperId?: number) =>
    api.get('/srs/stats', { params: { paper_id: paperId } }).then(res => res.data);

export const addToSrs = (questionId: number) =>
    api.post('/srs/add', { question_id: questionId }).then(res => res.data);

// ========== 图谱漫游 ==========
export const startGraphWalk = (knowledgeId: number) =>
    api.post('/graph/walk/start', { knowledge_id: knowledgeId }).then(res => res.data);

export const getRelatedKnowledge = (knowledgeId: number, paperId?: number) =>
    api.get('/graph/walk/related', { params: { knowledge_id: knowledgeId, paper_id: paperId } })
        .then(res => res.data);