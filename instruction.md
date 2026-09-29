# Git 上传 / 下载命令总结

- 项目：`ZJ-Electric-Power-Trading-Practice-System`
- 仓库：`https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git`
- 本地路径：`E:\工作文件\Python-project\practice system`

---

## 一、上传前必做（安全自查）

### 1.1 检查子目录有没有独立的 .git

`backend` / `frontend` 若是从模板 clone 来的，可能各自带 `.git`，会被当成 submodule（推上去只是空链接，代码丢失）。

```powershell
cd "E:\工作文件\Python-project\practice system"
Get-ChildItem -Recurse -Force -Directory -Filter ".git" | Select-Object FullName
```

若有 `backend\.git`、`frontend\.git`，确认不需要历史后删除：

```powershell
Remove-Item -Recurse -Force ".\backend\.git"
Remove-Item -Recurse -Force ".\frontend\.git"
```

### 1.2 敏感信息自查

推之前扫一遍已跟踪文件，确认没有硬编码的密码 / Key：

```powershell
git ls-files                                            # 看有没有 .env、数据库、密钥文件
git grep -n -i -E "password|api_key|secret|token|passwd"  # 搜关键词
```

搜出内容就说明还有东西要脱敏，先做第三章再上传。

### 1.3 建好 .gitignore

在项目根目录新建 `.gitignore`：

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/
.pytest_cache/
.mypy_cache/
*.db
*.sqlite3

# Node
node_modules/
dist/
build/
.vite/
.next/
npm-debug.log*
yarn-error.log*
pnpm-debug.log*

# 环境变量（顺序不能反，!.env.example 必须在最后）
.env
.env.*
!.env.example

# IDE
.vscode/
.idea/
*.swp

# 系统文件
.DS_Store
Thumbs.db

# 日志
*.log
```

---

## 二、上传（原机器 → GitHub）

### 2.1 首次上传完整流程

```powershell
# 1. 进入项目目录
cd "E:\工作文件\Python-project\practice system"

# 2. 初始化仓库并切到 main 分支
git init
git branch -M main

# 3. 提交（用 -A，新增/修改/删除都覆盖）
git add -A
git status          # 确认没有 node_modules / .venv / .env
git commit -m "chore: 初始化项目"

# 4. 关联远程（已存在 origin 时用 set-url）
git remote add origin https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git
# 若报 remote origin already exists：
# git remote set-url origin https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git

# 5. 推送
git push -u origin main
# 远程非空被拒时：git push -u origin main --force
```

### 2.2 覆盖远程（本地为准，强制推送）

想让远程内容和本地完全一致：

```powershell
git add -A
git status              # 确认 modified / deleted 都被记录
git commit -m "更新：覆盖远程内容"
git push origin main --force
```

**`git add .` 与 `git add -A` 的区别**（之前"只推了新文件"就是踩了这个）：

| 命令 | 新增 | 修改 | 删除 |
|---|---|---|---|
| `git add .` | ✅ | ✅ | ❌ |
| `git add -u` | ❌ | ✅ | ✅ |
| `git add -A` | ✅ | ✅ | ✅ |

若被分支保护拦下（`GH006: Protected branch update failed`）：
GitHub → 仓库 Settings → Branches → 删除或暂时关闭 `main` 的保护规则，推完再开。

> ⚠️ 强制推送会永久丢弃远程上本地没有的提交。推之前用 `git status` / `git log --oneline` 确认。

### 2.3 后续日常更新

```powershell
cd "E:\工作文件\Python-project\practice system"
git add -A
git commit -m "描述这次改了什么"
git push
```

---

## 三、敏感信息脱敏改造

### 3.1 改造 config.py

不要用"打码后硬编码"（如 `MYSQL_PASSWORD = "******"`），程序跑不起来。正确做法是把密钥放进 `.env`，代码只读环境变量。

```python
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# MySQL 数据库配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "exam_db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))

# 智谱AI配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_MODEL = os.getenv("ZHIPU_MODEL", "glm-4.7-flash")
ZHIPU_RETRY_COUNT = int(os.getenv("ZHIPU_RETRY_COUNT", "7"))
ZHIPU_RETRY_DELAY = int(os.getenv("ZHIPU_RETRY_DELAY", "2"))

# 以下不含敏感信息，保持原样
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
```

### 3.2 新建 .env（本地用，绝对不提交）

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=你的新密码
MYSQL_DB=exam_db
MYSQL_PORT=3306
ZHIPU_API_KEY=你的新APIKey
ZHIPU_MODEL=glm-4.7-flash
```

### 3.3 新建 .env.example（提交到仓库，只留格式）

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DB=exam_db
MYSQL_PORT=3306
ZHIPU_API_KEY=your_api_key_here
ZHIPU_MODEL=glm-4.7-flash
```

### 3.4 安装依赖

```powershell
pip install python-dotenv
pip freeze > requirements.txt
```

### 3.5 如果密钥已经推送过（清历史）

**光改文件再提交不够**，旧密钥还在 Git 历史里，任何人能翻出来。同时务必：

1. 改掉 MySQL 密码（别用 root 直连更好）；
2. 去智谱开放平台重新生成 API Key，作废旧 Key。

#### 方案 A：仓库刚建、只有自己用 → 推平重来（最简单）

```powershell
cd "E:\工作文件\Python-project\practice system"

Remove-Item -Recurse -Force .git
git init
git branch -M main
git add -A
git commit -m "init: 清理敏感信息后重新提交"
git remote add origin https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git
git push origin main --force
```

#### 方案 B：有需要保留的历史 → filter-repo / BFG

```powershell
pip install git-filter-repo

# 把含密钥的文件从所有历史中移除
git filter-repo --path backend/config.py --invert-paths
# 注意：文件本身也会被删，之后要重新添加脱敏版
```

或用 BFG（需 Java）：

```powershell
java -jar bfg.jar --replace-text passwords.txt
# passwords.txt 每行写一个要替换的敏感字符串
```

清理完同样要 `git push origin main --force`，然后联系 GitHub Support 清理缓存（force push 后旧提交仍可能通过 commit hash 直链访问一段时间）。

---

## 四、下载（另一台机器 ← GitHub）

### 4.1 首次克隆

```powershell
git clone https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git
cd ZJ-Electric-Power-Trading-Practice-System
```

### 4.2 后端（Python）

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # 然后编辑 .env 填真实配置
# alembic upgrade head      # 若有数据库迁移
python main.py              # 按项目实际启动命令
```

### 4.3 前端（Node）

```powershell
cd frontend
npm install
npm run dev
```

### 4.4 后续拉取最新代码

```powershell
cd ZJ-Electric-Power-Trading-Practice-System
git pull
# 如果依赖有变化：
#   后端：pip install -r requirements.txt
#   前端：npm install
```

> **不能直接跑**：Git 只传源码，`node_modules`、`.venv`、`.env`、数据库、构建产物都不在里面，必须按上面步骤补装依赖和配置。

---

## 五、网络问题排查

### 5.1 SSL 证书报错

`SSL certificate verify result: unable to get local issuer certificate (20)`

让 Git 改用 Windows 系统证书存储：

```powershell
git config --global http.sslBackend schannel
git push -u origin main --force
```

不行的话，可临时关闭验证（**仅诊断，推完立刻恢复**）：

```powershell
git config --global http.sslVerify false
git push -u origin main --force
git config --global http.sslVerify true
```

公司网络下可再加：`git config --global http.schannelCheckRevoke false`

### 5.2 Connection was reset

先查代理配置：

```powershell
git config --global --get http.proxy
git config --global --get https.proxy
```

**用了代理软件（Clash / V2Ray 等）**——端口要和软件一致，常见 `7890` / `10809`：

```powershell
git config --global http.proxy http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

**没用代理或代理已关**——取消 Git 的代理设置：

```powershell
git config --global --unset http.proxy
git config --global --unset https.proxy
```

仍不行，以**管理员身份**刷新网络后重启：

```powershell
ipconfig /flushdns
netsh winsock reset
```

也可临时在"网络连接 → 网卡属性"里取消勾选 `Internet 协议版本 6 (TCP/IPv6)`。

### 5.3 改用 SSH（长期推荐，绕过 HTTPS 证书与代理问题）

```powershell
# 1. 生成 Key（已有则跳过）
ssh-keygen -t ed25519 -C "你的邮箱"

# 2. 把 ~/.ssh/id_ed25519.pub 内容贴到 GitHub
#    Settings → SSH and GPG keys → New SSH key

# 3. 测试
ssh -T git@github.com

# 4. 切换远程地址并推送
git remote set-url origin git@github.com:anye13/ZJ-Electric-Power-Trading-Practice-System.git
git push -u origin main --force
```

22 端口被封锁时，编辑 `~/.ssh/config`：

```
Host github.com
  Hostname ssh.github.com
  Port 443
  User git
```

---

## 六、常用命令速查

| 操作               | 命令                                     |
| ------------------ | ---------------------------------------- |
| 看远程地址         | `git remote -v`                          |
| 改远程地址         | `git remote set-url origin <新地址>`     |
| 看状态             | `git status`                             |
| 看提交历史         | `git log --oneline`                      |
| 看当前分支         | `git branch`                             |
| 拉取最新           | `git pull`                               |
| 推送               | `git push`                               |
| 强制覆盖远程       | `git push origin main --force`           |
| 撤销 add（未提交） | `git restore --staged .`                 |
| 查看某文件改动     | `git diff <文件名>`                      |
| 列出已跟踪文件     | `git ls-files`                           |
| 搜敏感关键词       | `git grep -n -i -E "password\|api_key"`  |

---

## 七、容易踩的坑

1. **远程已有内容**：新建仓库时别勾 README / .gitignore / license，否则首次推送要 `--force` 或先 `git pull --rebase`。
2. **子目录带 .git**：会变成空的 submodule，代码丢失，推之前先删。
3. **上传了 node_modules / .venv**：几百 MB，推送超时或失败，靠 `.gitignore` 拦住。
4. **.env 被上传**：密钥泄露，务必加进 `.gitignore`，只提交 `.env.example`；`!.env.example` 必须写在 `.env.*` 之后。
5. **只推了新文件**：`git add .` 不记录删除，统一用 `git add -A`。
6. **HTTPS 认证**：密码位置填 Personal Access Token（勾 `repo` 权限），不是 GitHub 登录密码。
7. **密钥进过历史**：改文件没用，必须清历史 + 立即更换密码和 Key。
8. **另一台机器跑不起来**：多半是缺 `requirements.txt`、`.env`、数据库，或 Python / Node 版本不一致。
9. **大文件超 100MB**：用 Git LFS，或从历史中彻底删除。
10. **中文文件名乱码**：`git config --global core.quotepath false`。