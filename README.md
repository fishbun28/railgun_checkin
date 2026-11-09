# Railgun 自动打卡

每天自动登录 [railgun.info](https://railgun.info/console/checkin) 并打卡。

## 环境要求

- Python 3.11+
- Windows（用于计划任务）
- QQ 邮箱 IMAP 授权码

## 快速开始

1. 安装依赖：
   ```bash
   uv venv --python 3.12
   uv pip install -r requirements.txt
   uv run playwright install chromium
   ```
   或（没有 uv）：
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

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `RAILGUN_EMAIL` | 你在 railgun 注册的邮箱 | — |
| `QQ_EMAIL` | 接收验证码的 QQ 邮箱 | — |
| `QQ_AUTH_CODE` | QQ 邮箱 IMAP 授权码（不是登录密码） | — |
| `RUN_TIME` | 每天自动打卡时间 | `09:00` |
| `IMAP_SERVER` | QQ 邮箱 IMAP 服务器地址 | `imap.qq.com` |
| `IMAP_PORT` | QQ 邮箱 IMAP 服务器端口 | `993` |

## 日志与截图

- 日志：`logs/checkin-YYYY-MM-DD.log`
- 截图：`screenshots/`，文件名为 `01_login_page_YYYYMMDD_HHMMSS_mmmmmm.png` 格式，带时间戳不会覆盖之前的运行结果
- 并发锁：`checkin.lock`（防止多实例同时运行，5 分钟后自动过期）

## 测试

运行单元测试：

```bash
uv run pytest tests/ -v
```

## 故障排查

- 如果提示 "Another instance is running"：检查是否有残留的 `checkin.lock` 文件，或等待 5 分钟后自动过期。
- 如果收不到验证码：检查 QQ 邮箱 IMAP 授权码是否正确，以及邮件是否被归入垃圾箱。
- 如果打卡失败：查看 `logs/` 日志和 `screenshots/` 截图。
- 如果日志出现 `Could not reach the login form`、`Login button not found`、`Checkin button not found`：说明站点改版、按钮文案或结构变了。`browser.py` 顶部的选择器常量（`SUBMIT_BUTTON`、`CHECKIN_BUTTON_GROUPS` 等）已同时兼容中英文多种文案（Login / Sign in / 登录 / 签到 …），此时把新文案补进去即可，不需要重写流程。
- 页面文案是英文还是中文不影响运行；结果判定同时匹配「今日已签到」「今天已打卡」「already checked in」等提示。

## 计划任务管理

以下命令都需要**管理员权限**的 PowerShell：

- 查看任务：`Get-ScheduledTask -TaskName RailgunAutoCheckin`
- 临时停用：`Disable-ScheduledTask -TaskName RailgunAutoCheckin`
- 重新启用：`Enable-ScheduledTask -TaskName RailgunAutoCheckin`
- 删除任务：`Unregister-ScheduledTask -TaskName RailgunAutoCheckin -Confirm:$false`
