# Railgun 自动打卡

每天自动登录 [railgun.info](https://railgun.info/console/checkin) 并打卡。

## 环境要求

- Python 3.11+
- Windows（用于计划任务）
- QQ 邮箱 IMAP 授权码

## 快速开始

1. 安装依赖：
   ```bash
   uv sync
   ```
   或：
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. 复制配置模板并填写真实信息：
   ```bash
   cp .env.example .env
   ```
   编辑 `.env`：
   ```bash
   RAILGUN_EMAIL=your_railgun_email@example.com
   QQ_EMAIL=your_qq@qq.com
   QQ_AUTH_CODE=your_qq_imap_auth_code
   RUN_TIME=09:00
   ```

3. 手动运行一次，确认能成功打卡：
   ```bash
   uv run python checkin.py
   ```
   或（如果没有 uv）：
   ```bash
   .venv\Scripts\python.exe checkin.py
   ```

4. 安装 Windows 计划任务（需要以管理员身份运行 PowerShell）：
   ```powershell
   .\setup_task.ps1
   ```

## 配置说明

| 变量 | 说明 |
|------|------|
| `RAILGUN_EMAIL` | 你在 railgun 注册的邮箱 |
| `QQ_EMAIL` | 接收验证码的 QQ 邮箱 |
| `QQ_AUTH_CODE` | QQ 邮箱 IMAP 授权码（不是登录密码） |
| `RUN_TIME` | 每天自动打卡时间，默认 09:00 |

## 日志与截图

- 日志：`logs/checkin-YYYY-MM-DD.log`
- 截图：`screenshots/`

## 计划任务管理

- 查看任务：`Get-ScheduledTask -TaskName RailgunAutoCheckin`
- 删除任务：`Unregister-ScheduledTask -TaskName RailgunAutoCheckin -Confirm:$false`
