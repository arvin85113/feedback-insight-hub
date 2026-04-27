# Feedback Insight Hub

以 Django 作為門面層，負責：

- 使用者驗證與角色分流
- 模板頁面與後台入口
- Django Admin 與帳號管理

以 Flask 作為 feedback domain 微服務，負責：

- 首頁統計摘要
- 顧客端回饋紀錄與通知列表
- 管理端儀表板彙整
- 問卷提交寫入
- 統計分析與文字分析 API

## 架構

- `accounts/`
  - Django 帳號、登入、偏好設定
- `feedback/`
  - Django façade views
  - 問卷建置與改善公告管理
  - Flask service client
- `services/feedback_service/`
  - Flask app
  - SQLAlchemy data access
  - feedback domain API

## 本機啟動

1. 安裝依賴

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. 初始化 Django

```bash
python manage.py migrate
python manage.py ensure_superuser
python manage.py seed_demo
```

3. 可選：啟動 Flask 微服務

```bash
python -m flask --app services.feedback_service.app run --host 127.0.0.1 --port 5001
```

4. 啟動 Django façade

```bash
python manage.py runserver
```

目前所有問卷都採登入後填答，沒有匿名或快速填答模式。
若未設定 `FEEDBACK_SERVICE_URL`，Django 會直接使用本地 provider，適合目前的 Django-only 開發或部署方式。
若設定 `FEEDBACK_SERVICE_URL`，Django 會優先呼叫 Flask 微服務；Flask 暫時不可用時，Django 仍會在短 timeout 後自動退回本地 provider，並在冷卻期間避免重複等待。

## 重要環境變數

```text
DJANGO_SECRET_KEY=replace-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DEFAULT_FROM_EMAIL=noreply@example.com
FEEDBACK_SERVICE_URL=http://127.0.0.1:5001
FEEDBACK_SERVICE_CONNECT_TIMEOUT=0.35
FEEDBACK_SERVICE_READ_TIMEOUT=0.8
FEEDBACK_SERVICE_FAILURE_COOLDOWN=30
```

## Render Blueprint

`render.yaml` 已拆成兩個 service：

- `feedback-insight-hub`: Django 對外 Web Service
- `feedback-domain-service`: Flask 私有服務

Django 透過內網 URL 呼叫 Flask 服務；兩者共用同一份 `DATABASE_URL`。
若只部署 Django，請不要設定 `FEEDBACK_SERVICE_URL`，系統會直接走 Django fallback。
