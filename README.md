````markdown
# Nhentai 漫畫轉 Telegram 預覽機器人

這是一個 Telegram Bot，用於將 nhentai 漫畫轉換為 Telegraph 頁面，方便在 Telegram 內直接預覽。它會解析 nhentai 漫畫連結，下載所有圖片並上傳到 ImgBB 圖床，最後生成一個包含所有圖片的 Telegraph 頁面，並將連結回傳給用戶。

## 功能特色

* **自動解析 nhentai 連結**: 只需發送 nhentai 漫畫連結，機器人即可自動識別並處理。
* **多圖上傳支援**: 下載漫畫中的所有圖片。
* **可靠的圖片託管**: 將圖片上傳至 ImgBB 圖床以確保穩定性。
* **Telegraph 頁面生成**: 將所有圖片整合到一個美觀的 Telegraph 頁面中，方便預覽。
* **進度追蹤**: 在處理過程中提供即時進度更新。
* **錯誤處理**: 具備基本的錯誤處理和日誌記錄功能。

## 預覽

(您可以在這裡放置一個 Bot 實際運行效果的截圖或 GIF)

## 環境要求

* Python 3.8 或更高版本
* `pip` (Python 套件管理工具)
* 一個 Telegram Bot Token (從 [@BotFather](https://t.me/botfather) 獲取)
* 一個 ImgBB API Key (從 [ImgBB](https://imgbb.com/account/api) 獲取)

## 安裝步驟

**1. 建立並激活虛擬環境 (強烈推薦)**

為了避免套件衝突，建議為此專案建立一個獨立的虛擬環境。您可以選擇使用 `conda` 或 `venv`。

**使用 `conda` (推薦，如果已安裝 Anaconda 或 Miniconda):**

```bash
conda create -n nhtg_bot_env python=3.10
conda activate nhtg_bot_env
````

**使用 `venv` (Python 內建):**

```bash
python -m venv nhtg_bot_env
# Windows
.\nhtg_bot_env\Scripts\activate
# macOS/Linux
source nhtg_bot_env/bin/activate
```

**2. 安裝所需 Python 庫**

在激活的虛擬環境中，運行以下命令來安裝所有必要的庫：

```bash
pip install "python-telegram-bot[callback-data]>=20.0" requests beautifulsoup4 telegraph pytz
```

  * `"python-telegram-bot[callback-data]>=20.0"`: 核心 Telegram Bot 庫，包含處理回調數據的必要組件，並指定 v20 或更高版本。
  * `requests`: 用於發送 HTTP 請求。
  * `beautifulsoup4`: 用於解析網頁 HTML。
  * `telegraph`: 用於與 Telegraph API 互動。
  * `pytz`: 處理時區問題 (雖不直接使用，但作為 `APScheduler` 的間接依賴，建議安裝)。

**3. 配置您的 Bot**

打開 `nhtg_bot.py` 文件，並修改以下配置項：

```python
# 請替換為您自己的真實 Telegram Bot Token
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN' 
TELEGRAPH_SHORT_NAME = "nhentai_viewer_bot" # 您可以自定義這個短名稱
# 請替換為您自己的 ImgBB API Key
IMGBB_API_KEY = 'YOUR_IMGBB_API_KEY' 
```

  * 將 `YOUR_TELEGRAM_BOT_TOKEN` 替換為您從 [@BotFather](https://t.me/botfather) 獲得的 Bot Token。
  * 將 `YOUR_IMGBB_API_KEY` 替換為您從 [ImgBB](https://www.google.com/url?sa=E&source=gmail&q=https://imgbb.com/account/api) 獲取的 API Key。

## 運行 Bot

在完成配置後，確保您的虛擬環境已激活，然後運行：

```bash
python nhtg_bot.py
```

機器人將會啟動並開始監聽消息。

## 使用方法

1.  向您的 Telegram Bot 發送一個 nhentai 漫畫連結，例如：
    `https://nhentai.net/g/177013/`
2.  機器人將會開始處理，並發送進度更新消息。
3.  處理完成後，機器人會回覆一個包含 Telegraph 頁面連結的消息。點擊該連結即可在 Telegram 內直接預覽漫畫。

## 注意事項

  * 請勿濫用 ImgBB 或 Telegraph 服務。
  * 本程式碼僅供學習和個人使用，請遵守相關網站的使用條款。
  * 由於 nhentai 網站結構可能隨時變化，本程式碼可能需要定期維護和更新以保持其功能性。
  * 如果遇到 `RuntimeError: To use CallbackDataCache, PTB must be installed via pip install "python-telegram-bot[callback-data]"` 錯誤，請務必按照上述步驟重新執行 `pip install "python-telegram-bot[callback-data]>=20.0" ...` 命令，以確保正確安裝所有組件。

## 許可 (License)

(您可以選擇添加一個開源許可證，例如 MIT 許可證)

-----
