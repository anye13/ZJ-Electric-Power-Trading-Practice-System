import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# MySQL 数据库配置（请根据实际修改）
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "Zcy13145257!!"
MYSQL_DB = "exam_db"
MYSQL_PORT = 3306
# 智谱AI配置
ZHIPU_API_KEY = (
    "470c2eecc7484ad4bba03801e50c50a5.fCxqzRVC2nFJYu9x"  # 请替换为您的API Key
)
ZHIPU_MODEL = "glm-4.7-flash"  # 可选：glm-4, glm-3-turbo
ZHIPU_RETRY_COUNT = 7  # 重试次数
ZHIPU_RETRY_DELAY = 2  # 初始延迟（秒），指数退避
# 题型顺序（用于排序）
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
