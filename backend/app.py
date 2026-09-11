from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from data_manager import *
import random
import json
import sys
from zai import ZhipuAiClient
from zhipuai import ZhipuAI
from config import ZHIPU_API_KEY, ZHIPU_MODEL, ZHIPU_RETRY_COUNT, ZHIPU_RETRY_DELAY
import time
import atexit

app = Flask(__name__)
# 初始化智谱客户端
client = ZhipuAiClient(api_key=ZHIPU_API_KEY)
CORS(app)
init_db()
print("数据库初始化完成", file=sys.stderr)

# 创建调度器
scheduler = BackgroundScheduler()
# 每天凌晨2点执行清理
scheduler.add_job(func=clean_old_progress, trigger="cron", hour=2, minute=0)
scheduler.start()

# 在应用退出时关闭调度器
atexit.register(lambda: scheduler.shutdown())


# ------------------------- 全局状态类 -------------------------
class ExamState:

    def __init__(self):
        print("ExamState 初始化开始", file=sys.stderr)
        try:
            self.questions, self.paper_info = load_questions()
            self.total = len(self.questions)
            settings = load_user_settings()
            self.current_pos = settings.get("current_pos", 0)
            self.filter_wrong = settings.get("filter_wrong", False)
            self.random_order = settings.get("random_order", False)
            self.wrong_ids = set(get_wrong_question_ids(1))
            self.practice_limit = settings.get("practice_limit", 20)
            self.paper_id = settings.get("paper_id")  # ← 新增
            self.order_list = []
            self.progress = settings.get("progress", {})
            self._build_order_list()
            print(f"ExamState 初始化成功，paper_id={self.paper_id}", file=sys.stderr)
        except Exception as e:
            print(f"ExamState 初始化失败: {e}", file=sys.stderr)
            self.questions = []
            self.paper_info = {"title": "无试卷"}
            self.total = 0
            self.current_pos = 0
            self.filter_wrong = False
            self.random_order = False
            self.wrong_ids = set()
            self.order_list = []
            self.practice_limit = 20
            self.paper_id = None

    def _build_order_list(self):
        # 先按 paper_id 过滤基础题目集合
        if self.paper_id is not None:
            base_indices = [
                i
                for i, q in enumerate(self.questions)
                if q.get("paper_id") == self.paper_id
            ]
        else:
            base_indices = list(range(self.total))

        # 再按错题/未作答过滤
        if self.filter_wrong:
            wrong_ids_str = {str(wid) for wid in self.wrong_ids}
            indices = [
                i for i in base_indices if str(self.questions[i]["id"]) in wrong_ids_str
            ]
            print(
                f"错题库模式：错题数量 {len(self.wrong_ids)}，过滤后 indices 数量 {len(indices)}"
            )
        else:
            indices = [
                i
                for i in base_indices
                if not self.progress.get(str(self.questions[i]["id"]), False)
            ]

        if self.random_order:
            random.shuffle(indices)
        else:
            indices.sort(key=lambda idx: self.questions[idx]["id"])

        if self.practice_limit > 0 and len(indices) > self.practice_limit:
            indices = random.sample(indices, self.practice_limit)

        self.order_list = indices

        # all_done 判断应基于当前试卷的题目数
        paper_total = len(base_indices)
        self.all_done = (not self.filter_wrong) and (
            len(self.order_list) == 0 and paper_total > 0
        )

    def rebuild_order(self):
        self._build_order_list()
        if self.current_pos >= len(self.order_list):
            self.current_pos = 0

    def current_question(self):
        if not self.order_list:
            return None
        if self.current_pos >= len(self.order_list):
            self.current_pos = 0
        idx = self.order_list[self.current_pos]
        return idx, self.questions[idx]

    def get_question_data(self, idx):
        q = self.questions[idx]
        return {
            "id": q["id"],
            "paper_id": q.get("paper_id"),  # 新增
            "type": q["type"],
            "content": q["content"],
            "options": q.get("options", []),
            "explanation": q.get("explanation", ""),
            "steps": q.get("steps", []),
            "correct_answer": q.get("answer", ""),
            "user_answer": None,
        }

    def check_answer(self, user_ans, correct_ans, q_type):
        if q_type == "single_choice":
            return user_ans == correct_ans
        elif q_type == "multiple_choice":
            if not isinstance(user_ans, list) or not isinstance(correct_ans, list):
                return False
            return set(user_ans) == set(correct_ans)
        elif q_type == "true_false":

            def to_bool(v):
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    return v.lower() == "true"
                return bool(v)

            return to_bool(user_ans) == to_bool(correct_ans)
        elif q_type in ("fill_in_blank", "calculation"):
            return user_ans.strip() == correct_ans.strip()
        elif q_type == "essay":
            # 解答题默认正确（后续可人工评分）
            return True
        return False

    def save_progress(self):
        settings = {
            "current_pos": self.current_pos,
            "filter_wrong": self.filter_wrong,
            "random_order": self.random_order,
            "practice_limit": self.practice_limit,
            "paper_id": self.paper_id,  # 新增
            "progress": self.progress,
        }
        save_user_settings(settings)

    def reload_questions(self):
        try:
            self.questions, self.paper_info = load_questions()
            self.total = len(self.questions)
            self.wrong_ids = set(get_wrong_question_ids(1))
            self.rebuild_order()
            self.save_progress()
            return True
        except Exception as e:
            print(f"刷新题库失败: {e}", file=sys.stderr)
            return False

    def get_answer_sheet(self):
        items = []
        wrong_ids_str = {str(wid) for wid in self.wrong_ids}
        for pos, idx in enumerate(self.order_list):
            q = self.questions[idx]
            items.append(
                {
                    "pos": pos,
                    "index": idx,
                    "id": q["id"],
                    "type": q["type"],
                    "is_wrong": str(q["id"]) in wrong_ids_str,
                }
            )
        return {
            "total": len(self.order_list),
            "items": items,
            "current_pos": self.current_pos,
        }


state = ExamState()


# ------------------------- API 路由 -------------------------
@app.route("/api/test", methods=["GET"])
def test():
    return jsonify({"status": "ok"})


@app.route("/api/questions", methods=["GET"])
def get_questions():
    print(f"处理 /api/questions, order_list 长度: {len(state.order_list)}")
    if not state.order_list:
        # 无题目时返回空状态（200），让前端根据 filter_wrong 决定显示什么
        return jsonify(
            {
                "current_pos": 0,
                "total_display": 0,
                "total_all": state.total,
                "is_wrong": False,
                "all_done": not state.filter_wrong,  # 未作答模式无题表示全部完成
            }
        )

    # 确保 current_pos 在范围内
    if state.current_pos >= len(state.order_list):
        state.current_pos = 0
        state.save_progress()

    idx = state.order_list[state.current_pos]
    q = state.questions[idx]
    data = state.get_question_data(idx)
    data["current_pos"] = state.current_pos
    data["total_display"] = len(state.order_list)
    data["total_all"] = state.total
    data["is_wrong"] = q["id"] in state.wrong_ids
    print(f"返回题目 ID: {q['id']}, 当前进度: {state.current_pos}")
    return jsonify(data)


@app.route("/api/settings", methods=["POST"])
def set_settings():
    data = request.json
    if "filter_wrong" in data:
        state.filter_wrong = data["filter_wrong"]
    if "random_order" in data:
        state.random_order = data["random_order"]
    if "limit" in data:
        state.practice_limit = data["limit"]
    if "paper_id" in data:
        state.paper_id = data["paper_id"]
        state.current_pos = 0  # 切换试卷时重置进度
    state.rebuild_order()
    state.save_progress()
    return jsonify(
        {
            "status": "ok",
            "filter_wrong": state.filter_wrong,
            "random_order": state.random_order,
            "practice_limit": state.practice_limit,
            "paper_id": state.paper_id,
        }
    )


@app.route("/api/user_settings", methods=["GET"])
def get_user_settings():
    return jsonify(
        {
            "filter_wrong": state.filter_wrong,
            "random_order": state.random_order,
            "practice_limit": state.practice_limit,
            "paper_id": state.paper_id,
            "current_pos": state.current_pos,
        }
    )


@app.route("/api/submit", methods=["POST"])
def submit_answer():
    data = request.json
    question_id = data.get("index")
    user_ans = data.get("answer")
    if question_id is None:
        return jsonify({"error": "缺少题目id"}), 400

    target_idx = None
    for i, q in enumerate(state.questions):
        if q["id"] == question_id:
            target_idx = i
            break
    if target_idx is None:
        return jsonify({"error": "题目不存在"}), 400

    q = state.questions[target_idx]
    q_type = q["type"]
    correct_ans = q["answer"]

    # ----- 评判逻辑 -----
    if q_type == "single_choice":
        is_correct = user_ans == correct_ans
    elif q_type == "multiple_choice":
        if not isinstance(user_ans, list) or not isinstance(correct_ans, list):
            is_correct = False
        else:
            is_correct = set(user_ans) == set(correct_ans)
    elif q_type == "true_false":

        def to_bool(v):
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                return v.lower() == "true"
            return bool(v)

        is_correct = to_bool(user_ans) == to_bool(correct_ans)
    elif q_type in ("fill_in_blank", "calculation", "essay"):
        is_correct = user_ans.strip() == correct_ans.strip()
    else:
        is_correct = False

    # 错题处理（仅一次）
    if is_correct:
        remove_wrong_question(1, question_id)
        update_progress_timestamp(question_id)
    else:
        add_wrong_question(1, question_id)

    # 更新错题ID列表
    state.wrong_ids = set(get_wrong_question_ids(1))

    # 记录已作答
    qid_str = str(question_id)
    if not state.progress.get(qid_str, False):
        state.progress[qid_str] = True
        state.save_progress()

    return jsonify(
        {
            "correct": is_correct,
            "correct_answer": correct_ans,
            "explanation": q.get("explanation", ""),
            "steps": q.get("steps", []),
            "is_wrong": (not is_correct) and (question_id in state.wrong_ids),
            "all_done": state.all_done,
        }
    )


@app.route("/api/reset_progress", methods=["POST"])
def reset_progress():
    state.progress = {}
    state.save_progress()
    state.rebuild_order()
    return jsonify({"status": "ok"})


@app.route("/api/reset_all", methods=["POST"])
def reset_all():
    from data_manager import get_db

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM wrong_questions WHERE user_id = 1")
            cursor.execute("DELETE FROM user_settings WHERE user_id = 1")
        conn.commit()
    finally:
        conn.close()
    state.wrong_ids = set()
    state.current_pos = 0
    state.rebuild_order()
    state.save_progress()
    return jsonify({"status": "ok"})


@app.route("/api/reload", methods=["POST"])
def reload_questions():
    success = state.reload_questions()
    if success:
        return jsonify({"status": "ok", "total": state.total})
    else:
        return jsonify({"error": "刷新题库失败"}), 500


@app.route("/api/answer_sheet", methods=["GET"])
def answer_sheet():
    return jsonify(state.get_answer_sheet())


@app.route("/api/jump", methods=["POST"])
def jump_to():
    data = request.json
    pos = data.get("pos")
    if pos is None or not isinstance(pos, int):
        return jsonify({"error": "缺少位置参数"}), 400
    if pos < 0 or pos >= len(state.order_list):
        return jsonify({"error": "位置超出范围"}), 400
    state.current_pos = pos
    state.save_progress()
    result = state.current_question()
    if result is None:
        return jsonify({"error": "无题目"}), 404
    idx, q = result
    data = state.get_question_data(idx)
    data["current_pos"] = state.current_pos
    data["total_display"] = len(state.order_list)
    data["total_all"] = state.total
    data["is_wrong"] = q["id"] in state.wrong_ids
    return jsonify(data)


@app.route("/api/navigate", methods=["POST"])
def navigate():
    data = request.json
    direction = data.get("direction")
    if direction == "next":
        if state.current_pos + 1 < len(state.order_list):
            state.current_pos += 1
        else:
            return jsonify(
                {
                    "is_last": True,
                    "need_refresh": not state.filter_wrong,
                    "current_pos": state.current_pos,
                    "total_display": len(state.order_list),
                    "total_all": state.total,
                }
            )
    elif direction == "prev":
        if state.current_pos > 0:
            state.current_pos -= 1
        else:
            return jsonify({"error": "已经是第一题"}), 400
    else:
        return jsonify({"error": "无效方向"}), 400

    state.save_progress()
    result = state.current_question()
    if result is None:
        return jsonify({"error": "无题目"}), 404
    idx, q = result
    data = state.get_question_data(idx)
    data["current_pos"] = state.current_pos
    data["total_display"] = len(state.order_list)
    data["total_all"] = state.total
    data["is_wrong"] = q["id"] in state.wrong_ids
    return jsonify(data)


@app.route("/api/refresh", methods=["POST"])
def refresh_questions():
    """重新生成题目顺序（基于当前 filter_wrong 和 progress），并返回第一题"""
    state.rebuild_order()
    state.current_pos = 0
    state.save_progress()
    idx, q = state.current_question()
    if q is None:
        return jsonify({"error": "没有符合条件的题目"}), 404
    data = state.get_question_data(idx)
    data["current_pos"] = state.current_pos
    data["total_display"] = len(state.order_list)
    data["total_all"] = state.total
    data["is_wrong"] = q["id"] in state.wrong_ids
    return jsonify(data)


@app.route("/api/wrong_report", methods=["GET"])
def wrong_report():
    """获取所有错题数据（不含AI）"""
    from data_manager import get_wrong_report_data

    data = get_wrong_report_data(1)
    return jsonify(data)


@app.route("/api/chop_question", methods=["POST"])
def chop_question():
    data = request.json
    question_id = data.get("index")
    if question_id is None:
        return jsonify({"error": "缺少题目id"}), 400

    # 查找题目
    target_idx = None
    for i, q in enumerate(state.questions):
        if q["id"] == question_id:
            target_idx = i
            break
    if target_idx is None:
        return jsonify({"error": "题目不存在"}), 400

    # 强制标记为正确：从错题表中移除（如果存在），并记录已作答
    remove_wrong_question(1, question_id)
    qid_str = str(question_id)
    if not state.progress.get(qid_str, False):
        state.progress[qid_str] = True
        state.save_progress()

    # 更新错题ID列表
    state.wrong_ids = set(get_wrong_question_ids(1))
    # 重建顺序（可选，但不需要立即重建，因为用户会跳转）
    # 返回成功
    return jsonify({"status": "ok"})


@app.route("/api/chat", methods=["POST"])
def chat():
    """AI 对话接口"""
    data = request.json
    user_message = data.get("message")
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 可以维护对话上下文（可选），此处仅单轮
    try:
        response = client.chat.completions.create(
            model=ZHIPU_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个学习助手，帮助用户解答学习问题。",
                },
                {"role": "user", "content": user_message},
            ],
            max_tokens=4096,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"AI 对话失败: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500


# 管理接口
@app.route("/api/manage/list", methods=["GET"])
def manage_list():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "")
    wrong_only = request.args.get("wrong_only", "false").lower() == "true"
    qtype = request.args.get("type", "")
    unanswered_only = request.args.get("unanswered_only", "false").lower() == "true"
    paper_id = request.args.get("paper_id", type=int)  # ← 新增

    questions, total = get_questions_page(
        search,
        page,
        per_page,
        wrong_only,
        qtype,
        unanswered_only,
        paper_id,  # ← 传递 paper_id
    )
    return jsonify(
        {"items": questions, "total": total, "page": page, "per_page": per_page}
    )


@app.route("/api/manage/create", methods=["POST"])
def create_question():
    data = request.get_json()
    knowledge_ids = data.get("knowledge_ids", [])
    qid = create_question_in_db(data)
    if knowledge_ids:
        set_question_knowledge(qid, knowledge_ids)
    state.reload_questions()
    reset_all_ids()
    state.reload_questions()
    return jsonify({"id": qid, "success": True})


@app.route("/api/manage/batch_delete", methods=["POST"])
def batch_delete():
    data = request.get_json()
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "未提供ID"}), 400
    batch_delete_questions(ids)
    state.reload_questions()
    reset_all_ids()  # 新增
    state.reload_questions()
    return jsonify({"success": True})


@app.route("/api/manage/edit/<int:qid>", methods=["PUT"])
def edit_question(qid):
    data = request.get_json()
    knowledge_ids = data.get("knowledge_ids", [])
    update_question(qid, data)
    set_question_knowledge(qid, knowledge_ids)
    state.reload_questions()
    return jsonify({"success": True})


@app.route("/api/manage/delete/<int:qid>", methods=["DELETE"])
def delete_question_route(qid):
    delete_question(qid)
    state.reload_questions()
    reset_all_ids()  # 新增
    state.reload_questions()
    return jsonify({"success": True})


@app.route("/api/import", methods=["POST"])
def import_questions():
    data = request.get_json()
    if not data or "questions" not in data:
        return jsonify({"error": "无效数据"}), 400
    paper_id = data.get("paper_id")  # ← 从请求中获取
    added, skipped = import_from_json_data(data, paper_id)
    state.reload_questions()
    reset_all_ids()
    state.reload_questions()
    return jsonify({"added": added, "skipped": skipped})


@app.route("/api/stats", methods=["GET"])
def get_stats():
    data = get_stats_data()
    return jsonify(data)


@app.route("/api/recent_wrong", methods=["GET"])
def recent_wrong():
    limit = request.args.get("limit", 10, type=int)
    data = get_recent_wrong_questions(1, limit)
    return jsonify(data)


@app.route("/api/clean_progress", methods=["POST"])
def clean_progress():
    days = request.json.get("days", 7)
    clean_old_progress(days)
    return jsonify({"status": "ok", "days": days})


@app.route("/api/set_clean_days", methods=["POST"])
def set_clean_days():
    data = request.json
    days = data.get("days", 7)
    if days < 1:
        days = 1
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE user_settings SET clean_days = %s WHERE user_id = 1", (days,)
            )
            conn.commit()
        return jsonify({"status": "ok", "days": days})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------- 试卷管理 -------------------------
@app.route("/api/papers", methods=["GET"])
def get_papers():
    papers = get_all_papers()
    return jsonify(papers)


@app.route("/api/papers", methods=["POST"])
def create_paper():
    data = request.json
    title = data.get("title", "未命名试卷")
    if not title:
        return jsonify({"error": "试卷名称不能为空"}), 400
    paper_id = create_paper_db(title)
    return jsonify({"id": paper_id, "title": title})


@app.route("/api/papers/<int:paper_id>", methods=["PUT"])
def update_paper(paper_id):
    data = request.json
    title = data.get("title")
    if not title:
        return jsonify({"error": "试卷名称不能为空"}), 400
    update_paper(paper_id, title)
    return jsonify({"status": "ok"})


@app.route("/api/papers/<int:paper_id>", methods=["DELETE"])
def delete_paper(paper_id):
    delete_paper(paper_id)
    state.reload_questions()
    return jsonify({"status": "ok"})


@app.route("/api/knowledge_graph", methods=["GET"])
def knowledge_graph():
    data = get_knowledge_graph_data(1)
    return jsonify(data)


# ------------------------- 知识点管理 -------------------------
@app.route("/api/knowledge_points", methods=["GET"])
def get_knowledge_points():
    return jsonify(get_all_knowledge_points())


@app.route("/api/knowledge_points", methods=["POST"])
def create_knowledge_point():
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "知识点名称不能为空"}), 400
    kp_id = create_knowledge_point(name, data.get("description", ""))
    return jsonify({"id": kp_id, "name": name})


@app.route("/api/knowledge_points/<int:kp_id>", methods=["PUT"])
def update_knowledge_point(kp_id):
    data = request.json
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "知识点名称不能为空"}), 400
    update_knowledge_point(kp_id, name, data.get("description", ""))
    return jsonify({"status": "ok"})


@app.route("/api/knowledge_points/<int:kp_id>", methods=["DELETE"])
def delete_knowledge_point(kp_id):
    delete_knowledge_point(kp_id)
    return jsonify({"status": "ok"})


# 题目-知识点关联 (在新增/编辑题目时已处理，此处仅提供获取)
@app.route("/api/question_knowledge/<int:qid>", methods=["GET"])
def get_question_knowledge_route(qid):
    return jsonify(get_question_knowledge(qid))


# 知识图谱数据
@app.route("/api/knowledge_graph", methods=["GET"])
def get_knowledge_graph():
    data = get_knowledge_graph_data(1)  # user_id=1
    return jsonify(data)


@app.route("/api/daily_stats", methods=["GET"])
def daily_stats():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    data = get_daily_stats(1, year, month)
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
