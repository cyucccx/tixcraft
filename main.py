from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, TimeoutException

import time
import datetime
from selenium.webdriver.chrome.options import Options
from captcha import ocr_captcha

def wait_until_specific_time(sell_hour, sell_minute, sell_second):
    while True:
        # 获取当前时间
        now = datetime.datetime.now()
        
        # 设置目标时间
        target_time = now.replace(hour=sell_hour, minute=sell_minute, second=sell_second, microsecond=0)
        
        # 如果目标时间已经过去，则设置为第二天
        if now > target_time:
            target_time += datetime.timedelta(days=1)
        
        # 计算等待时间
        wait_seconds = (target_time - now).total_seconds()
        
        print(f"将在 {wait_seconds:.2f} 秒后启动脚本")
        time.sleep(wait_seconds)
        
        return  # 到达指定时间后退出函数

def get_ticket():

    #初始化
    sort_kind = 'y'  # 預設為優先購買便宜區域
    sell_hour, sell_minute, sell_second = 0, 0, 0

    # 輸入參數
    get_kind = input("請輸入搶票類型(1: 定時搶票, 2: 立馬搶票): ")
    have_seat = input("請輸入座位類型(1.指定價錢座位, 2.有座位就好(每次皆先嘗試一次指定座位)): ")
    change_activity = input("tixcraft活動名稱代號:")
    show_id = input("tixcraft 場次ID:")
    price_keywords = input("想要的票價關鍵字，以空格隔開(沒有請enter不要亂打，且請打正確不然會抓錯)(例如: 3225 4200 5600): ").strip().split()
    desired_ticket_count = int(input("想要購買的張數: "))  # 新增這行
    sort_kind = input("優先購買便宜區域?(從座位最下區域往上判斷)(預設: 是)(y/n): ")
    kick_price =  input("請輸入要排除的價錢(身障票價等，沒有請enter不要亂打)(預設偵測到身障相關字詞將排除)(例如: 3225 4200 5600): ").strip().split()
    account_cookie = input("請輸入帳號 cookie(SID): ")

    if get_kind == '1':
        sell_time = input("tixcraft 搶票時間(24小時制)(格式: HH:MM:SS): ")
        sell_hour, sell_minute, sell_second = map(int, sell_time.split(':'))

    #後續參數設置
    new_activity_url = f"https://tixcraft.com/ticket/area/{change_activity}/{show_id}"
    
    # 初始化 Selenium WebDriver
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://tixcraft.com')
    
    #登入操作
    print("原有的 cookies:")
    cookies = driver.get_cookies()
    for cookie in cookies:
        if cookie['name'] == 'SID':
            print(f"找到原有的 SID: {cookie['value']}")
    
    #刪除原有的 SID cookie
    driver.delete_cookie('SID')
    print("已刪除原有的 SID")
    
    # 加入 cookie
    driver.add_cookie({
        'name': 'SID',
        'value': account_cookie,
        'domain': '.tixcraft.com'
    })
    time.sleep(1)  # 等待 cookie 生效
    driver.get('https://tixcraft.com')
    time.sleep(1)  # 等待頁面載入

    
    #定時搶票
    if get_kind == '1':
        print(f"將在 {sell_hour:02}:{sell_minute:02}:{sell_second:02} 開始搶票")
        wait_until_specific_time(sell_hour, sell_minute, sell_second)
    driver.get(new_activity_url) #改活動名與訂票編號ID
    start_time = time.time()

    #刷票
    while True:
        try:
            #等待可能的回答頁面
            print(f"當前網址: {driver.current_url}")
            if "verify" in driver.current_url and "area" not in driver.current_url:
                time.sleep(1)  # 等待頁面載入
                while True:
                    # 偵測 alert（若有會拋出 NoAlertPresentException）
                    if "area" in driver.current_url:
                        print("✅ 成功進入票區頁面！")
                        break
                    
                    try:
                        alert = WebDriverWait(driver, 25).until(EC.alert_is_present())
                        alert.accept()
                        break
                    except NoAlertPresentException:
                        pass  # 沒有 alert，正常忽略

            # 找所有票區標籤
            print(1)
            zone_labels = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "zone-label"))
            )
            print(f"找到區域數: {len(zone_labels)}")

            # 反轉列表，從最便宜的區域開始檢查
            zone_labels.reverse()  

            # 排除指定的價錢與身障票價、視野瑕疵票價等
            BAD_KEYWORDS = ["身障", "身心障礙", "輪椅", "視野", "瑕疵", "視線"]
            kick_price = [p.strip() for p in kick_price if p.strip()]  # 移除空白與空字串
            filtered_zone_labels = []

            for zone_label in zone_labels:
                zone_price_text = zone_label.find_element(By.TAG_NAME, "b").text

                is_bad_price = any(price in zone_price_text for price in kick_price)
                is_bad_keyword = any(bad_word in zone_price_text for bad_word in BAD_KEYWORDS)

                if is_bad_price or is_bad_keyword:
                    print(f"🚫 排除區域: {zone_price_text}")
                    continue

                filtered_zone_labels.append(zone_label)

            zone_labels = filtered_zone_labels

            #想從貴的區域開始買
            if sort_kind.lower() == 'n':
                zone_labels.reverse()  


            # 優先檢查包含目標票價的區域
            found_seat = False
            for zone_label in zone_labels:
            # 先檢查包含關鍵字的區域
                for price_keyword in price_keywords:
                    try:
                        # 獲取票區標題
                        zone_title = zone_label.find_element(By.TAG_NAME, "b").text
                        print(f"檢查區域: {zone_title}")
                        
                        # 檢查是否包含目標票價關鍵字
                        if price_keyword in zone_title:
                            print(f"找到目標票價區域: {zone_title}")
                            target_zone_id = zone_label.get_attribute("data-id")
                            
                            # 找到對應的座位列表
                            seat_list = WebDriverWait(driver, 3).until(
                                EC.presence_of_element_located((By.ID, target_zone_id))
                            )
                            
                            # 從座位列表中找到所有 li 元素
                            all_li_elements = seat_list.find_elements(By.TAG_NAME, "li")
                            
                            # 篩選出有 class 屬性的 li 元素
                            clickable_li_elements = []
                            for li in all_li_elements:
                                if li.get_attribute("class"):  # 如果有 class 屬性
                                    clickable_li_elements.append(li)

                            if len(clickable_li_elements) > 0:
                                print(f"找到有 class 屬性的 li 元素數: {len(clickable_li_elements)}")
                                # 在 li 元素中尋找 a 標籤

                                max_remaining = -1
                                target_seat = None

                                for li in clickable_li_elements:
                                    try:
                                        font = li.find_element(By.TAG_NAME, "font")
                                        text = font.text  # e.g., "剩餘 18"
                                        remaining = int(text.strip().replace("剩餘", "").strip())

                                        if remaining > max_remaining:
                                            max_remaining = remaining
                                            target_seat = li
                                    except:
                                        continue  # 如果沒有 font 或格式錯誤就略過

                                a_tags = target_seat.find_elements(By.TAG_NAME, "a")
                                if len(a_tags) > 0:
                                    print("找到可點擊的座位")
                                    seat_to_click = a_tags[0]
                                    driver.execute_script("arguments[0].click();", seat_to_click)
                                    print("成功點擊座位")
                                    found_seat = True
                                
                                if found_seat:
                                    break
                            else:
                                print("該區域沒有可選座位，繼續檢查其他區域")
                    except Exception as e:
                        print(f"檢查區域時發生錯誤: {e}")
                        continue
            
            #如果沒找到目標票價的座位，直接買
            if not found_seat and have_seat == '2':
                for zone_label in zone_labels:
                    try:
                        zone_title = zone_label.find_element(By.TAG_NAME, "b").text
                        print(f"檢查區域: {zone_title}")
                        target_zone_id = zone_label.get_attribute("data-id")
                        
                        # 找到對應的座位列表
                        seat_list = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.ID, target_zone_id))
                        )
                        
                        # 從座位列表中找到所有 li 元素
                        all_li_elements = seat_list.find_elements(By.TAG_NAME, "li")
                        
                        # 篩選出有 class 屬性的 li 元素
                        clickable_li_elements = []
                        for li in all_li_elements:
                            if li.get_attribute("class"):  # 如果有 class 屬性
                                clickable_li_elements.append(li)
                        
                        if len(clickable_li_elements) > 0:
                            print(f"找到有 class 屬性的 li 元素數: {len(clickable_li_elements)}")
                            # 在 li 元素中尋找 a 標籤
                            for li in clickable_li_elements:
                                a_tags = li.find_elements(By.TAG_NAME, "a")
                                if len(a_tags) > 0:
                                    print("找到可點擊的座位")
                                    seat_to_click = a_tags[0]
                                    driver.execute_script("arguments[0].click();", seat_to_click)
                                    print("成功點擊座位")
                                    found_seat = True
                                    break
                            
                            if found_seat:
                                break
                        else:
                            print("該區域沒有可選座位，繼續檢查其他區域")
                    except Exception as e:
                        print(f"檢查倒數區域時發生錯誤: {e}")
                        continue
            
            if found_seat:
                break
            print("所有區域都沒有可選座位，重新嘗試中...")
            driver.refresh()
            
        except Exception as e:
            print(f"頁面處理時發生錯誤: {repr(e)}")

    
    try:
        if "verify" in driver.current_url and "ticket/ticket" not in driver.current_url:
                time.sleep(1)  # 等待頁面載入
                while True:
                    # 偵測 alert（若有會拋出 NoAlertPresentException）
                    if "ticket/ticket" in driver.current_url:
                        print("✅ 成功進入票區頁面！")
                        break
                    
                    try:
                        alert = WebDriverWait(driver, 25).until(EC.alert_is_present())
                        alert.accept()
                        break
                    except NoAlertPresentException:
                        pass  # 沒有 alert，正常忽略


        select_elements = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, "//select[starts-with(@id, 'TicketForm_ticketPrice')]"))
        )
        
        for select_element in select_elements:
            select = Select(select_element)
            options = select.options
            # 取得所有可選張數（排除 value="0"）
            available_counts = [int(opt.get_attribute("value")) for opt in options if opt.get_attribute("value").isdigit() and int(opt.get_attribute("value")) > 0]
            if not available_counts:
                continue
            max_count = max(available_counts)
            # 判斷是否足夠
            if desired_ticket_count in available_counts:
                select.select_by_value(str(desired_ticket_count))
                print(f"已選擇 {desired_ticket_count} 張")
            else:
                select.select_by_value(str(max_count))
                print(f"數量不足，已選擇最大可選張數 {max_count} 張")
            break
        
        agree_checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "TicketForm_agree"))
        )

        driver.execute_script("arguments[0].click();", agree_checkbox)
        
        input_box = driver.find_element(By.ID, 'TicketForm_verifyCode')
        input_box.click()
    except Exception as e:
        print(f"選擇張數或勾選同意時發生錯誤: {e}")

    captcha = ocr_captcha(driver)
    print(f"識別出的驗證碼: {captcha}")

    if len(captcha) == 4:
        # 填入驗證碼
        input_box = driver.find_element(By.ID, 'TicketForm_verifyCode')
        input_box.clear()
        input_box.send_keys(captcha)
        print(f"已填入驗證碼: {captcha}")


    submit_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                    )
    driver.execute_script("arguments[0].click();", submit_button)
    print("已點擊「確認張數」按鈕")
    end_time = time.time()
    print(f"共花費 {end_time - start_time:.2f} 秒")
    


    input("請在新頁面中完成支付，然後按 Enter 鍵結束腳本...")


get_ticket()