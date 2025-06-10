import logging
import requests
import time
import traceback
import json 
# 確保使用 Application 和 filters，不使用 Updater 或 Filters
from telegram.ext import Application, MessageHandler, filters 
from bs4 import BeautifulSoup as BS
from telegraph import Telegraph
import base64
import os
import re

################# 組態區 #################
# 注意：這裡的token我稍微修改了一下，請替換回你自己的真實token。
TELEGRAM_BOT_TOKEN = 'Token' # 請替換為您自己的 Bot Token
TELEGRAPH_SHORT_NAME = "nhentai_viewer_bot"
IMGBB_API_KEY = 'Token' # 請替換為您自己的 ImgBB API Key
IMGBB_API_URL = 'https://api.imgbb.com/1/upload'

# --- 日誌設定 ---
logging.basicConfig(
    level=logging.INFO, # 可以改成 logging.DEBUG 以獲取更詳細的日誌，方便除錯
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 通用請求頭部
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
}

############ 1. 從nhentai取得所有圖片的原始連結 ############
def get_nh_images(nh_url):
    logger.info(f"開始解析URL: {nh_url}")
    max_retries = 3
    timeout_duration = 30
    
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    
    # 提取漫畫ID 
    gallery_id_match = re.search(r'https?://nhentai\.net/g/(\d+)', nh_url) 
    gallery_id_from_url = gallery_id_match.group(1) if gallery_id_match else "unknown"
    
    # 加入Referer繞過防盜鏈
    referer = f"https://nhentai.net/g/{gallery_id_from_url}/"
    session.headers["Referer"] = referer
    
    image_urls = [] 

    for attempt in range(max_retries):
        try:
            logger.info(f"嘗試 {attempt+1}/{max_retries} 連接到 nhentai 主頁...")
            resp = session.get(nh_url, timeout=timeout_duration)
            
            if resp.status_code != 200:
                logger.error(f"請求主頁失敗，狀態碼: {resp.status_code}")
                return []
                
            logger.info("主頁請求成功，開始解析HTML內容以獲取頁數...")
            
            # 從JavaScript的window._gallery對象提取畫廊ID和頁數
            gallery_json_match = re.search(r"window\._gallery = JSON\.parse\(\"(.*?)\"\);", resp.text, re.DOTALL) 
            
            if gallery_json_match:
                escaped_json_string_raw = gallery_json_match.group(1).strip()
                try:
                    unescaped_json_string = escaped_json_string_raw.encode('latin1').decode('unicode_escape')
                except Exception as e:
                    logger.error(f"解轉義 Unicode 序列失敗: {e}")
                    unescaped_json_string = escaped_json_string_raw

                try:
                    gallery_data = json.loads(unescaped_json_string) 
                    gallery_id = gallery_data.get('id')
                    num_pages = gallery_data.get('num_pages')

                    if gallery_id is not None and num_pages is not None:
                        logger.info(f"從JavaScript的_gallery對象檢測到畫廊ID: {gallery_id}, 總頁數: {num_pages}")

                        # 遍歷每一頁的單頁預覽頁面
                        for i in range(1, num_pages + 1):
                            page_preview_url = f"https://nhentai.net/g/{gallery_id}/{i}/" 
                            logger.info(f"訪問單頁預覽頁面: {page_preview_url}")
                            
                            page_resp = session.get(page_preview_url, timeout=timeout_duration)
                            if page_resp.status_code == 200:
                                page_soup = BS(page_resp.text, 'html.parser')
                                
                                img_src = None
                                image_container_img = page_soup.select_one('#image-container img')
                                
                                if image_container_img:
                                    img_src = image_container_img.get('src') or image_container_img.get('data-src')
                                    if img_src:
                                        logger.info(f"在 #image-container 內找到圖片: {img_src}")
                                    else:
                                        logger.warning(f"在 #image-container 內找到 img 標籤，但沒有 src 或 data-src 屬性: {page_preview_url}")
                                else:
                                    logger.warning(f"在 {page_preview_url} 中找不到 #image-container 內部的圖片標籤。")

                                if img_src:
                                    if img_src.startswith('//'):
                                        img_src = 'https:' + img_src
                                    logger.info(f"獲取到原圖連結: {img_src}")
                                    image_urls.append(img_src)
                                else:
                                    logger.warning(f"在 {page_preview_url} 中無法獲取到有效圖片URL。")
                            else:
                                logger.error(f"請求單頁預覽頁面失敗，狀態碼: {page_resp.status_code} - {page_preview_url}")
                            time.sleep(0.1) # 訪問每個單頁之間稍微延遲
                        return image_urls
                    else:
                        logger.error("從_gallery對象中未能提取到有效的畫廊ID或總頁數。")
                        return [] 

                except json.JSONDecodeError as e:
                    logger.error(f"解析_gallery JSON數據失敗: {e}")
                    logger.error(f"嘗試解析的字串 (部分): {unescaped_json_string[:500]}...")
                    logger.error(traceback.format_exc())
                    return []
            else:
                logger.error("未能從主頁JavaScript中提取_gallery對象。")
                return []

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < max_retries - 1:
                logger.warning(f"連接超時，5秒後重試... (嘗試 {attempt+1}/{max_retries})")
                time.sleep(5)
                continue
            else:
                logger.error("已達到最大重試次數，放棄請求。")
                return []
                
        except Exception as e:
            logger.error(f"解析過程發生錯誤: {e}")
            logger.error(traceback.format_exc())
            return []
            
    return []

############ 2. 圖片下載函數 (帶防盜鏈繞過) ############
def download_image_with_retry(image_url, referer_url, max_retries=3):
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)
    session.headers["Referer"] = referer_url
    
    for attempt in range(max_retries):
        try:
            resp = session.get(image_url, timeout=20)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"圖片下載失敗 [嘗試 {attempt+1}]: HTTP {resp.status_code} - {image_url}")
        except requests.RequestException as e:
            logger.warning(f"圖片下載異常 [嘗試 {attempt+1}]: {str(e)}")
        
        if attempt < max_retries - 1:
            delay = 2 ** attempt
            logger.info(f"等待 {delay} 秒後重試")
            time.sleep(delay)
    
    logger.error(f"所有重試失敗: {image_url}")
    return None

############ 3. 將單張圖片上傳到ImgBB圖床 ############
def upload_to_imgbb(image_data):
    logger.info(f"準備上傳圖片 (大小: {len(image_data)/1024:.1f}KB)")
    
    try:
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        payload = {
            "key": IMGBB_API_KEY,
            "image": base64_image,
            "expiration": "0"
        }
        
        logger.info(f"開始上傳到ImgBB...")
        
        response = requests.post(
            IMGBB_API_URL,
            data=payload,
            headers=COMMON_HEADERS,
            timeout=60
        )
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get("success", False):
                img_url = json_data["data"]["url"]
                logger.info(f"圖片上傳成功: {img_url}")
                return img_url
            else:
                error_msg = json_data.get('error', {}).get('message', '未知錯誤')
                logger.error(f"ImgBB API返回錯誤: {error_msg}")
                return None
        else:
            logger.error(f"ImgBB上傳失敗，狀態碼: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"ImgBB上傳過程中發生異常: {e}")
        logger.error(traceback.format_exc())
        return None

############ 4. 建立Telegraph頁面 ############
def create_tele_page(title, img_urls):
    try:
        logger.info(f"正在建立Telegraph頁面: {title} ({len(img_urls)}張圖片)")
        tgph = Telegraph()
        tgph.create_account(
            short_name=TELEGRAPH_SHORT_NAME,
            author_name="NHBot"
        )
        
        html_content = ''
        for i, url in enumerate(img_urls):
            html_content += f'<figure><img src="{url}"/></figure>'
        
        response = tgph.create_page(
            title=title[:200],
            html_content=html_content,
            author_name="Nhentai Bot"
        )
        
        telegraph_url = "https://telegra.ph/" + response['path']
        logger.info(f"Telegraph頁面建立成功: {telegraph_url}")
        return telegraph_url
    except Exception as e:
        logger.error(f'創建Telegraph頁面失敗: {e}')
        logger.error(traceback.format_exc())
        return None

############ 5. 處理消息的主邏輯 ############
async def handle_message(update, context):
    original_user_message = update.message
    user = update.effective_user
    username = user.username if user else "未知用戶"
    
    try:
        text_msg = original_user_message.text.strip()
        logger.info(f"收到來自 {username} 的消息: {text_msg}")
        
        # 提取 nhentai 連結 (使用相同的正規表達式)
        nh_match = re.search(r'https?://nhentai\.net/g/(\d+)', text_msg)
        
        # 如果沒有找到 nhentai 連結，則直接返回，不執行後續處理
        if not nh_match:
            logger.info(f"消息不包含 nhentai 連結，跳過處理。")
            # 可以選擇回覆用戶，也可以選擇不回覆
            # await original_user_message.reply_text("我只處理nhentai漫畫連結喔！", parse_mode="Markdown")
            return
            
        gallery_id = nh_match.group(1)
        referer_url = f"https://nhentai.net/g/{gallery_id}/" 
        
        progress_message = await original_user_message.reply_text('🔍 已收到連結，開始解析漫畫頁面並獲取大圖...')
        
        start_time = time.time()
        final_image_urls = get_nh_images(referer_url) 
        
        if not final_image_urls:
            await progress_message.edit_text('❌ 解析失敗，無法獲取圖片連結。')
            return

        total_count = len(final_image_urls)
        initial_status_text = f'✅ 找到 {total_count} 張圖片，準備上傳到圖床...'
        await progress_message.edit_text(initial_status_text)
        
        imgbb_urls = []
        failed_count = 0

        progress_bar_length = 20 
        filled_char = '█'       
        empty_char = '░'        
        
        for i, img_url in enumerate(final_image_urls, 1):
            try:
                percentage = (i / total_count) * 100
                filled_chars_count = int(progress_bar_length * (i / total_count))
                
                if filled_chars_count == 0 and percentage > 0:
                    filled_chars_count = 1
                
                progress_bar = (filled_char * filled_chars_count).ljust(progress_bar_length, empty_char)
                
                status_text = (
                    f'⏳ 處理中：\n'
                    f'`[{progress_bar}] {percentage:.1f}% ({i}/{total_count})`\n' 
                )
                if failed_count > 0:
                    status_text += f'❌ 失敗: {failed_count}'
                
                await progress_message.edit_text(status_text, parse_mode="Markdown")
                
                image_data = download_image_with_retry(img_url, referer_url) 
                if not image_data:
                    logger.error(f"下載圖片 {img_url} 失敗，跳過上傳。")
                    failed_count += 1
                    continue
                
                uploaded_url = upload_to_imgbb(image_data)
                if uploaded_url:
                    imgbb_urls.append(uploaded_url)
                else:
                    failed_count += 1
                
                time.sleep(0.5)  
                
            except Exception as e:
                logger.error(f"處理圖片失敗: {e}")
                failed_count += 1
                status_text = (
                    f'⏳ 處理中：\n'
                    f'`[{progress_bar}] {percentage:.1f}% ({i}/{total_count})`\n'
                )
                status_text += f'❌ 失敗: {failed_count}' 
                await progress_message.edit_text(status_text, parse_mode="Markdown")
                time.sleep(0.5)
        
        elapsed = int(time.time() - start_time)
        if imgbb_urls:
            gallery_code = f"NH-{gallery_id}-{time.strftime('%H%M')}"
            telegraph_url = create_tele_page(gallery_code, imgbb_urls)
            
            if telegraph_url:
                result_message_text = (
                    f"🎉 完成！查看 [Telegraph]({telegraph_url})\n"
                    f"✅ 成功: {len(imgbb_urls)}/{total_count}\n"
                    f"❌ 失敗: {failed_count}\n"
                    f"⌛ 耗時: {elapsed}秒"
                )
                
                await context.bot.send_message(
                    chat_id=original_user_message.chat_id,
                    text=result_message_text,
                    parse_mode="Markdown",
                    reply_to_message_id=original_user_message.message_id 
                )

                try:
                    await progress_message.delete()
                    logger.info("進度條訊息已成功刪除。")
                except Exception as e:
                    logger.error(f"刪除進度條訊息失敗: {e}")
                    await progress_message.edit_text("✅ 圖片處理完成！")


            else:
                await progress_message.edit_text('❌ 創建Telegraph頁面失敗。')
        else:
            await progress_message.edit_text('❌ 所有圖片上傳失敗，請稍後再試。')
            
    except Exception as e:
        logger.error(f"處理過程出錯: {e}")
        logger.error(traceback.format_exc())
        await original_user_message.reply_text(f"❌ 處理錯誤: {str(e)}")

############ 6. 主程序入口 ############
if __name__ == "__main__":
    logger.info("啟動nhentai漫畫轉Telegram預覽機器人...")
    
    try:
        # 使用 Application.builder() 初始化機器人，這裡移除了 .arbitrary_callback_data(True)
        # 因為最新的 pytb 版本可能不需要它，且它曾引發 CallbackDataCache 錯誤
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build() 

        # 使用正則表達式過濾只包含 nhentai 連結的消息
        # filters.Regex 允許你指定一個正則表達式，只有匹配該表達式的消息才會被處理
        # 這裡我們使用 nh_match 的正則表達式來過濾
        nhentai_link_filter = filters.Regex(r'https?://nhentai\.net/g/\d+')
        application.add_handler(MessageHandler(filters.TEXT & nhentai_link_filter, handle_message))
        
        logger.info("機器人啟動完成，開始監聽消息...")
        application.run_polling()
    except Exception as e:
        logger.error(f"機器人啟動失敗: {e}")
        logger.error(traceback.format_exc())