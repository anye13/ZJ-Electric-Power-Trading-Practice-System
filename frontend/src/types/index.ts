// 试卷
export interface Paper {
    id: number;
    title: string;
    total_questions: number;
    created_at: string;
}
export interface KnowledgePoint {
    id: number;
    name: string;
    description?: string;
}
// 题目类型
export type QuestionType = 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_in_blank' | 'calculation' | 'essay';
export interface Question {
    id: number;
    type: QuestionType;
    content: string;
    options: string[];
    answer: string | boolean | string[];
    explanation: string;
    steps: string[];
    status?: string;
    paper_id?: number;        // 确保存在
    knowledge?: KnowledgePoint[];
    knowledge_ids?: number[];
}

// 前端显示的题目数据（包含用户答案等）
export interface DisplayQuestion extends Question {
    user_answer: any;
    submitted: boolean;
    result: boolean;
    correct_count: number;
    correct_answer: any;
    is_wrong: boolean;
}

// 答题卡项
export interface SheetItem {
    pos: number;
    index: number;
    id: number;
    type: QuestionType;
    is_wrong: boolean;
    submitted: boolean; // 新增
}

export interface SheetData {
    total: number;
    items: SheetItem[];
    current_pos: number;
}

// 分页列表
export interface PageResult<T> {
    items: T[];
    total: number;
    page: number;
    per_page: number;
}

// 导入结果
export interface ImportResult {
    added: number;
    skipped: number;
}

// 统计
export interface StatsData {
    total_questions: number;
    wrong_total: number;
    type_stats: { type: string; wrong_count: number }[];
}
