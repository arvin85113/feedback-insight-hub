# Feedback Insight Hub

以 Django 製作的「使用者回饋與統計分析平台」專題骨架，適合直接發布到 GitHub，並部署到 Render。

## 專題定位

這個版本把重點放在「平台」而不是單一問卷子系統：

- 前台分成正式登入介面與快捷收集介面
- 後台有角色登入與管理儀表板
- 問題建立時可先定義資料型態
- 依題目資料型態推薦後續統計分析方式
- 文字回饋可做關鍵字萃取、分類候選與質性整理
- 可建立產品改進追蹤通知，寄給同意追蹤的用戶

## 目前功能

- `accounts`
  - 客戶註冊
  - 客戶 / 管理人員角色區分
  - 登入 / 登出
- `feedback`
  - 問卷 `Survey`
  - 題目 `Question`
  - 回覆 `FeedbackSubmission` 與 `Answer`
  - 關鍵字分類 `KeywordCategory`
  - 改進追蹤 `ImprovementUpdate` / `ImprovementDispatch`
- 頁面
  - 首頁
  - 正式填答頁
  - 快捷收集頁
  - 後台儀表板
  - 改進通知建立頁

## 本機執行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

進入後台：

- Django Admin: `http://127.0.0.1:8000/admin/`
- 平台首頁: `http://127.0.0.1:8000/`

## 建議展示流程

1. 以 admin 建立一份問卷與數個題目
   或直接執行 `python manage.py seed_demo`
2. 其中數值題先標記為 `continuous` 或 `discrete`
3. 文字題勾選 `enable_keyword_tracking`
4. 以正式頁面或快捷頁面送出數筆回覆
5. 以管理者登入後台儀表板查看：
   - 描述性統計
   - 關鍵字分類候選
   - 每題適合的統計分析方式
6. 建立一筆改進追蹤通知，模擬後續寄信

## Render 部署

本專案已附：

- `requirements.txt`
- `build.sh`
- `render.yaml`
- `runtime.txt`

### Render 設定步驟

1. 把此資料夾初始化成 Git 專案並推上 GitHub
2. 到 Render 建立新的 Web Service
3. 連接 GitHub repository
4. Render 會自動讀取 `render.yaml`
5. 若要使用 PostgreSQL，於 Render 新增 PostgreSQL 並設定 `DATABASE_URL`

## 後續建議強化

- 加入真正的卡方檢定、T 檢定、相關分析模組
- 串接 `pandas`、`scipy`、`plotly`
- 產生實際文字雲圖片
- 增加 QRCode 產生功能
- 增加表單設計器 UI
- 增加 email 樣板與批次寄送紀錄
