import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 优先加载同目录下的 .env；override=False 表示已存在的环境变量优先
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)


def _get_int(key: str, default: int) -> int:
    """读取整型环境变量，非法值回落到默认值"""
    raw = os.getenv(key)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_str(key: str, default: str = "") -> str:
    val = os.getenv(key)
    return val if val is not None else default


# ============ MySQL 数据库配置 ============
MYSQL_HOST = _get_str("MYSQL_HOST", "localhost")
MYSQL_USER = _get_str("MYSQL_USER", "root")
MYSQL_PASSWORD = _get_str("MYSQL_PASSWORD", "")
MYSQL_DB = _get_str("MYSQL_DB", "exam_db")
MYSQL_PORT = _get_int("MYSQL_PORT", 3306)

# ============ 智谱 AI 配置 ============
ZHIPU_API_KEY = _get_str("ZHIPU_API_KEY", "")
ZHIPU_MODEL = _get_str("ZHIPU_MODEL", "glm-4.7-flash")
ZHIPU_RETRY_COUNT = _get_int("ZHIPU_RETRY_COUNT", 7)
ZHIPU_RETRY_DELAY = _get_int("ZHIPU_RETRY_DELAY", 2)

# ============ 题型顺序（代码常量，不放进 .env） ============
TYPE_ORDER = {
    "single_choice": 0,
    "multiple_choice": 1,
    "true_false": 2,
    "fill_in_blank": 3,
    "calculation": 4,
    "essay": 5,
}

TYPE_NAMES = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "true_false": "判断题",
    "fill_in_blank": "填空题",
    "calculation": "计算题",
    "essay": "解答题",
}
