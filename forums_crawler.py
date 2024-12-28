
# import libary
import requests
import re
import csv
from bs4 import BeautifulSoup
import time
from datetime import datetime, timedelta
import os
import logging
import pytz
import csv_tools
import forums_shop_main
import configparser
import sys
# endregion

# 創建 ConfigParser 對象
config = configparser.ConfigParser()

# 讀取配置文件
config.read('config.ini')

debug_mode = config.getboolean('Settings', 'debug_mode')
Check_Forums_URL = config.get('URLs', 'Check_Forums_URL')

'''
輸入論壇帖 URL，進行爬蟲
'''
# Check_Forums_URL = 'https://forums.e-hentai.org/index.php?showtopic=273276'
# debug_mode = True
# Max_Rental_Day = 7


# 指定時區
timezone = pytz.timezone('Asia/Taipei')

# 取得當前目錄
current_directory = os.path.dirname(os.path.abspath(__file__))
csv_directory = os.path.join(current_directory, 'csv')


# 檢查工作目錄是否有資料夾，沒有的話建立 log 資料夾
log_dir = os.path.join(current_directory, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    print(f"因資料夾不存在， 建立'{log_dir}' 資料夾。")

# Load configparser
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'config.ini')
config.read(config_path, encoding="utf-8")

# 設置日誌
Log_Mode = config.get('Log', 'Log_Mode')
Log_Format = '%(asctime)s %(filename)s %(levelname)s:%(message)s'  # 日誌格式
log_file_path = os.path.join(
    current_directory, 'log', 'sample.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


def get_cookie():

    cookies = {}
    ipb_member_id_value = config.get(
        'Account', 'HV_Equip_Rental_Shop_UID')
    ipb_pass_hash_value = config.get('Account', 'ipb_pass_hash')

    cookies = {
        'ipb_member_id': ipb_member_id_value,
        'ipb_pass_hash': ipb_pass_hash_value
    }

    return cookies


def get_item_suit_id():
    item_suit_id_list = []
    shop_order_setting_csv_path = os.path.join(
        csv_directory, 'free_shop_order_setting.csv')
    with open(shop_order_setting_csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            item_suit_id_list.append(row['item_suit_id'])
    return set(item_suit_id_list)


def get_last_post_number():
    """
    取得上次檢查的最後 Post Number
    """

    free_shop_last_post_csv_path = os.path.join(
        csv_directory, 'free_shop_last_post.csv')
    headers = ['Time', 'Last_Post_Number', 'Note']
    if not csv_tools.check_csv_exists(free_shop_last_post_csv_path, headers):
        new_data = {
            'Time': datetime.now().isoformat(),
            'Last_Post_Number': 5,
            'Note': ''
        }
        with open(free_shop_last_post_csv_path, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writerow(new_data)

    # 讀取 CSV 檔案，取得上次的 post_number
    last_post_number = 0
    try:
        with open(free_shop_last_post_csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            # 取得最後一行的 Last_Post_Number
            for row in reader:
                last_post_number = row.get('Last_Post_Number')

    except FileNotFoundError:
        pass

    # 確保 last_post_number 是整數並減 1
    if last_post_number:
        last_post_number = int(last_post_number) - 1
    else:
        last_post_number = 0

    return last_post_number


# 將檢查的最後一筆 Post Number 寫入 csv
def write_last_post_info(last_post_number: int):
    # 追加方式打開 CSV 檔案，將目前的 post_number 追加到後面
    current_directory = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(csv_directory, 'free_shop_last_post.csv')
    header = ['Time', 'Last_Post_Number', 'Note']
    csv_tools.check_csv_exists(file_path, header)
    # check_csv_exists(file_path, header)

    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        headers = reader.fieldnames

    # 寫入資料
    with open(file_path, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)

        writer.writerow({
            'Time': datetime.now().isoformat(),
            'Last_Post_Number': last_post_number,
            'Note': ''
        })

    logging.info('write last_post_number:{}'.format(last_post_number))


# 論壇分析爬蟲主體
def Forums_Respond_Segmentation(soup: BeautifulSoup):

    response_info_array = {}

    # 找到所有具有 class="borderwrap" 的 div 元素
    borderwrap_divs = soup.find_all('div', class_='borderwrap')

    # 遍歷每個<div class="borderwrap">
    for div in borderwrap_divs:
        # 提取序列編號
        post_number_tag = div.find(
            'a', onclick=lambda x: x and 'link_to_post' in x)
        if post_number_tag:
            # 取得 post 序號(#多少)
            post_number = post_number_tag.text.strip('#')

            # 初始化 post_number 的子字典
            response_info_array[post_number] = {}

            # 透過擷取 <a herf>，取得 post-id
            a_tag = div.find('a')
            onclick_value = a_tag['onclick']
            post_id_start = onclick_value.find('(') + 1
            post_id_end = onclick_value.find(')')
            post_id = onclick_value[post_id_start:post_id_end]

            # 提取 user-id 和 user-uid
            user_span = div.find('span', class_='bigusername')
            user_id = user_span.find('a').text
            user_uid = user_span.find('a')['href'].split('=')[-1]

            # 提取等級，提取失敗很可能是等級未超過顯示門檻，因此定義為0
            user_level = div.find(
                'div', {'style': 'float:left; text-align:left'})
            if user_level:
                user_level_text = user_level.get_text(strip=True)
                # 使用正規表達式提取數字部分
                match = re.search(r'Level\s+(\d+)', user_level_text)
                level_number = match.group(1)
            else:
                level_number = 0

            # 透過 Post-ID 提取原始回應
            response_content_raw = div.find(
                'div', class_='postcolor')

            # 提取文本內容，並以 <br> 為分隔符分割成多行
            response_content = response_content_raw.get_text('\n', strip=True)

            # 判斷編輯狀態
            post_edited_ststus = 'This post has been edited by' in response_content

            # 如果已經編輯過，複製編輯資訊至 post_edited_info，並在 response_content 移除相應字串
            post_edited_info = 'Null'
            if post_edited_ststus:
                edited_start = response_content.find(
                    'This post has been edited by')
                post_edited_info = response_content[edited_start:].strip()
                response_content = response_content[:edited_start].strip()

            response_info_array[post_number]['Post-ID'] = post_id
            response_info_array[post_number]['User-ID'] = user_id
            response_info_array[post_number]['User-UID'] = user_uid
            response_info_array[post_number]['response'] = response_content
            response_info_array[post_number]['post_edited_ststus'] = post_edited_ststus
            response_info_array[post_number]['post_edited_info'] = post_edited_info
            response_info_array[post_number]['User_Level'] = level_number

    return response_info_array


# 輸入網址進行論壇爬蟲
def Get_Forums_INFO(Forums_URL_Start: str):

    Forums_INFO = []

    current_post = get_last_post_number()
    logging.info('current_post:{}'.format(current_post))

    Post_Step = 20

    while True:

        current_url = f"{Forums_URL_Start}&st={current_post}"
        logging.info('Crawling page {} at {}'.format(
            current_post, Forums_URL_Start))

        # 發送帶有 Cookie 的請求
        response = requests.get(current_url, cookies=get_cookie())

        if response.status_code == 200:
            # 獲取網頁內容，並手動轉成 utf-8
            html_content = response.text.encode('ISO-8859-1').decode('utf-8')
        else:
            logging.critical('Request failed. Status code: {},error message:{}'.format(
                response.status_code, response.text))
            break

        soup = BeautifulSoup(html_content, 'html.parser')

        response_info = Forums_Respond_Segmentation(soup)
        if response_info:
            max_post_number = max(response_info, key=int)
            # 檢查頁面是否包含新的內容，如果沒有則停止爬取
            if int(max_post_number) < current_post:
                logging.info('No new content found. Stopping crawl. max_post_number is {}'.format(
                    max_post_number))
                write_last_post_info(max_post_number)
                break

            # 遍歷字典中的每一個鍵值對
            # for post_number, post_data in response_info.items():
            for post_number in response_info.keys():
                post_data = response_info[post_number]
                tempdata = {
                    'Post Number': post_number,
                    'Post ID': post_data['Post-ID'],
                    'User-ID': post_data['User-ID'],
                    'User-UID': post_data['User-UID'],
                    'User_Level': post_data['User_Level'],
                    'response': post_data['response'],
                    'post_edited_ststus': post_data['post_edited_ststus'],
                    'post_edited_info': post_data['post_edited_info']
                }
                Forums_INFO.append(tempdata)

            # 增加一些延遲，以免對目標網站造成過大的負擔
            time.sleep(1)

        current_post += Post_Step

    logging.info('Get_Forums_INFO:{}'.format(Forums_INFO))

    return Forums_INFO


def Get_Forums_Ticket():

    Ticket_Info = []
    Warning_Log = []
    Warning_Log_Temp = []

    Forums_INFO = Get_Forums_INFO(Check_Forums_URL)
    shop_order_setting_csv_path = os.path.join(
        csv_directory, 'free_shop_order_setting.csv')
    free_shop_order_setting_data = forums_shop_main.get_free_shop_order_setting(
        shop_order_setting_csv_path)

    # 用來儲存符合條件的數字和unit
    matching_numbers = []
    Order = {}

    # 第一筆資料前一次已處理，因此從第二筆資料開始檢查 response
    for item in Forums_INFO[1:]:
        response = item.get('response', '')  # 取得 response 的值
        User_ID = item.get('User-ID', '')  # 取得 User-ID 的值
        User_UID = item.get('User-UID', '')  # 取得 User-UID 的值
        User_Level = item.get('User_Level', '')  # 取得 User_Level 的值
        post_edited_ststus = item.get(
            'post_edited_ststus', '')  # 取得 post_edited_ststus 的值
        post_number = item.get('Post Number', '')  # 取得 post_number 的值
        Post_ID = item.get('Post ID', '')  # 取得 Post ID 的值

# --------------------------------------------------------------------------------
        # 使用 \n 分隔字段
        fields = response.split('\n')

        # 對每個字段進行處理
        for field in fields:

            # 使用正則表達式將所有類型的空白字符替換為單一空白字符
            field = re.sub(r'\s+', ' ', field)

            # 使用正則表達式將多個連續的空白字符替換為單一空白字符
            field = ' '.join(field.split())

            # 使用空格分隔字段中的兩個部分
            parts = field.split(' ')

            # *如果分隔後的部分數量不為1，可能是格式不正確的情況
            if len(parts) != 1:
                Warning_Log_Temp = {
                    'post_number': post_number,
                    'Post_ID': Post_ID,
                    'User_ID': User_ID,
                    'Input_Error_Type': 'Unrecognized-Format-Part-Not-1'
                }
                Warning_Log.append(Warning_Log_Temp)

            # *確認order在設定中
            elif not parts[0] in list(free_shop_order_setting_data.keys()):
                Warning_Log_Temp = {
                    'post_number': post_number,
                    'Post_ID': Post_ID,
                    'User_ID': User_ID,
                    'Input_Error_Type': 'Unrecognized-Format'
                }
                Warning_Log.append(Warning_Log_Temp)

            # *檢查是否為黑名單成員
            elif csv_tools.Get_Black_List_Reason_From_User_UID(User_UID):
                Warning_Log_Temp = {
                    'post_number': post_number,
                    'Post_ID': Post_ID,
                    'User_ID': User_ID,
                    'Input_Error_Type': 'On-List-User'
                }
                Warning_Log.append(Warning_Log_Temp)

            # 格式為1段的才執行判斷
            else:
                matching_numbers.append(
                    (post_number, Post_ID, User_ID, User_UID, User_Level, post_edited_ststus, parts[0]))

# --------------------------------------------------------------------------------

    matching_numbers_part2 = []
    for Match_Item in matching_numbers:
        post_number, Post_ID, User_ID, User_UID, User_Level, post_edited_ststus, parts = Match_Item

        # *檢查等級是否低於item-suit下限
        if int(User_Level) < free_shop_order_setting_data[parts]['item_suit_level_limit_min']:
            Warning_Log_Temp = {
                'post_number': post_number,
                'Post_ID': Post_ID,
                'User_ID': User_ID,
                'Input_Error_Type': 'Player-Level-Is-Lower-Than-Order-Require'
            }
            Warning_Log.append(Warning_Log_Temp)

        # *檢查等級是否超過item-suit上限
        elif int(User_Level) > free_shop_order_setting_data[parts]['item_suit_level_limit_max']:
            Warning_Log_Temp = {
                'post_number': post_number,
                'Post_ID': Post_ID,
                'User_ID': User_ID,
                'Input_Error_Type': 'Player-Level-Is-Higher-Than-Order-Require'
            }
            Warning_Log.append(Warning_Log_Temp)

        # *檢查order時間間隔
        elif not csv_tools.check_user_has_ticket_in_time_list(User_UID, free_shop_order_setting_data[parts]['item_suit_cold_time_day']):
            Warning_Log_Temp = {
                'post_number': post_number,
                'Post_ID': Post_ID,
                'User_ID': User_ID,
                'Input_Error_Type': 'Need-Wait-Cool-Time'
            }
            Warning_Log.append(Warning_Log_Temp)

        # *檢查編輯狀態
        elif not post_edited_ststus:
            Warning_Log_Temp = {
                'post_number': post_number,
                'Post_ID': Post_ID,
                'User_ID': User_ID,
                'Input_Error_Type': 'Already-Edited'
            }
            Warning_Log.append(Warning_Log_Temp)

        elif response in get_item_suit_id():
            matching_numbers_part2.append(
                (post_number, Post_ID, User_ID, User_UID, User_Level, post_edited_ststus, response))
        else:
            Warning_Log_Temp = {
                'post_number': post_number,
                'Post_ID': Post_ID,
                'User_ID': User_ID,
                'Input_Error_Type': 'Unknown-Error'
            }
            Warning_Log.append(Warning_Log_Temp)

    for Match_Item in matching_numbers_part2:
        post_number, Post_ID, User_ID, User_UID, User_Level, post_edited_ststus, response = Match_Item

        Ticket_No = csv_tools.add_free_shop_ticket(
            User_ID, User_UID, User_Level, response)
        Ticket_Temp = {
            'order_suit': response,
            'post_number': post_number,
            'User_ID': User_ID,
            'User_UID': User_UID,
            'User_Level': User_Level,
            'Ticket_No': Ticket_No
        }

        Ticket_Info.append(
            Ticket_Temp)

    logging.info('Ticket_Info:{}'.format(Ticket_Info))
    logging.warning('Warning_Log:{}'.format(Warning_Log))

    return Ticket_Info, Warning_Log


# 去除日期後綴函數
def clean_date_suffix(date_str):
    for suffix in ['st', 'nd', 'rd', 'th']:
        date_str = date_str.replace(suffix, '')
    return date_str


def get_user_id_history_latest(user_uid):

    current_url = 'https://forums.e-hentai.org/index.php?s=&act=profile&CODE=show-display-names&id={}'.format(
        user_uid)

    # 發送帶有 Cookie 的請求
    response = requests.get(current_url, cookies=get_cookie())

    if response.status_code == 200:
        # 獲取網頁內容，並手動轉乘 utf-8
        html_content = response.text.encode('ISO-8859-1').decode('utf-8')
    else:
        logging.warning(
            'Request failed. Status code: {response.status_code} error message:{response.text}')
        sys.exit()

    # 解析 HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # 提取表格資料
    table = soup.find('table', class_='ipbtable')
    rows = table.find_all('tr')[1:]  # 忽略標題列

    # 儲存結果
    results = []
    for row in rows:
        columns = row.find_all('td')
        from_name = columns[0].get_text(strip=True)
        to_name = columns[1].get_text(strip=True)
        change_date_str = clean_date_suffix(columns[2].get_text(strip=True))

        # 將時間轉換為 ISO 格式並儲存原始資料
        change_date_obj = datetime.strptime(
            change_date_str, '%d %B %Y - %H:%M')
        change_date_iso = change_date_obj.strftime('%Y-%m-%dT%H:%M:%S')

        results.append({
            'From': from_name,
            'To': to_name,
            'Change Date': change_date_iso
        })

    # 找到最新的一筆資料
    latest_record = max(results, key=lambda x: x['Change Date'])

    return latest_record
