from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import ddddocr
import base64

def ocr_captcha(driver, expected_length=4, max_attempts=5):
    """
    從驅動程式獲取驗證碼圖片並進行OCR識別
    
    Args:
        driver: Selenium webdriver實例
        expected_length: 預期的驗證碼長度，默認為4
        max_attempts: 最大嘗試次數，默認為5
    
    Returns:
        識別出的驗證碼文字
    """
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # 找到驗證碼圖片元素
            img_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "TicketForm_verifyCode-image"))
            )
            
            # 獲取圖片的src屬性值
            img_src = img_element.get_attribute("src")
            
            # 如果src是相對路徑，則轉換為完整URL
            if img_src.startswith("/"):
                base_url = driver.current_url.split("/ticket/")[0]
                img_src = base_url + img_src
            
            print(f"嘗試 {attempt+1}/{max_attempts} - 驗證碼圖片URL: {img_src}")
            
            # 使用webdriver直接獲取圖片內容，而不是使用requests
            # 這樣可以保持相同的會話和cookies
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])
            driver.get(img_src)
            
            # 使用JavaScript獲取圖片為base64
            img_base64 = driver.execute_script("""
                var canvas = document.createElement('canvas');
                var img = document.querySelector('img');
                if (!img) {
                    // 如果頁面上沒有img標籤，可能整個頁面就是一張圖片
                    return document.documentElement.outerHTML;
                }
                canvas.width = img.width;
                canvas.height = img.height;
                var ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                return canvas.toDataURL('image/png').split(',')[1];
            """)
            
            # 關閉圖片頁籤並切回主頁籤
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            
            if not img_base64 or "DOCTYPE" in img_base64:
                print("無法獲取圖片，嘗試重新刷新...")
                attempt += 1
                # 點擊驗證碼圖片刷新
                img_element.click()
                continue
            
            ocr = ddddocr.DdddOcr(beta=True)
            image = base64.b64decode(img_base64)

            # 儲存圖片到本地 (為了調試)
            with open(f"captcha_{attempt}.png", "wb") as f:
                f.write(image)
            print(f"已將驗證碼圖片存為 captcha_{attempt}.png")
            
            # 進行OCR識別
            result = ocr.classification(image)
            print(f"識別結果: {result}")
            
            # 檢查識別結果是否符合預期長度
            if len(result) == expected_length:
                print(f"成功識別完整驗證碼: {result}")
                return result
            else:
                print(f"識別結果長度不符 ({len(result)}/{expected_length})，刷新驗證碼...")
                # 點擊驗證碼圖片刷新
                img_element.click()
                attempt += 1
        
        except Exception as e:
            print(f"驗證碼識別過程發生錯誤: {e}")
            attempt += 1
            # 尝试刷新验证码
            try:
                img_element = driver.find_element(By.ID, "TicketForm_verifyCode-image")
                img_element.click()
            except:
                pass
    
    # 如果所有嘗試都失敗，返回最後一次的識別結果（可能不完整）
    print(f"達到最大嘗試次數 {max_attempts}，無法獲得完整驗證碼")
    return result if 'result' in locals() else ""