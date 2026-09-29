import json
import pymysql
from config import (
    MYSQL_HOST,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DB,
    MYSQL_PORT,
    TYPE_ORDER,
)
from datetime import datetime, timedelta, date
import sys
import re
import jieba
import os

# 停用词（可按需扩展）
STOP_WORDS = set(
    [
        "的",
        "了",
        "是",
        "在",
        "和",
        "与",
        "或",
        "及",
        "等",
        "这",
        "那",
        "有",
        "为",
        "对",
        "以",
        "并",
        "而",
        "但",
        "则",
        "之",
        "其",
        "它",
        "他",
        "她",
        "我",
        "你",
        "您",
        "我们",
        "你们",
        "他们",
        "一个",
        "一种",
        "以下",
        "关于",
        "根据",
        "按照",
        "下列",
        "哪些",
        "什么",
        "哪个",
        "属于",
        "不属于",
        "关于",
        "the",
        "a",
        "an",
        "is",
        "are",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "not",
        "with",
        "by",
        "as",
        "at",
        "from",
        "that",
        "this",
        "which",
    ]
)
# ============ 数据库配置文件（用户可覆盖 config.py 中的默认值） ============
DB_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "db_config.json"
)
_db_config_cache = None
# ============ AI 配置文件 ============
AI_CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "ai_config.json"
)

_ai_config_cache = None


def _tokenize(text: str) -> set:
    """使用 jieba 分词，返回去除停用词和标点后的词集合"""
    if not text:
        return set()
    # 去除 LaTeX 定界符和多余空白
    text = re.sub(r"\s+", "", text)
    text = text.replace("$", "").replace("\\", "")
    # 分词
    tokens = jieba.lcut(text)
    # 过滤停用词、标点、单字符、纯符号
    result = set()
    for tok in tokens:
        tok = tok.strip().lower()
        if not tok:
            continue
        if tok in STOP_WORDS:
            continue
        # 只保留中文字符、字母、数字组成的词
        if re.match(r"^[\u4e00-\u9fa5a-z0-9]+$", tok):
            result.add(tok)
    return result


def _load_db_config():
    """读取数据库配置：优先 db_config.json，否则回落到 config.py 默认值"""
    global _db_config_cache
    if _db_config_cache is not None:
        return _db_config_cache

    cfg = {
        "host": MYSQL_HOST,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "database": MYSQL_DB,
        "port": int(MYSQL_PORT),
    }
    if os.path.exists(DB_CONFIG_FILE):
        try:
            with open(DB_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for k in ("host", "user", "password", "database", "port"):
                if saved.get(k) not in (None, ""):
                    cfg[k] = int(saved[k]) if k == "port" else saved[k]
        except Exception as e:
            print(f"读取 db_config.json 失败，使用默认配置: {e}", file=sys.stderr)

    _db_config_cache = cfg
    return cfg


def get_db_config():
    """获取当前数据库配置（副本）"""
    return dict(_load_db_config())


def save_db_config(new_cfg):
    """写入 db_config.json 并刷新缓存"""
    global _db_config_cache
    with open(DB_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, ensure_ascii=False, indent=2)
    _db_config_cache = None
    print("✅ 数据库配置已保存到 db_config.json", file=sys.stderr)


def get_db(override=None):
    """获取数据库连接。override 用于测试连接而不修改全局配置。"""
    cfg = override if override else _load_db_config()
    return pymysql.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=int(cfg["port"]),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 试卷信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_info (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    title VARCHAR(255) NOT NULL,
                    total_questions INT DEFAULT 0,
                    instructions TEXT,
                    question_types JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 题目表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    type VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    options JSON,
                    answer JSON NOT NULL,
                    explanation TEXT,
                    steps JSON,
                    paper_id INT,
                    FOREIGN KEY (paper_id) REFERENCES paper_info(id) ON DELETE CASCADE
                )
            """)
            # 错题表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wrong_questions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT DEFAULT 1,
                    question_id INT NOT NULL,
                    wrong_count INT DEFAULT 1,
                    last_wrong_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_user_question (user_id, question_id)
                )
            """)
            # 用户设置表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INT PRIMARY KEY DEFAULT 1,
                    current_pos INT DEFAULT 0,
                    filter_wrong BOOLEAN DEFAULT FALSE,
                    random_order BOOLEAN DEFAULT FALSE,
                    progress JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            # 知识点表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_points (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 题目-知识点关联表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS question_knowledge (
                    question_id INT,
                    knowledge_id INT,
                    PRIMARY KEY (question_id, knowledge_id),
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge_points(id) ON DELETE CASCADE
                )
            """)

            # 费曼学习记录
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feynman_sessions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT DEFAULT 1,
                    question_id INT,
                    messages JSON,
                    score INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 图谱漫游记录
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_walks (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT DEFAULT 1,
                    knowledge_id INT,
                    path JSON,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # ========== 字段迁移（分别独立判断） ==========
            # progress_timestamp
            cursor.execute("SHOW COLUMNS FROM user_settings LIKE 'progress_timestamp'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE user_settings ADD COLUMN progress_timestamp JSON"
                )

            # paper_id
            cursor.execute("SHOW COLUMNS FROM user_settings LIKE 'paper_id'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE user_settings ADD COLUMN paper_id INT DEFAULT NULL"
                )

            # practice_limit
            cursor.execute("SHOW COLUMNS FROM user_settings LIKE 'practice_limit'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE user_settings ADD COLUMN practice_limit INT DEFAULT 20"
                )

            # clean_days
            cursor.execute("SHOW COLUMNS FROM user_settings LIKE 'clean_days'")
            if not cursor.fetchone():
                cursor.execute(
                    "ALTER TABLE user_settings ADD COLUMN clean_days INT DEFAULT 7"
                )

        conn.commit()
    finally:
        conn.close()


def _load_ai_config():
    """读取 AI 配置，首次运行会用 .env 里的智谱配置做种子"""
    global _ai_config_cache
    if _ai_config_cache is not None:
        return _ai_config_cache

    cfg = {"active_id": None, "providers": []}

    if os.path.exists(AI_CONFIG_FILE):
        try:
            with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                cfg["active_id"] = saved.get("active_id")
                cfg["providers"] = saved.get("providers") or []
        except Exception as e:
            print(f"读取 ai_config.json 失败: {e}", file=sys.stderr)
    else:
        # 首次启动，用 config.py 里的 ZHIPU_* 做种子
        from config import (
            ZHIPU_API_KEY,
            ZHIPU_MODEL,
            ZHIPU_RETRY_COUNT,
            ZHIPU_RETRY_DELAY,
        )

        if ZHIPU_API_KEY:
            seed = {
                "id": "seed-zhipu",
                "name": "智谱 GLM（来自 .env）",
                "provider": "zhipu",
                "api_key": ZHIPU_API_KEY,
                "model": ZHIPU_MODEL,
                "base_url": "",
                "retry_count": ZHIPU_RETRY_COUNT,
                "retry_delay": ZHIPU_RETRY_DELAY,
            }
            cfg["providers"] = [seed]
            cfg["active_id"] = seed["id"]
            try:
                with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                print("✅ 已根据 .env 生成 ai_config.json", file=sys.stderr)
            except Exception as e:
                print(f"写入 ai_config.json 失败: {e}", file=sys.stderr)

    _ai_config_cache = cfg
    return cfg


def get_ai_config(mask_key=True):
    """获取 AI 配置。mask_key=True 时脱敏 api_key 并标记 has_api_key"""
    cfg = _load_ai_config()
    if not mask_key:
        return cfg

    masked = {"active_id": cfg.get("active_id"), "providers": []}
    for p in cfg.get("providers", []):
        item = dict(p)
        key = item.get("api_key", "") or ""
        if key:
            if len(key) > 12:
                item["api_key_masked"] = f"{key[:4]}****{key[-4:]}"
            else:
                item["api_key_masked"] = "*" * len(key)
            item["has_api_key"] = True
            item["api_key"] = ""  # 不回传明文
        else:
            item["api_key_masked"] = ""
            item["has_api_key"] = False
        masked["providers"].append(item)
    return masked


def save_ai_config(new_cfg):
    global _ai_config_cache
    with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, ensure_ascii=False, indent=2)
    _ai_config_cache = None
    print("✅ AI 配置已保存到 ai_config.json", file=sys.stderr)


def get_active_ai_provider():
    """返回当前激活的 provider（含明文 api_key），没有则 None"""
    cfg = _load_ai_config()
    providers = cfg.get("providers") or []
    if not providers:
        return None
    active_id = cfg.get("active_id")
    for p in providers:
        if p.get("id") == active_id:
            return p
    return providers[0]


def add_ai_provider(provider):
    import uuid

    cfg = _load_ai_config()
    if not provider.get("id"):
        provider["id"] = f"ai-{uuid.uuid4().hex[:8]}"
    cfg["providers"].append(provider)
    if not cfg.get("active_id"):
        cfg["active_id"] = provider["id"]
    save_ai_config(cfg)
    return cfg


def update_ai_provider(provider_id, updates):
    cfg = _load_ai_config()
    found = False
    for p in cfg["providers"]:
        if p.get("id") == provider_id:
            # api_key 为空字符串或 None 表示不修改
            if "api_key" in updates and not updates["api_key"]:
                updates = {k: v for k, v in updates.items() if k != "api_key"}
            p.update(updates)
            found = True
            break
    if not found:
        raise ValueError("Provider 不存在")
    save_ai_config(cfg)
    return cfg


def delete_ai_provider(provider_id):
    cfg = _load_ai_config()
    before = len(cfg["providers"])
    cfg["providers"] = [p for p in cfg["providers"] if p.get("id") != provider_id]
    if len(cfg["providers"]) == before:
        raise ValueError("Provider 不存在")
    if cfg.get("active_id") == provider_id:
        cfg["active_id"] = cfg["providers"][0]["id"] if cfg["providers"] else None
    save_ai_config(cfg)
    return cfg


def set_active_ai_provider(provider_id):
    cfg = _load_ai_config()
    if not any(p.get("id") == provider_id for p in cfg["providers"]):
        raise ValueError("Provider 不存在")
    cfg["active_id"] = provider_id
    save_ai_config(cfg)
    return cfg


def load_questions():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM paper_info ORDER BY id LIMIT 1")
            paper = cursor.fetchone()
            if not paper:
                return [], {"title": "无试卷", "total_questions": 0}
            # 加载所有题目（含 paper_id）
            cursor.execute("SELECT * FROM questions")
            rows = cursor.fetchall()
            questions = []
            for row in rows:
                q = {
                    "id": row["id"],
                    "paper_id": row["paper_id"],
                    "type": row["type"],
                    "content": row["content"],
                    "options": json.loads(row["options"]) if row["options"] else [],
                    "answer": json.loads(row["answer"]) if row["answer"] else None,
                    "explanation": row["explanation"] or "",
                    "steps": json.loads(row["steps"]) if row["steps"] else [],
                }
                questions.append(q)
            questions.sort(key=lambda q: TYPE_ORDER.get(q.get("type", ""), 99))
            paper_info = {
                "title": paper["title"],
                "total_questions": paper["total_questions"],
                "instructions": paper["instructions"] or "",
                "question_types": (
                    json.loads(paper["question_types"])
                    if paper["question_types"]
                    else []
                ),
            }
            return questions, paper_info
    finally:
        conn.close()


def load_user_settings():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM user_settings WHERE user_id = 1")
            row = cursor.fetchone()
            if not row:
                return {
                    "current_pos": 0,
                    "filter_wrong": False,
                    "random_order": False,
                    "practice_limit": 20,
                    "paper_id": None,
                    "progress": {},
                    "progress_timestamp": {},
                }
            return {
                "current_pos": row["current_pos"],
                "filter_wrong": row["filter_wrong"],
                "random_order": row["random_order"],
                "practice_limit": row.get("practice_limit", 20),
                "paper_id": row.get("paper_id"),
                "progress": json.loads(row["progress"]) if row.get("progress") else {},
                "progress_timestamp": (
                    json.loads(row["progress_timestamp"])
                    if row.get("progress_timestamp")
                    else {}
                ),
            }
    finally:
        conn.close()


def save_user_settings(settings):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 是否要更新 progress_timestamp
            update_ts = (
                "progress_timestamp" in settings
                and settings["progress_timestamp"] is not None
            )

            if update_ts:
                cursor.execute(
                    """
                    INSERT INTO user_settings 
                        (user_id, current_pos, filter_wrong, random_order, 
                         practice_limit, paper_id, progress, progress_timestamp)
                    VALUES (1, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        current_pos=VALUES(current_pos),
                        filter_wrong=VALUES(filter_wrong),
                        random_order=VALUES(random_order),
                        practice_limit=VALUES(practice_limit),
                        paper_id=VALUES(paper_id),
                        progress=VALUES(progress),
                        progress_timestamp=VALUES(progress_timestamp)
                    """,
                    (
                        settings.get("current_pos", 0),
                        settings.get("filter_wrong", False),
                        settings.get("random_order", False),
                        settings.get("practice_limit", 20),
                        settings.get("paper_id"),
                        json.dumps(settings.get("progress", {})),
                        json.dumps(settings.get("progress_timestamp", {})),
                    ),
                )
            else:
                # 不更新 progress_timestamp，保留数据库中的原值
                cursor.execute(
                    """
                    INSERT INTO user_settings 
                        (user_id, current_pos, filter_wrong, random_order, 
                         practice_limit, paper_id, progress)
                    VALUES (1, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        current_pos=VALUES(current_pos),
                        filter_wrong=VALUES(filter_wrong),
                        random_order=VALUES(random_order),
                        practice_limit=VALUES(practice_limit),
                        paper_id=VALUES(paper_id),
                        progress=VALUES(progress)
                    """,
                    (
                        settings.get("current_pos", 0),
                        settings.get("filter_wrong", False),
                        settings.get("random_order", False),
                        settings.get("practice_limit", 20),
                        settings.get("paper_id"),
                        json.dumps(settings.get("progress", {})),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def delete_question(qid):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM questions WHERE id = %s", (qid,))
        conn.commit()
    finally:
        conn.close()


def update_question(qid, data, threshold=0.85):
    """更新题目，先排除自身后做相似度检查
    返回 (success, error_message, existing_id)
    """
    content = data["content"]
    # 获取该题所属试卷
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT paper_id FROM questions WHERE id = %s", (qid,))
            row = cursor.fetchone()
            if not row:
                return False, "题目不存在", None
            paper_id = row["paper_id"]
    finally:
        conn.close()

    # 相似度检查（排除自身）
    similar = find_similar_question(
        content, paper_id=paper_id, exclude_id=qid, threshold=threshold
    )
    if similar is not None:
        return (
            False,
            f"与已有题目 #{similar[0]} 高度相似（{similar[2]*100:.1f}%）",
            similar[0],
        )

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE questions SET
                    type=%s, content=%s, options=%s, answer=%s,
                    explanation=%s, steps=%s
                   WHERE id=%s""",
                (
                    data["type"],
                    content,
                    json.dumps(data.get("options", [])),
                    json.dumps(data["answer"]),
                    data.get("explanation", ""),
                    json.dumps(data.get("steps", [])),
                    qid,
                ),
            )
        conn.commit()
        return True, None, None
    finally:
        conn.close()


def import_from_json_data(data, paper_id=None, threshold=0.85):
    """追加导入，使用 jieba + Jaccard 相似度去重（默认阈值 0.85）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 获取或创建 paper_id
            if paper_id is None:
                cursor.execute("SELECT id FROM paper_info ORDER BY id LIMIT 1")
                paper_row = cursor.fetchone()
                if paper_row is None:
                    paper_info = data["paper_info"]
                    cursor.execute(
                        """INSERT INTO paper_info (title, total_questions, instructions, question_types)
                           VALUES (%s, %s, %s, %s)""",
                        (
                            paper_info["title"],
                            paper_info["total_questions"],
                            paper_info.get("instructions", ""),
                            json.dumps(paper_info.get("question_types", [])),
                        ),
                    )
                    paper_id = cursor.lastrowid
                else:
                    paper_id = paper_row["id"]

            # 预加载该试卷下已有题目的分词集合
            cursor.execute(
                "SELECT id, content FROM questions WHERE paper_id = %s",
                (paper_id,),
            )
            existing_rows = cursor.fetchall()
            existing_sets = []
            for row in existing_rows:
                tokens = _tokenize(row["content"])
                if tokens:
                    existing_sets.append((row["id"], tokens))

            added = 0
            skipped = 0
            added_sets = []  # 本次导入中已添加的，防止内部重复

            for q in data["questions"]:
                content = q["content"]
                new_set = _tokenize(content)

                if not new_set:
                    # 分词后无有效词，退回直接添加
                    is_dup = False
                else:
                    is_dup = False
                    # 1. 与数据库中已有题目对比
                    for _, old_set in existing_sets:
                        len_ratio = min(len(new_set), len(old_set)) / max(
                            len(new_set), len(old_set)
                        )
                        if len_ratio < 0.5:
                            continue
                        if jaccard_similarity(new_set, old_set) >= threshold:
                            is_dup = True
                            break
                    # 2. 与本次导入中已添加的对比
                    if not is_dup:
                        for old_set in added_sets:
                            len_ratio = min(len(new_set), len(old_set)) / max(
                                len(new_set), len(old_set)
                            )
                            if len_ratio < 0.5:
                                continue
                            if jaccard_similarity(new_set, old_set) >= threshold:
                                is_dup = True
                                break

                if is_dup:
                    skipped += 1
                    continue

                cursor.execute(
                    """INSERT INTO questions
                       (type, content, options, answer, explanation, steps, paper_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        q["type"],
                        content,
                        json.dumps(q.get("options", [])),
                        json.dumps(q["answer"]),
                        q.get("explanation", ""),
                        json.dumps(q.get("steps", [])),
                        paper_id,
                    ),
                )
                qid = cursor.lastrowid
                added += 1

                # 知识点处理
                knowledge_names = q.get("knowledge", [])
                if knowledge_names:
                    for kname in knowledge_names:
                        kname = kname.strip()
                        if not kname:
                            continue
                        cursor.execute(
                            "SELECT id FROM knowledge_points WHERE name = %s", (kname,)
                        )
                        row = cursor.fetchone()
                        if row:
                            kid = row["id"]
                        else:
                            cursor.execute(
                                "INSERT INTO knowledge_points (name) VALUES (%s)",
                                (kname,),
                            )
                            kid = cursor.lastrowid
                        cursor.execute(
                            "INSERT INTO question_knowledge (question_id, knowledge_id) VALUES (%s, %s)",
                            (qid, kid),
                        )

                if new_set:
                    added_sets.append(new_set)

            conn.commit()
            return added, skipped
    finally:
        conn.close()


def get_questions_page(
    search=None,
    page=1,
    per_page=20,
    wrong_only=False,
    qtype=None,
    unanswered_only=False,
    paper_id=None,
):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 获取 progress 和 wrong_ids
            cursor.execute("SELECT progress FROM user_settings WHERE user_id = 1")
            row = cursor.fetchone()
            progress = json.loads(row["progress"]) if row and row["progress"] else {}
            wrong_ids = set(get_wrong_question_ids(1))

            # 构建查询条件（原逻辑）
            sql = "SELECT * FROM questions"
            params = []
            conditions = []
            if paper_id is not None:
                conditions.append("paper_id = %s")
                params.append(paper_id)
            if search:
                conditions.append("(content LIKE %s OR id LIKE %s)")
                params.extend([f"%{search}%", f"%{search}%"])

            if wrong_only:
                wrong_ids_filter = set(get_wrong_question_ids(1))
                if not wrong_ids_filter:
                    return [], 0
                placeholders = ",".join(["%s"] * len(wrong_ids_filter))
                conditions.append(f"id IN ({placeholders})")
                params.extend(list(wrong_ids_filter))

            if qtype:
                conditions.append("type = %s")
                params.append(qtype)

            if unanswered_only:
                if progress:
                    answered_ids = list(progress.keys())
                    placeholders = ",".join(["%s"] * len(answered_ids))
                    conditions.append(f"id NOT IN ({placeholders})")
                    params.extend(answered_ids)

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            # 计数
            count_sql = "SELECT COUNT(*) as total FROM questions"
            if conditions:
                count_sql += " WHERE " + " AND ".join(conditions)
            count_params = params[:]
            cursor.execute(count_sql, count_params)
            total = cursor.fetchone()["total"]

            sql += " ORDER BY id LIMIT %s OFFSET %s"
            params.extend([per_page, (page - 1) * per_page])
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            questions = []
            for row in rows:
                qid = row["id"]
                q = {
                    "id": qid,
                    "type": row["type"],
                    "content": row["content"],
                    "options": json.loads(row["options"]) if row["options"] else [],
                    "answer": json.loads(row["answer"]) if row["answer"] else None,
                    "explanation": row["explanation"] or "",
                    "steps": json.loads(row["steps"]) if row["steps"] else [],
                    "status": determine_status(qid, progress, wrong_ids),
                }
                q["knowledge"] = get_question_knowledge(row["id"])
                questions.append(q)
            return questions, total
    finally:
        conn.close()


def create_question_in_db(data, threshold=0.85):
    """插入新题目，先做相似度去重
    返回 (qid, is_duplicate, existing_id, similarity)
    - 若插入成功：is_duplicate=False, qid=新ID
    - 若检测到相似：is_duplicate=True, qid=None, existing_id=相似题ID
    """
    content = data["content"]
    paper_id = data.get("paper_id", 1)

    # 相似度检查
    similar = find_similar_question(content, paper_id=paper_id, threshold=threshold)
    if similar is not None:
        return None, True, similar[0], similar[2]

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO questions
                   (type, content, options, answer, explanation, steps, paper_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    data["type"],
                    content,
                    json.dumps(data.get("options", [])),
                    json.dumps(data["answer"]),
                    data.get("explanation", ""),
                    json.dumps(data.get("steps", [])),
                    paper_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid, False, None, 0.0
    finally:
        conn.close()


def batch_delete_questions(ids):
    if not ids:
        return
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(f"DELETE FROM questions WHERE id IN ({placeholders})", ids)
            conn.commit()
    finally:
        conn.close()


def add_wrong_question(user_id, question_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO wrong_questions (user_id, question_id, wrong_count)
                   VALUES (%s, %s, 1)
                   ON DUPLICATE KEY UPDATE wrong_count = wrong_count + 1, last_wrong_time = CURRENT_TIMESTAMP""",
                (user_id, question_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_wrong_question_ids(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT question_id FROM wrong_questions WHERE user_id = %s", (user_id,)
            )
            rows = cursor.fetchall()
            return [row["question_id"] for row in rows]
    finally:
        conn.close()


def get_stats_data(paper_id=None):
    """统计：总题数、错题数、各题型错题数（可按试卷过滤）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 总题数
            if paper_id is not None:
                cursor.execute(
                    "SELECT COUNT(*) as total FROM questions WHERE paper_id = %s",
                    (paper_id,),
                )
            else:
                cursor.execute("SELECT COUNT(*) as total FROM questions")
            total_q = cursor.fetchone()["total"]

            # 错题总数
            if paper_id is not None:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT w.question_id) as total 
                    FROM wrong_questions w
                    JOIN questions q ON w.question_id = q.id
                    WHERE w.user_id = 1 AND q.paper_id = %s
                """,
                    (paper_id,),
                )
            else:
                cursor.execute(
                    "SELECT COUNT(DISTINCT question_id) as total FROM wrong_questions WHERE user_id = 1"
                )
            wrong_total = cursor.fetchone()["total"]

            # 各题型错题数
            if paper_id is not None:
                cursor.execute(
                    """
                    SELECT q.type, COUNT(w.question_id) as wrong_count
                    FROM wrong_questions w
                    JOIN questions q ON w.question_id = q.id
                    WHERE w.user_id = 1 AND q.paper_id = %s
                    GROUP BY q.type
                """,
                    (paper_id,),
                )
            else:
                cursor.execute("""
                    SELECT q.type, COUNT(w.question_id) as wrong_count
                    FROM wrong_questions w
                    JOIN questions q ON w.question_id = q.id
                    WHERE w.user_id = 1
                    GROUP BY q.type
                """)
            type_stats = cursor.fetchall()

            return {
                "total_questions": total_q,
                "wrong_total": wrong_total,
                "type_stats": type_stats,
            }
    finally:
        conn.close()


def get_recent_wrong_questions(user_id, limit=10, paper_id=None):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT q.id, q.type, q.content, q.options, q.answer, q.explanation, q.steps,
                       w.wrong_count, w.last_wrong_time
                FROM wrong_questions w
                JOIN questions q ON w.question_id = q.id
                WHERE w.user_id = %s
            """
            params = [user_id]
            if paper_id is not None:
                sql += " AND q.paper_id = %s"
                params.append(paper_id)
            sql += " ORDER BY w.last_wrong_time DESC LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            questions = []
            for row in rows:
                q = {
                    "id": row["id"],
                    "type": row["type"],
                    "content": row["content"],
                    "options": json.loads(row["options"]) if row["options"] else [],
                    "answer": json.loads(row["answer"]) if row["answer"] else None,
                    "explanation": row["explanation"] or "",
                    "steps": json.loads(row["steps"]) if row["steps"] else [],
                    "wrong_count": row["wrong_count"],
                    "last_wrong_time": (
                        row["last_wrong_time"].strftime("%Y-%m-%d %H:%M:%S")
                        if row["last_wrong_time"]
                        else None
                    ),
                }
                questions.append(q)
            return questions
    finally:
        conn.close()


def remove_wrong_question(user_id, question_id):
    """删除错题记录（当回答正确时）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM wrong_questions WHERE user_id = %s AND question_id = %s",
                (user_id, question_id),
            )
        conn.commit()
    finally:
        conn.close()


def determine_status(qid, progress, wrong_ids):
    """根据进度和错题表判断状态"""
    qid_str = str(qid)
    if qid_str in progress and progress[qid_str]:
        # 已作答
        if qid in wrong_ids:
            return "错误"
        else:
            return "正确"
    else:
        return "未作答"


def get_wrong_report_data(user_id, paper_id=None):
    """获取错题详细信息（可按试卷过滤）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT q.id, q.type, q.content, q.explanation,
                       w.wrong_count, w.last_wrong_time
                FROM wrong_questions w
                JOIN questions q ON w.question_id = q.id
                WHERE w.user_id = %s
            """
            params = [user_id]
            if paper_id is not None:
                sql += " AND q.paper_id = %s"
                params.append(paper_id)
            sql += " ORDER BY w.last_wrong_time DESC"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            questions = []
            for row in rows:
                questions.append(
                    {
                        "id": row["id"],
                        "type": row["type"],
                        "content": row["content"],
                        "explanation": row["explanation"] or "暂无解析",
                        "wrong_count": row["wrong_count"],
                        "last_wrong_time": (
                            row["last_wrong_time"].strftime("%Y-%m-%d %H:%M")
                            if row["last_wrong_time"]
                            else None
                        ),
                    }
                )
            return questions
    finally:
        conn.close()


def reset_all_ids():
    """
    重置所有题目的 ID 为从 1 开始连续编号，并同步更新 progress、progress_timestamp、wrong_questions 和 question_knowledge 表。
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 获取当前所有题目（按 ID 升序）
            cursor.execute("SELECT * FROM questions ORDER BY id")
            rows = cursor.fetchall()
            if not rows:
                cursor.execute("ALTER TABLE questions AUTO_INCREMENT = 1")
                conn.commit()
                return

            # 2. 构建旧ID到新ID的映射
            old_to_new = {}
            new_id = 1
            for row in rows:
                old_to_new[row["id"]] = new_id
                new_id += 1

            # 3. 备份所有题目的知识点关联（旧ID -> knowledge_ids）
            question_knowledge_map = {}
            for row in rows:
                old_qid = row["id"]
                cursor.execute(
                    "SELECT knowledge_id FROM question_knowledge WHERE question_id = %s",
                    (old_qid,),
                )
                kps = cursor.fetchall()
                question_knowledge_map[old_qid] = [kp["knowledge_id"] for kp in kps]

            # 4. 禁用外键检查（关键）
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            # 5. 清空 question_knowledge（安全）
            cursor.execute("DELETE FROM question_knowledge")

            # 6. 更新 user_settings.progress 和 progress_timestamp
            cursor.execute(
                "SELECT progress, progress_timestamp FROM user_settings WHERE user_id = 1"
            )
            row = cursor.fetchone()
            if row:
                progress = json.loads(row["progress"]) if row["progress"] else {}
                new_progress = {}
                for old_qid, answered in progress.items():
                    old_qid_int = int(old_qid)
                    if old_qid_int in old_to_new:
                        new_progress[str(old_to_new[old_qid_int])] = answered
                cursor.execute(
                    "UPDATE user_settings SET progress = %s WHERE user_id = 1",
                    (json.dumps(new_progress),),
                )
                timestamp = (
                    json.loads(row["progress_timestamp"])
                    if row["progress_timestamp"]
                    else {}
                )
                new_timestamp = {}
                for old_qid, ts in timestamp.items():
                    old_qid_int = int(old_qid)
                    if old_qid_int in old_to_new:
                        new_timestamp[str(old_to_new[old_qid_int])] = ts
                cursor.execute(
                    "UPDATE user_settings SET progress_timestamp = %s WHERE user_id = 1",
                    (json.dumps(new_timestamp),),
                )

            # 7. 更新 wrong_questions
            cursor.execute(
                "SELECT id, question_id FROM wrong_questions WHERE user_id = 1"
            )
            wrong_rows = cursor.fetchall()
            if wrong_rows:
                for w in wrong_rows:
                    old_qid = w["question_id"]
                    if old_qid in old_to_new:
                        cursor.execute(
                            "UPDATE wrong_questions SET question_id = %s WHERE id = %s",
                            (old_to_new[old_qid], w["id"]),
                        )

            # 8. 删除并重建 questions 表（此时外键检查已禁用）
            cursor.execute("DROP TABLE questions")
            cursor.execute("""
                CREATE TABLE questions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    type VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    options JSON,
                    answer JSON NOT NULL,
                    explanation TEXT,
                    steps JSON,
                    paper_id INT,
                    FOREIGN KEY (paper_id) REFERENCES paper_info(id) ON DELETE CASCADE
                )
            """)
            # 插入新数据
            for old_row, new_id in zip(rows, range(1, len(rows) + 1)):
                cursor.execute(
                    """INSERT INTO questions
                       (id, type, content, options, answer, explanation, steps, paper_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        new_id,
                        old_row["type"],
                        old_row["content"],
                        old_row["options"],
                        old_row["answer"],
                        old_row["explanation"],
                        old_row["steps"],
                        old_row["paper_id"],
                    ),
                )

            # 9. 重新插入 question_knowledge 关联（使用新ID）
            for old_qid, knowledge_ids in question_knowledge_map.items():
                if knowledge_ids:
                    new_qid = old_to_new[old_qid]
                    for kid in knowledge_ids:
                        cursor.execute(
                            "INSERT INTO question_knowledge (question_id, knowledge_id) VALUES (%s, %s)",
                            (new_qid, kid),
                        )

            # 10. 更新 paper_info.total_questions
            cursor.execute("UPDATE paper_info SET total_questions = %s", (len(rows),))
            cursor.execute(
                "ALTER TABLE questions AUTO_INCREMENT = %s", (len(rows) + 1,)
            )

            # 11. 恢复外键检查
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            conn.commit()
            print(
                f"✅ ID 重置成功，共 {len(rows)} 道题，新 ID 为 1~{len(rows)}",
                file=sys.stderr,
            )
    except Exception as e:
        conn.rollback()
        print(f"❌ 重置 ID 失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


def update_progress_timestamp(question_id):
    """记录题目的最后作答时间（独立于 save_progress）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT progress_timestamp FROM user_settings WHERE user_id = 1"
            )
            row = cursor.fetchone()
            ts = {}
            if row and row["progress_timestamp"]:
                try:
                    ts = (
                        json.loads(row["progress_timestamp"])
                        if isinstance(row["progress_timestamp"], str)
                        else row["progress_timestamp"]
                    )
                except Exception:
                    ts = {}
            ts[str(question_id)] = datetime.now().isoformat()
            cursor.execute(
                "UPDATE user_settings SET progress_timestamp = %s WHERE user_id = 1",
                (json.dumps(ts),),
            )
        conn.commit()
    finally:
        conn.close()


def clean_old_progress():
    """使用数据库中存储的天数执行清理"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT clean_days FROM user_settings WHERE user_id = 1")
            row = cursor.fetchone()
            days = row["clean_days"] if row and row.get("clean_days") is not None else 7
    except:
        days = 7
    clean_old_progress_with_days(days)


def clean_old_progress_with_days(days):
    """清理超过指定天数的已作答记录"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT progress, progress_timestamp FROM user_settings WHERE user_id = 1"
            )
            row = cursor.fetchone()
            if not row or not row["progress_timestamp"]:
                return

            progress = json.loads(row["progress"]) if row["progress"] else {}
            ts = (
                json.loads(row["progress_timestamp"])
                if row["progress_timestamp"]
                else {}
            )

            now = datetime.now()
            cutoff = now - timedelta(days=days)
            removed = 0

            to_remove = []
            for qid_str, timestamp_str in ts.items():
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                    if dt < cutoff:
                        to_remove.append(qid_str)
                except:
                    to_remove.append(qid_str)

            if not to_remove:
                return

            for qid in to_remove:
                progress.pop(qid, None)
                ts.pop(qid, None)
                removed += 1

            cursor.execute(
                "UPDATE user_settings SET progress = %s, progress_timestamp = %s WHERE user_id = 1",
                (json.dumps(progress), json.dumps(ts)),
            )
            conn.commit()
            print(
                f"✅ 清理完成，移除了 {removed} 条过期记录（超过 {days} 天）",
                file=sys.stderr,
            )
    except Exception as e:
        conn.rollback()
        print(f"❌ 清理进度失败: {e}", file=sys.stderr)
    finally:
        conn.close()


def get_all_papers():
    """获取所有试卷，并实时统计每个试卷的题目数"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.title, p.created_at,
                       (SELECT COUNT(*) FROM questions q WHERE q.paper_id = p.id) AS total_questions
                FROM paper_info p
                ORDER BY p.id
            """)
            return cursor.fetchall()
    finally:
        conn.close()


def create_paper_db(title):
    """创建试卷"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO paper_info (title) VALUES (%s)", (title,))
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()


def update_paper(paper_id, title):
    """更新试卷"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE paper_info SET title = %s WHERE id = %s", (title, paper_id)
            )
            conn.commit()
    finally:
        conn.close()


def delete_paper(paper_id):
    """删除试卷（级联删除题目）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM paper_info WHERE id = %s", (paper_id,))
            conn.commit()
    finally:
        conn.close()


def get_knowledge_graph_data(user_id=1, paper_id=None):
    """获取知识图谱数据（可按试卷过滤）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 获取知识点（仅统计该试卷下的题目）
            cursor.execute("SELECT id, name FROM knowledge_points")
            kps = cursor.fetchall()
            nodes = []
            for kp in kps:
                if paper_id is not None:
                    cursor.execute(
                        """
                        SELECT COUNT(*) as cnt FROM question_knowledge qk
                        JOIN questions q ON qk.question_id = q.id
                        WHERE qk.knowledge_id = %s AND q.paper_id = %s
                    """,
                        (kp["id"], paper_id),
                    )
                    cnt = cursor.fetchone()["cnt"]

                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT qk.question_id) as wrong_cnt
                        FROM question_knowledge qk
                        JOIN questions q ON qk.question_id = q.id
                        JOIN wrong_questions w ON w.question_id = qk.question_id AND w.user_id = %s
                        WHERE qk.knowledge_id = %s AND q.paper_id = %s
                    """,
                        (user_id, kp["id"], paper_id),
                    )
                    wrong = cursor.fetchone()["wrong_cnt"] or 0

                    cursor.execute(
                        """
                        SELECT qk.question_id FROM question_knowledge qk
                        JOIN questions q ON qk.question_id = q.id
                        WHERE qk.knowledge_id = %s AND q.paper_id = %s
                    """,
                        (kp["id"], paper_id),
                    )
                    qids = [row["question_id"] for row in cursor.fetchall()]
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as cnt FROM question_knowledge WHERE knowledge_id = %s",
                        (kp["id"],),
                    )
                    cnt = cursor.fetchone()["cnt"]

                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT qk.question_id) as wrong_cnt
                        FROM question_knowledge qk
                        JOIN wrong_questions w ON w.question_id = qk.question_id AND w.user_id = %s
                        WHERE qk.knowledge_id = %s
                    """,
                        (user_id, kp["id"]),
                    )
                    wrong = cursor.fetchone()["wrong_cnt"] or 0

                    cursor.execute(
                        "SELECT question_id FROM question_knowledge WHERE knowledge_id = %s",
                        (kp["id"],),
                    )
                    qids = [row["question_id"] for row in cursor.fetchall()]

                # 仅保留有题目的知识点
                if cnt > 0:
                    nodes.append(
                        {
                            "id": kp["id"],
                            "name": kp["name"],
                            "value": cnt,
                            "wrong": wrong,
                            "question_ids": qids,
                        }
                    )

            # 计算边（共现关系，仅在该试卷内）
            edges = []
            if paper_id is not None:
                cursor.execute(
                    """
                    SELECT qk1.knowledge_id as k1, qk2.knowledge_id as k2, COUNT(*) as weight
                    FROM question_knowledge qk1
                    JOIN question_knowledge qk2 
                        ON qk1.question_id = qk2.question_id 
                        AND qk1.knowledge_id < qk2.knowledge_id
                    JOIN questions q ON qk1.question_id = q.id
                    WHERE q.paper_id = %s
                    GROUP BY k1, k2
                    ORDER BY weight DESC
                """,
                    (paper_id,),
                )
            else:
                cursor.execute("""
                    SELECT qk1.knowledge_id as k1, qk2.knowledge_id as k2, COUNT(*) as weight
                    FROM question_knowledge qk1
                    JOIN question_knowledge qk2 
                        ON qk1.question_id = qk2.question_id 
                        AND qk1.knowledge_id < qk2.knowledge_id
                    GROUP BY k1, k2
                    ORDER BY weight DESC
                """)
            edge_rows = cursor.fetchall()
            for row in edge_rows:
                edges.append(
                    {"source": row["k1"], "target": row["k2"], "weight": row["weight"]}
                )

            return {"nodes": nodes, "edges": edges}
    finally:
        conn.close()


def get_all_knowledge_points():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description FROM knowledge_points ORDER BY name"
            )
            return cursor.fetchall()
    finally:
        conn.close()


def create_knowledge_point(name, description=""):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO knowledge_points (name, description) VALUES (%s, %s)",
                (name, description),
            )
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()


def update_knowledge_point(kp_id, name, description):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE knowledge_points SET name=%s, description=%s WHERE id=%s",
                (name, description, kp_id),
            )
            conn.commit()
    finally:
        conn.close()


def delete_knowledge_point(kp_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM knowledge_points WHERE id=%s", (kp_id,))
            conn.commit()
    finally:
        conn.close()


def get_question_knowledge(question_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT k.id, k.name 
                FROM knowledge_points k
                JOIN question_knowledge qk ON k.id = qk.knowledge_id
                WHERE qk.question_id = %s
            """,
                (question_id,),
            )
            return cursor.fetchall()
    finally:
        conn.close()


def set_question_knowledge(question_id, knowledge_ids):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 删除旧关联
            cursor.execute(
                "DELETE FROM question_knowledge WHERE question_id = %s", (question_id,)
            )
            # 插入新关联
            for kid in knowledge_ids:
                cursor.execute(
                    "INSERT INTO question_knowledge (question_id, knowledge_id) VALUES (%s, %s)",
                    (question_id, kid),
                )
            conn.commit()
    finally:
        conn.close()


def get_daily_stats(user_id, year=None, month=None, paper_id=None):
    """获取指定月份的每日做题数据（做题数、错题数、正确率，可按试卷过滤）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT progress_timestamp FROM user_settings WHERE user_id = %s",
                (user_id,),
            )
            row = cursor.fetchone()
            if not row or not row["progress_timestamp"]:
                return {}
            ts = json.loads(row["progress_timestamp"])
            if not ts:
                return {}

            # 当前错题ID集合（可按试卷过滤）
            if paper_id is not None:
                cursor.execute(
                    """
                    SELECT w.question_id FROM wrong_questions w
                    JOIN questions q ON w.question_id = q.id
                    WHERE w.user_id = %s AND q.paper_id = %s
                """,
                    (user_id, paper_id),
                )
            else:
                cursor.execute(
                    "SELECT question_id FROM wrong_questions WHERE user_id = %s",
                    (user_id,),
                )
            wrong_ids = {r["question_id"] for r in cursor.fetchall()}

            # 该试卷下的所有题目ID（用于过滤 progress_timestamp）
            if paper_id is not None:
                cursor.execute(
                    "SELECT id FROM questions WHERE paper_id = %s",
                    (paper_id,),
                )
                valid_ids = {r["id"] for r in cursor.fetchall()}
            else:
                valid_ids = None  # 不限制

            if year is None or month is None:
                now = datetime.now()
                year = now.year
                month = now.month

            daily_stats = {}
            for qid_str, timestamp_str in ts.items():
                try:
                    qid = int(qid_str)
                    # 若指定试卷，仅统计属于该试卷的题目
                    if valid_ids is not None and qid not in valid_ids:
                        continue
                    dt = datetime.fromisoformat(timestamp_str)
                    if dt.year == year and dt.month == month:
                        key = dt.strftime("%Y-%m-%d")
                        if key not in daily_stats:
                            daily_stats[key] = {"total": 0, "wrong": 0, "correct": 0}
                        daily_stats[key]["total"] += 1
                        if qid in wrong_ids:
                            daily_stats[key]["wrong"] += 1
                        else:
                            daily_stats[key]["correct"] += 1
                except Exception:
                    continue

            # 计算正确率
            for stat in daily_stats.values():
                if stat["total"] > 0:
                    stat["accuracy"] = round(stat["correct"] / stat["total"] * 100, 1)
                else:
                    stat["accuracy"] = 0

            return daily_stats
    finally:
        conn.close()


def start_graph_walk(knowledge_id, user_id=1):
    """从某知识点开始漫游"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO graph_walks (user_id, knowledge_id, path, status)
                VALUES (%s, %s, %s, 'active')
            """,
                (user_id, knowledge_id, json.dumps([knowledge_id])),
            )
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()


def get_related_knowledge(knowledge_id, paper_id=None, limit=10):
    """获取与指定知识点相关（共现）的其他知识点"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            if paper_id is not None:
                cursor.execute(
                    """
                    SELECT DISTINCT k.id, k.name, COUNT(*) as weight
                    FROM question_knowledge qk1
                    JOIN question_knowledge qk2 ON qk1.question_id = qk2.question_id
                    JOIN knowledge_points k ON k.id = qk2.knowledge_id
                    JOIN questions q ON qk1.question_id = q.id
                    WHERE qk1.knowledge_id = %s AND qk2.knowledge_id != %s AND q.paper_id = %s
                    GROUP BY k.id, k.name
                    ORDER BY weight DESC
                    LIMIT %s
                """,
                    (knowledge_id, knowledge_id, paper_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT DISTINCT k.id, k.name, COUNT(*) as weight
                    FROM question_knowledge qk1
                    JOIN question_knowledge qk2 ON qk1.question_id = qk2.question_id
                    JOIN knowledge_points k ON k.id = qk2.knowledge_id
                    WHERE qk1.knowledge_id = %s AND qk2.knowledge_id != %s
                    GROUP BY k.id, k.name
                    ORDER BY weight DESC
                    LIMIT %s
                """,
                    (knowledge_id, knowledge_id, limit),
                )
            return cursor.fetchall()
    finally:
        conn.close()


def jaccard_similarity(set1: set, set2: set) -> float:
    """计算两个集合的 Jaccard 相似度"""
    if not set1 or not set2:
        return 0.0
    intersection = set1 & set2
    union = set1 | set2
    if not union:
        return 0.0
    return len(intersection) / len(union)


def is_similar_question(content1: str, content2: str, threshold: float = 0.85) -> bool:
    """判断两个题目是否相似（基于 jieba 分词 + Jaccard）"""
    s1 = _tokenize(content1)
    s2 = _tokenize(content2)
    if not s1 or not s2:
        return False
    # 长度差过大直接判不相似（性能优化）
    len_ratio = min(len(s1), len(s2)) / max(len(s1), len(s2))
    if len_ratio < 0.5:
        return False
    return jaccard_similarity(s1, s2) >= threshold


def find_similar_question(
    content: str, paper_id=None, exclude_id=None, threshold: float = 0.85
):
    """在指定试卷（或全部）中查找与给定内容相似的题目
    返回：(existing_id, existing_content, similarity) 或 None
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, content FROM questions"
            params = []
            conditions = []
            if paper_id is not None:
                conditions.append("paper_id = %s")
                params.append(paper_id)
            if exclude_id is not None:
                conditions.append("id != %s")
                params.append(exclude_id)
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            new_set = _tokenize(content)
            if not new_set:
                return None

            best = None
            for row in rows:
                old_set = _tokenize(row["content"])
                if not old_set:
                    continue
                len_ratio = min(len(new_set), len(old_set)) / max(
                    len(new_set), len(old_set)
                )
                if len_ratio < 0.5:
                    continue
                sim = jaccard_similarity(new_set, old_set)
                if sim >= threshold:
                    if best is None or sim > best[2]:
                        best = (row["id"], row["content"], sim)
            return best
    finally:
        conn.close()


def get_recommended_next(knowledge_id, paper_id=None, limit=5):
    """基于共现次数 + 错题数 + 错题率，推荐下一站知识点。

    score = cooccur * 1.0 + wrong_count * 2.0 + wrong_rate * 5.0
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 找出与当前知识点共现的所有知识点
            if paper_id is not None:
                cursor.execute(
                    """
                    SELECT k.id, k.name,
                           COUNT(DISTINCT qk1.question_id) AS cooccur
                    FROM question_knowledge qk1
                    JOIN question_knowledge qk2
                        ON qk1.question_id = qk2.question_id
                        AND qk2.knowledge_id != qk1.knowledge_id
                    JOIN knowledge_points k ON k.id = qk2.knowledge_id
                    JOIN questions q ON qk1.question_id = q.id
                    WHERE qk1.knowledge_id = %s AND q.paper_id = %s
                    GROUP BY k.id, k.name
                    """,
                    (knowledge_id, paper_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT k.id, k.name,
                           COUNT(DISTINCT qk1.question_id) AS cooccur
                    FROM question_knowledge qk1
                    JOIN question_knowledge qk2
                        ON qk1.question_id = qk2.question_id
                        AND qk2.knowledge_id != qk1.knowledge_id
                    JOIN knowledge_points k ON k.id = qk2.knowledge_id
                    WHERE qk1.knowledge_id = %s
                    GROUP BY k.id, k.name
                    """,
                    (knowledge_id,),
                )
            rows = cursor.fetchall()

            candidates = []
            for row in rows:
                kid = row["id"]
                # 2. 该知识点下的总题数 & 错题数
                if paper_id is not None:
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT qk.question_id) AS total,
                               COUNT(DISTINCT w.question_id) AS wrong
                        FROM question_knowledge qk
                        JOIN questions q ON qk.question_id = q.id
                        LEFT JOIN wrong_questions w
                            ON w.question_id = qk.question_id AND w.user_id = 1
                        WHERE qk.knowledge_id = %s AND q.paper_id = %s
                        """,
                        (kid, paper_id),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT qk.question_id) AS total,
                               COUNT(DISTINCT w.question_id) AS wrong
                        FROM question_knowledge qk
                        LEFT JOIN wrong_questions w
                            ON w.question_id = qk.question_id AND w.user_id = 1
                        WHERE qk.knowledge_id = %s
                        """,
                        (kid,),
                    )
                stats = cursor.fetchone()
                total = stats["total"] or 0
                wrong = stats["wrong"] or 0

                cooccur = row["cooccur"] or 0
                wrong_rate = (wrong / total) if total > 0 else 0.0

                # 3. 综合评分
                score = cooccur * 1.0 + wrong * 2.0 + wrong_rate * 5.0

                # 4. 推荐理由
                reasons = []
                if cooccur > 0:
                    reasons.append(f"共现 {cooccur} 次")
                if wrong > 0:
                    reasons.append(f"错题 {wrong} 道")
                if total > 0 and wrong_rate >= 0.5:
                    reasons.append("掌握度较低")
                if not reasons:
                    reasons.append("相关知识")

                candidates.append(
                    {
                        "id": kid,
                        "name": row["name"],
                        "cooccur": cooccur,
                        "wrong_count": wrong,
                        "total": total,
                        "wrong_rate": round(wrong_rate * 100, 1),
                        "score": round(score, 2),
                        "reason": "，".join(reasons),
                    }
                )

            # 5. 按分数降序取前 N
            candidates.sort(key=lambda x: -x["score"])
            return candidates[:limit]
    finally:
        conn.close()
