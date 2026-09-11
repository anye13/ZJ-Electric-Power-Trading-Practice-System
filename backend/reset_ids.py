import json
import pymysql
import sys
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT


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


def reset_ids():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 获取所有题目，按当前 ID 排序
            cursor.execute(
                "SELECT id, type, content, options, answer, explanation, steps, paper_id FROM questions ORDER BY id"
            )
            rows = cursor.fetchall()
            if not rows:
                print("题库为空，无需重置")
                return

            # 2. 构建旧ID到新ID的映射
            old_to_new = {}
            new_id = 1
            for row in rows:
                old_to_new[row["id"]] = new_id
                new_id += 1

            print(f"共 {len(rows)} 道题目，将重置 ID 为 1~{len(rows)}")

            # 3. 更新 user_settings 中的 progress JSON
            cursor.execute("SELECT progress FROM user_settings WHERE user_id = 1")
            row = cursor.fetchone()
            if row and row["progress"]:
                progress = json.loads(row["progress"])
                new_progress = {}
                for old_qid, answered in progress.items():
                    old_qid_int = int(old_qid)
                    if old_qid_int in old_to_new:
                        new_progress[str(old_to_new[old_qid_int])] = answered
                if new_progress:
                    cursor.execute(
                        "UPDATE user_settings SET progress = %s WHERE user_id = 1",
                        (json.dumps(new_progress),),
                    )
                    print("user_settings.progress 已更新")
                else:
                    print("user_settings.progress 无有效数据，跳过")

            # 4. 更新 wrong_questions 中的 question_id
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
                print(f"wrong_questions 表已更新 {len(wrong_rows)} 条记录")

            # 5. 重建 questions 表（由于主键自增，需先删除再插入）
            # 方法：创建临时表，插入新数据，删除原表，重命名临时表
            cursor.execute("CREATE TABLE questions_new LIKE questions")
            # 插入新数据（新 ID 从 1 开始）
            for old_row, new_id in zip(rows, range(1, len(rows) + 1)):
                cursor.execute(
                    """INSERT INTO questions_new
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

            # 删除原表，重命名新表
            cursor.execute("DROP TABLE questions")
            cursor.execute("RENAME TABLE questions_new TO questions")

            # 6. 更新 paper_info 中的 total_questions
            cursor.execute("UPDATE paper_info SET total_questions = %s", (len(rows),))
            print(f"paper_info.total_questions 更新为 {len(rows)}")

            # 7. 重置 auto_increment（可选）
            cursor.execute(
                "ALTER TABLE questions AUTO_INCREMENT = %s", (len(rows) + 1,)
            )

            conn.commit()
            print("✅ ID 重置成功！所有相关表已同步更新。")

    except Exception as e:
        conn.rollback()
        print(f"❌ 重置失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("开始重置题目 ID...")
    reset_ids()
    print("脚本执行完毕。")
