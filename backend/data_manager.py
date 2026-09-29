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


def get_db():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        port=MYSQL_PORT,
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
            # 间隔重复卡片表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS srs_cards (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    user_id INT DEFAULT 1,
                    question_id INT NOT NULL,
                    ease_factor FLOAT DEFAULT 2.5,
                    interval_days INT DEFAULT 0,
                    repetitions INT DEFAULT 0,
                    due_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reviewed_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_user_question (user_id, question_id),
                    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
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


def update_question(qid, data):
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
                    data["content"],
                    json.dumps(data.get("options", [])),
                    json.dumps(data["answer"]),
                    data.get("explanation", ""),
                    json.dumps(data.get("steps", [])),
                    qid,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def import_from_json_data(data, paper_id=None):
    """追加导入，去重基于 content+options，ID自动生成，支持知识点关联
    paper_id: 指定导入到哪张试卷；若为 None，则使用第一张试卷或创建默认试卷
    """
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 若未指定 paper_id，则获取第一张试卷或创建
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

            # 以下逻辑不变
            cursor.execute("SELECT content, options FROM questions")
            existing = cursor.fetchall()
            existing_keys = {(row["content"], row["options"]) for row in existing}

            added = 0
            skipped = 0
            for q in data["questions"]:
                key = (q["content"], json.dumps(q.get("options", []), sort_keys=True))
                if key in existing_keys:
                    skipped += 1
                    continue

                cursor.execute(
                    """INSERT INTO questions
                       (type, content, options, answer, explanation, steps, paper_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        q["type"],
                        q["content"],
                        json.dumps(q.get("options", [])),
                        json.dumps(q["answer"]),
                        q.get("explanation", ""),
                        json.dumps(q.get("steps", [])),
                        paper_id,
                    ),
                )
                qid = cursor.lastrowid
                added += 1

                # 知识点处理（不变）
                knowledge_names = q.get("knowledge", [])
                if knowledge_names:
                    knowledge_ids = []
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
                        knowledge_ids.append(kid)
                    if knowledge_ids:
                        for kid in knowledge_ids:
                            cursor.execute(
                                "INSERT INTO question_knowledge (question_id, knowledge_id) VALUES (%s, %s)",
                                (qid, kid),
                            )

                existing_keys.add(key)

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


def create_question_in_db(data):
    """插入新题目，返回自增ID"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            paper_id = data.get("paper_id", 1)
            cursor.execute(
                """INSERT INTO questions
                   (type, content, options, answer, explanation, steps, paper_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    data["type"],
                    data["content"],
                    json.dumps(data.get("options", [])),
                    json.dumps(data["answer"]),
                    data.get("explanation", ""),
                    json.dumps(data.get("steps", [])),
                    paper_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid
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


def add_question_to_srs(question_id, user_id=1):
    """将题目加入间隔重复系统（立即到期）"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT IGNORE INTO srs_cards (user_id, question_id, due_date)
                VALUES (%s, %s, NOW())
            """,
                (user_id, question_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_due_srs_cards(user_id=1, paper_id=None, limit=50):
    """获取今日待复习的题目"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT c.id AS card_id, c.question_id, c.ease_factor, c.interval_days,
                       c.repetitions, c.due_date,
                       q.type, q.content, q.options, q.answer, q.explanation, q.steps, q.paper_id
                FROM srs_cards c
                JOIN questions q ON c.question_id = q.id
                WHERE c.user_id = %s AND c.due_date <= NOW()
            """
            params = [user_id]
            if paper_id is not None:
                sql += " AND q.paper_id = %s"
                params.append(paper_id)
            sql += " ORDER BY c.due_date ASC, c.ease_factor ASC LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            cards = []
            for row in rows:
                cards.append(
                    {
                        "card_id": row["card_id"],
                        "question_id": row["question_id"],
                        "type": row["type"],
                        "content": row["content"],
                        "options": json.loads(row["options"]) if row["options"] else [],
                        "answer": json.loads(row["answer"]) if row["answer"] else None,
                        "explanation": row["explanation"] or "",
                        "steps": json.loads(row["steps"]) if row["steps"] else [],
                        "ease_factor": row["ease_factor"],
                        "interval_days": row["interval_days"],
                        "repetitions": row["repetitions"],
                    }
                )
            return cards
    finally:
        conn.close()


def review_srs_card(card_id, quality, user_id=1):
    """SM-2 算法复习一张卡片"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT ease_factor, interval_days, repetitions FROM srs_cards WHERE id = %s AND user_id = %s",
                (card_id, user_id),
            )
            row = cursor.fetchone()
            if not row:
                return None

            ef = row["ease_factor"]
            interval = row["interval_days"]
            reps = row["repetitions"]

            if quality < 3:
                reps = 0
                interval = 1
            else:
                if reps == 0:
                    interval = 1
                elif reps == 1:
                    interval = 6
                else:
                    interval = round(interval * ef)
                reps += 1

            ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            if ef < 1.3:
                ef = 1.3

            # 用 datetime.now() + timedelta
            due_datetime = datetime.now() + timedelta(days=interval)

            cursor.execute(
                """
                UPDATE srs_cards SET
                    ease_factor = %s,
                    interval_days = %s,
                    repetitions = %s,
                    due_date = %s,
                    last_reviewed_at = NOW()
                WHERE id = %s
            """,
                (ef, interval, reps, due_datetime, card_id),
            )
        conn.commit()
        return {
            "ease_factor": ef,
            "interval_days": interval,
            "repetitions": reps,
            "due_date": due_datetime.isoformat(),
        }
    finally:
        conn.close()


def get_srs_stats(user_id=1, paper_id=None):
    """SRS 复习统计"""
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            base_sql = """
                FROM srs_cards c
                JOIN questions q ON c.question_id = q.id
                WHERE c.user_id = %s
            """
            params = [user_id]
            if paper_id is not None:
                base_sql += " AND q.paper_id = %s"
                params.append(paper_id)

            cursor.execute(f"SELECT COUNT(*) as total {base_sql}", params)
            total = cursor.fetchone()["total"]

            # due_date <= NOW() 表示已到期
            cursor.execute(
                f"SELECT COUNT(*) as due {base_sql} AND c.due_date <= NOW()", params
            )
            due = cursor.fetchone()["due"]

            # 今日已复习：DATE(last_reviewed_at) = CURDATE()
            cursor.execute(
                f"SELECT COUNT(*) as today_reviewed {base_sql} AND DATE(c.last_reviewed_at) = CURDATE()",
                params,
            )
            today_reviewed = cursor.fetchone()["today_reviewed"]

            cursor.execute(
                f"SELECT COUNT(*) as mastered {base_sql} AND c.repetitions >= 3", params
            )
            mastered = cursor.fetchone()["mastered"]

            return {
                "total": total,
                "due": due,
                "today_reviewed": today_reviewed,
                "mastered": mastered,
            }
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
