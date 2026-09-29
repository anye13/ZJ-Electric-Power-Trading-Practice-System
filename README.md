# 项目依赖清单与环境配置指南

本文档用于帮助他人从 GitHub 克隆项目后，快速完成前后端环境配置与启动。项目分为 **后端 Flask + MySQL** 和 **前端 Vue3 + TypeScript + Vite** 两部分。

---

## 一、系统环境要求

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|----------|----------|------|
| Python | 3.9 | 3.10+ | 后端运行环境 |
| MySQL | 8.0 | 8.0+ | 数据库，需支持 JSON 类型 |
| Node.js | 18.0 | 20 LTS | 前端构建 |
| npm | 9.0 | 10+ | 随 Node.js 安装 |
| Git | 任意 | 最新 | 克隆代码 |

---

## 二、后端依赖（Python）

### 1. `backend/requirements.txt`

```
Flask>=3.0.0
Flask-Cors>=4.0.0
PyMySQL>=1.1.0
APScheduler>=3.10.4
zai>=0.1.0
zhipuai>=2.0.0
```

> 说明：
> - `zai` 是智谱AI新版 SDK，用于 AI 助手对话。
> - `zhipuai` 为旧版 SDK，代码中可能兼容引用。
> - 如不需要 AI 对话功能，可删除后两个依赖，并移除 `app.py` 中相关导入与路由。

### 2. 安装命令

```bash
cd backend
pip install -r requirements.txt
```

或手动安装：

```bash
pip install Flask Flask-Cors PyMySQL APScheduler zai zhipuai
```

---

## 三、前端依赖（Node.js）

### 1. `frontend/package.json` 依赖部分

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.7",
    "axios": "^1.6.0",
    "echarts": "^5.5.0",
    "marked": "^12.0.0",
    "html2pdf.js": "^0.10.1",
    "docx": "^8.5.0",
    "dayjs": "^1.11.10"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vue-tsc": "^2.0.0"
  }
}
```

### 2. 安装命令

```bash
cd frontend
npm install
```

### 3. 依赖用途说明

| 依赖 | 用途 |
|------|------|
| vue / vue-router / pinia | 核心框架、路由、状态管理 |
| axios | HTTP 请求 |
| echarts | 数据统计与知识图谱可视化 |
| marked | 错题分析 Markdown 渲染 |
| html2pdf.js | 错题分析导出 PDF |
| docx | 错题分析导出 Word |
| dayjs | 日期处理（首页日历） |
| typescript / vite / @vitejs/plugin-vue | 构建工具链 |

---

## 四、数据库配置

### 1. 创建数据库

```sql
CREATE DATABASE exam_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 修改 `backend/config.py`

```python
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "你的密码"
MYSQL_DB = "exam_db"
MYSQL_PORT = 3306

ZHIPU_API_KEY = "你的智谱API Key"   # 如不使用 AI 功能可留空
ZHIPU_MODEL = "glm-4-flash"
```

### 3. 数据库表结构

首次运行后端时会自动创建以下表：

- `paper_info`：试卷信息
- `questions`：题目
- `wrong_questions`：错题
- `knowledge_points`：知识点
- `question_knowledge`：题目-知识点关联
- `user_settings`：用户设置与进度

如需手动初始化，可运行：

```bash
cd backend
python -c "from data_manager import init_db; init_db()"
```

---

## 五、目录结构建议

```
project/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── data_manager.py
│   ├── requirements.txt
│   └── reset_ids.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── api/
│       ├── components/
│       ├── router/
│       ├── stores/
│       ├── types/
│       └── style.css
└── README.md
```

---

## 六、启动方式

### 后端

```bash
cd backend
python app.py
```

默认监听 `http://0.0.0.0:5000`，接口前缀 `/api`。

### 前端

```bash
cd frontend
npm run dev
```

默认监听 `http://localhost:5173`，通过 `vite.config.ts` 中的代理将 `/api` 转发到后端 5000 端口。

### 生产构建（可选）

```bash
cd frontend
npm run build
```

产物在 `frontend/dist/`，可部署到 Nginx 等。

---

## 七、`vite.config.ts` 关键配置

确保代理与别名正确：

```typescript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
});
```

---

## 八、首次使用流程

1. 启动 MySQL，创建 `exam_db` 数据库。
2. 修改 `backend/config.py` 数据库信息。
3. 启动后端（自动建表）。
4. 启动前端。
5. 浏览器打开 `http://localhost:5173`。
6. 进入“管理界面” → “新建试卷” → “导入题库”（JSON 格式见下）。
7. 进入“设置”选择试卷与模式。
8. 进入“做题界面”开始练习。

---

## 九、JSON 题库导入格式

```json
{
  "paper_info": {
    "title": "示例试卷",
    "total_questions": 2,
    "instructions": "",
    "question_types": ["single_choice", "true_false"]
  },
  "questions": [
    {
      "type": "single_choice",
      "content": "中国的首都是？",
      "options": ["A. 上海", "B. 北京", "C. 广州", "D. 深圳"],
      "answer": "B",
      "explanation": "北京是首都。",
      "steps": [],
      "knowledge": ["中国地理", "常识"]
    },
    {
      "type": "true_false",
      "content": "地球围绕太阳公转。",
      "options": ["正确", "错误"],
      "answer": true,
      "explanation": "事实。",
      "steps": [],
      "knowledge": ["天文常识"]
    }
  ]
}
```

> 建议每个题目都带 `knowledge` 字段，用于知识图谱构建。

---

## 十、常见问题

| 问题 | 解决 |
|------|------|
| 前端 404 / 无法连接后端 | 检查后端是否启动，`vite.config.ts` 代理是否指向 5000 |
| 数据库连接失败 | 检查 `config.py`，确认 MySQL 服务已启动 |
| `Duplicate column name` | 数据库迁移已做判断，若手动改过表请对照 `init_db()` |
| 知识图谱为空 | 确认 `question_knowledge` 表有数据，导入 JSON 时包含 `knowledge` |
| AI 对话报错 | 检查 `ZHIPU_API_KEY` 是否有效，或删除 AI 相关依赖与路由 |
| 试卷切换无效 | 确认前端 `updateSettings` 传递了 `paper_id`，后端 `/api/settings` 处理了该字段 |

---

## 十一、快速命令汇总

```bash
# 后端
cd backend
pip install -r requirements.txt
python app.py

# 前端
cd frontend
npm install
npm run dev
```

按以上步骤配置后，即可在本地完整运行本项目。