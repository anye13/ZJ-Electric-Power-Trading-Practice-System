<template>
    <div class="analysis-wrapper">
        <h2>📊 错题分析报告</h2>
        <div class="actions">
            <button class="btn btn-primary" @click="loadReport" :disabled="loading">
                {{ loading ? '加载中...' : '生成报告' }}
            </button>
            <button class="btn" v-if="reportData.length" @click="exportMarkdown">导出 Markdown</button>
            <button class="btn" v-if="reportData.length" @click="exportPDF">导出 PDF</button>
            <button class="btn btn-success" v-if="reportData.length" @click="exportWord">导出 Word</button>
        </div>

        <div v-if="loading" class="loading">正在加载错题数据...</div>
        <div v-if="error" class="error-banner">{{ error }}</div>

        <div v-if="reportData.length" class="report-layout">
            <!-- 左侧题型侧边栏 -->
            <div class="type-sidebar">
                <h3>题型导航</h3>
                <ul>
                    <li v-for="type in typeList" :key="type" :class="{ active: selectedType === type }"
                        @click="selectType(type)">
                        {{ typeMap[type] || type }}
                        <span class="count">({{ groupedData[type].length }})</span>
                    </li>
                </ul>
            </div>

            <!-- 右侧内容区域 -->
            <div class="report-content" ref="reportContent">
                <div v-if="selectedType && groupedData[selectedType]" class="type-group">
                    <h2>{{ typeMap[selectedType] || selectedType }}</h2>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>题号</th>
                                <th>题目内容</th>
                                <th>解析</th>
                                <th>错误次数</th>
                                <th>最近错误</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="q in groupedData[selectedType]" :key="q.id">
                                <td>{{ q.id }}</td>
                                <td>{{ q.content }}</td>
                                <td>{{ q.explanation }}</td>
                                <td>{{ q.wrong_count }}</td>
                                <td>{{ q.last_wrong_time }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else class="empty">请从左侧选择题型</div>
            </div>
        </div>

        <div v-else-if="!loading && !error" class="empty">暂无错题记录</div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import * as api from '@/api';
import html2pdf from 'html2pdf.js';
import { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell } from 'docx';
import { usePaperStore } from '@/stores/paper';
const reportData = ref<any[]>([]);
const loading = ref(false);
const error = ref('');
const selectedType = ref<string>('');
const paperStore = usePaperStore();
const typeMap: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    fill_in_blank: '填空题',
    calculation: '计算题',
    essay: '解答题'
};

const groupedData = computed(() => {
    const groups: Record<string, any[]> = {};
    reportData.value.forEach(q => {
        const key = q.type;
        if (!groups[key]) groups[key] = [];
        groups[key].push(q);
    });
    return groups;
});

const typeList = computed(() => {
    const order = ['single_choice', 'multiple_choice', 'true_false', 'fill_in_blank', 'calculation', 'essay'];
    return Object.keys(groupedData.value).sort((a, b) => order.indexOf(a) - order.indexOf(b));
});

function selectType(type: string) {
    selectedType.value = type;
}
async function loadReport() {
    loading.value = true;
    error.value = '';
    try {
        const data = await api.getWrongReport(paperStore.selectedPaperId ?? undefined);
        reportData.value = data;
        if (typeList.value.length > 0) {
            selectedType.value = typeList.value[0];
        }
    } catch (e: any) {
        error.value = e.response?.data?.error || '加载失败';
    } finally {
        loading.value = false;
    }
}

function exportMarkdown() {
    let md = '# 错题分析报告\n\n';
    md += `生成时间：${new Date().toLocaleString('zh-CN')}\n\n`;
    for (const [type, items] of Object.entries(groupedData.value)) {
        md += `## ${typeMap[type] || type}\n\n`;
        md += '| 题号 | 题目内容 | 解析 | 错误次数 | 最近错误 |\n';
        md += '|------|----------|------|----------|----------|\n';
        items.forEach((q: any) => {
            md += `| ${q.id} | ${q.content.replace(/\|/g, '\\|')} | ${q.explanation.replace(/\|/g, '\\|')} | ${q.wrong_count} | ${q.last_wrong_time} |\n`;
        });
        md += '\n';
    }
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '错题分析报告.md';
    a.click();
    URL.revokeObjectURL(url);
}

function exportPDF() {
    const fullReport = document.createElement('div');
    fullReport.innerHTML = `
    <h1>错题分析报告</h1>
    <p>生成时间：${new Date().toLocaleString('zh-CN')}</p>
  `;
    for (const [type, items] of Object.entries(groupedData.value)) {
        let tableHTML = `<h2>${typeMap[type] || type}</h2><table border="1" cellpadding="5"><thead><tr><th>题号</th><th>题目内容</th><th>解析</th><th>错误次数</th><th>最近错误</th></tr></thead><tbody>`;
        items.forEach((q: any) => {
            tableHTML += `<tr><td>${q.id}</td><td>${q.content}</td><td>${q.explanation}</td><td>${q.wrong_count}</td><td>${q.last_wrong_time}</td></tr>`;
        });
        tableHTML += '</tbody></table>';
        fullReport.innerHTML += tableHTML;
    }
    document.body.appendChild(fullReport);
    html2pdf()
        .set({
            margin: 1,
            filename: '错题分析报告.pdf',
            html2canvas: { scale: 2 },
            jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
        })
        .from(fullReport)
        .save()
        .then(() => {
            document.body.removeChild(fullReport);
        });
}

async function exportWord() {
    const doc = new Document({
        sections: [{
            properties: {},
            children: [
                new Paragraph({ children: [new TextRun({ text: '错题分析报告', bold: true, size: 32 })] }),
                new Paragraph({ children: [new TextRun({ text: `生成时间：${new Date().toLocaleString('zh-CN')}`, size: 20 })] }),
                new Paragraph({ text: '' }),
                ...Object.entries(groupedData.value).flatMap(([type, items]) => {
                    const heading = new Paragraph({ children: [new TextRun({ text: typeMap[type] || type, bold: true, size: 24 })] });
                    const rows = items.map(q => {
                        return new TableRow({
                            children: [
                                new TableCell({ children: [new Paragraph(q.id.toString())] }),
                                new TableCell({ children: [new Paragraph(q.content)] }),
                                new TableCell({ children: [new Paragraph(q.explanation)] }),
                                new TableCell({ children: [new Paragraph(q.wrong_count.toString())] }),
                                new TableCell({ children: [new Paragraph(q.last_wrong_time || '')] })
                            ]
                        });
                    });
                    const table = new Table({
                        rows: [
                            new TableRow({
                                children: ['题号', '题目内容', '解析', '错误次数', '最近错误'].map(text => {
                                    return new TableCell({ children: [new Paragraph({ children: [new TextRun({ text, bold: true })] })] });
                                })
                            }),
                            ...rows
                        ]
                    });
                    return [heading, table, new Paragraph({ text: '' })];
                })
            ]
        }]
    });

    const blob = await Packer.toBlob(doc);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '错题分析报告.docx';
    a.click();
    URL.revokeObjectURL(url);
}
watch(
    () => paperStore.selectedPaperId,
    () => loadReport()
);
onMounted(async () => {
    await paperStore.ensureInit();
    loadReport();
});
</script>

<style scoped>
.analysis-wrapper {
    padding: 20px;
    background: var(--bg-primary);
    color: var(--text-primary);
}

.actions {
    display: flex;
    gap: 12px;
    margin: 16px 0;
}

.loading {
    color: var(--text-secondary);
}

.error-banner {
    background: rgba(248, 81, 73, 0.15);
    color: var(--accent-red);
    padding: 12px 16px;
    border-radius: var(--radius);
    border-left: 4px solid var(--accent-red);
    margin: 12px 0;
}

.report-layout {
    display: flex;
    gap: 20px;
    margin-top: 16px;
    height: calc(100vh - 260px);
    /* 固定高度，根据顶部元素调整 */
    min-height: 400px;
}

.type-sidebar {
    width: 200px;
    flex-shrink: 0;
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 16px;
    border: 1px solid var(--border-color);
    overflow-y: auto;
}

.type-sidebar h3 {
    margin: 0 0 12px 0;
    font-size: 16px;
    color: var(--text-secondary);
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 8px;
}

.type-sidebar ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.type-sidebar li {
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: var(--transition);
    color: var(--text-secondary);
}

.type-sidebar li:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.type-sidebar li.active {
    background: var(--accent-blue);
    color: #fff;
}

.type-sidebar li .count {
    font-size: 12px;
    opacity: 0.7;
}

.report-content {
    flex: 1;
    background: var(--bg-card);
    border-radius: var(--radius);
    padding: 20px;
    border: 1px solid var(--border-color);
    overflow-y: auto;
    height: 100%;
}

.type-group h2 {
    margin: 0 0 12px 0;
    color: var(--text-primary);
    font-size: 20px;
}

.table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.table th,
.table td {
    border: 1px solid var(--border-color);
    padding: 6px 10px;
    text-align: left;
}

.table th {
    background: var(--bg-secondary);
    color: var(--text-secondary);
}

.table td {
    color: var(--text-primary);
}

.empty {
    text-align: center;
    padding: 40px;
    color: var(--text-secondary);
}
</style>