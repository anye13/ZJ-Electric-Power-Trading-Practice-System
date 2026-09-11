# Git 上传 / 下载命令总结

针对你的项目 `ZJ-Electric-Power-Trading-Practice-System`。

---

## 一、上传（原机器 → GitHub）

### 首次上传完整流程

```powershell
# 1. 进入项目目录
cd "E:\工作文件\Python-project\practice system"

# 2. 检查子目录有没有独立的 .git（有就删掉）
Get-ChildItem -Recurse -Force -Directory -Filter ".git" | Select-Object FullName

# 3. 初始化仓库并切到 main 分支
git init
git branch -M main

# 4. 提交（提交前先建好 .gitignore）
git add .
git status          # 确认没有 node_modules / .venv / .env
git commit -m "chore: 初始化项目"

# 5. 关联远程（已存在 origin 时用 set-url）
git remote add origin https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git
# 若报 remote origin already exists：
# git remote set-url origin https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git

# 6. 推送
git push -u origin main
# 远程非空被拒时：git push -u origin main --force
```

### 遇到 SSL 证书报错时

```powershell
git config --global http.sslBackend schannel
git push -u origin main --force
```

### 后续日常更新（改动后再上传）

```powershell
cd "E:\工作文件\Python-project\practice system"
git add .
git commit -m "描述这次改了什么"
git push
```

---

## 二、下载（另一台机器 ← GitHub）

### 首次克隆

```powershell
# 1. 克隆
git clone https://github.com/anye13/ZJ-Electric-Power-Trading-Practice-System.git
cd ZJ-Electric-Power-Trading-Practice-System
```

### 后端（Python）

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # 然后编辑 .env 填配置
# alembic upgrade head      # 若有数据库迁移
python main.py              # 按项目实际启动命令
```

### 前端（Node）

```powershell
cd frontend
npm install
npm run dev
```

### 后续拉取最新代码

```powershell
cd ZJ-Electric-Power-Trading-Practice-System
git pull
# 如果依赖有变化：
#   后端：pip install -r requirements.txt
#   前端：npm install
```

---

## 三、常用命令速查

| 操作 | 命令 |
|---|---|
| 看远程地址 | `git remote -v` |
| 改远程地址 | `git remote set-url origin <新地址>` |
| 看状态 | `git status` |
| 看提交历史 | `git log --oneline` |
| 看当前分支 | `git branch` |
| 拉取最新 | `git pull` |
| 推送 | `git push` |
| 撤销 add（未提交） | `git restore --staged .` |
| 查看某文件改动 | `git diff <文件名>` |

---

## 四、容易踩的坑

1. **远程已有内容**：新建仓库时别勾 README / .gitignore / license，否则首次推送要 `--force` 或先 `git pull --rebase`。
2. **子目录带 .git**：会变成空的 submodule，代码丢失，推之前先删。
3. **上传了 node_modules / .venv**：几百 MB，推送超时或失败，靠 `.gitignore` 拦住。
4. **.env 被上传**：密钥泄露，务必加进 `.gitignore`，只提交 `.env.example`。
5. **HTTPS 认证**：密码位置填 Personal Access Token，不是 GitHub 登录密码。
6. **另一台机器跑不起来**：多半是缺 `requirements.txt`、`.env`、数据库，或 Python / Node 版本不一致。

---

需要的话，我可以帮你生成一份现成的 `.gitignore`、`.env.example` 和 `README.md` 三件套，直接放进项目根目录就能用。