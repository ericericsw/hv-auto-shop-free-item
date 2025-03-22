# import libary
import requests
import json
import time
import datetime
import re
import logging
import os
import configparser
import pytz
import sys
from typing import List, Dict, TypedDict
from bs4 import BeautifulSoup
import enum
# endregion

"""
better coments 格式
* 000
! 123
? 456
TODO 789
@param check_folder_path_exists 1234124
//415646464886


# logging.CRITICAL（50）
# logging.ERROR（40）
# logging.WARNING（30）
# logging.INFO（20）
# logging.DEBUG（10）
"""

# 指定時區
timezone = pytz.timezone('Asia/Taipei')

if getattr(sys, 'frozen', False):
    # 如果是打包後的可執行文件
    current_directory = os.path.dirname(sys.executable)
else:
    # 如果是未打包的原始腳本
    current_directory = os.path.dirname(os.path.abspath(__file__))
# 創建 ConfigParser 對象
config = configparser.ConfigParser()
# 讀取配置文件
config_path = os.path.join(current_directory, 'config.ini')
config.read(config_path, encoding="utf-8")

csv_folder_path = os.path.join(current_directory, 'csv')
log_folder_path = os.path.join(current_directory, 'log')
json_folder_path = os.path.join(current_directory, 'json')

# 檢查工作目錄是否有資料夾，沒有的話建立 log 資料夾
log_dir = os.path.join(current_directory, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    print(f"因資料夾不存在， 建立'{log_dir}' 資料夾。")

# 設置日誌
Log_Mode = config.get('Log', 'Log_Mode')
# 日誌格式
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
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


class CookieDict(TypedDict):
    ipb_member_id: str
    ipb_pass_hash: str
    ipb_session_id: str


class Forums_Code(enum.Enum):
    ORDERED_LIST_START: str = '[list=1]'
    ORDERED_LIST_END: str = '[/list]'
    UNORDERED_LIST_START: str = '[list]'
    UNORDERED_LIST_END: str = '[/list]'
    LIST_ITEM: str = '[*]'
    CODE_START: str = '[code]'
    CODE_END: str = '[/code]'
    BOLD_START: str = '[b]'
    BOLD_END: str = '[/b]'
    ITALIC_START: str = '[i]'
    ITALIC_END: str = '[/i]'
    UNDERLINE_START: str = '[u]'
    UNDERLINE_END: str = '[/u]'
    STRIKETHROUGH_START: str = '[s]'
    STRIKETHROUGH_END: str = '[/s]'
    MAIL_START: str = '[email]'
    MAIL_END: str = '[/email]'
    IMAGE_START: str = '[img]'
    IMAGE_END: str = '[/img]'
    QUOTE_START: str = '[quote]'
    QUOTE_END: str = '[/quote]'
    ALIGN_LEFT_START: str = '[left]'
    ALIGN_LEFT_END: str = '/[left]'
    ALIGN_CENTER_START: str = '[center]'
    ALIGN_CENTER_END: str = '[/center]'
    ALIGN_RIGHT_START: str = '[right]'
    ALIGN_RIGHT_END: str = '[/right]'
    INDENT_START: str = '[indent]'
    INDENT_END: str = '[/indent]'
    URL_END: str = '[/url]'
    TEXT_COLOR_END: str = '[/color]'
    TEXT_SIZE_END: str = '[/size]'
    NEWLINE: str = '\n'

    def URL_START(fqdn: str) -> str:
        return f'[url={fqdn}]'

    def TEXT_COLOR_START(text_color_code: str) -> str:
        return f'[color={text_color_code}]'

    def TEXT_SIZE_START(text_size: int) -> str:
        return f'[size={text_size}]'


def get_cookie() -> CookieDict:

    cookies = {}
    ipb_member_uid_value = config.get('Account', 'HV_Free_Shop_UID')
    ipb_pass_hash_value = config.get('Account', 'ipb_pass_hash')
    ipb_session_id_value = config.get('Account', 'ipb_session_id')

    cookies = {
        'ipb_member_id': ipb_member_uid_value,
        'ipb_pass_hash': ipb_pass_hash_value,
        'ipb_session_id': ipb_session_id_value
    }

    return cookies


class Forums():
    def __init__(self, cookies: CookieDict):
        """
        Forums相關功能初始化
        """
        self.forums = 'https://forums.e-hentai.org'
        self.cookies = cookies
        self.md5check = get_md5check(self.forums)

    def post_edit(self, thread_id: int, post_number: int, post_text) -> bool:
        """
        修改 post
        https://forums.e-hentai.org/index.php?showtopic={thread_id}

        """
        url = self.forums + '/index.php?showtopic=' + str(thread_id)
        post_id = get_post_id(url, post_number)
        url = "https://forums.e-hentai.org/index.php?s=&act=xmlout&do=post-edit-save&p={}&t={}&f=4".format(
            post_id, thread_id)

        data = {
            "md5check": self.md5check,
            "Post": post_text,
            # "t": thread_id,
            # "f": 4,  # ! 還不知道這是什麼
            # "p": post_id,
            # "act": 'xmlout',  # ! 還不知道這是什麼
            # "do": 'post-edit-save',
            # "std_used": '1&',
        }

        response = requests.post(url, data=data, cookies=self.cookies)

        if response.status_code == 200:
            return True
        else:
            logging.warning('error code:{},error message:{}'.format(
                response.status_code, response.text))
            return False


def get_post_id(url: str, post_number: int) -> str:
    """
    輸入帶thread_id的URL與Post Number，回傳Post ID

    input:
        url範例:https://forums.e-hentai.org/index.php?showtopic=257252
        post_number: #2 則輸入 2

    """

    if isinstance(post_number, int) and post_number > 0:

        url = url + '&st=' + str(post_number-1)

        # Send a GET request to the URL
        response = requests.get(url, cookies=get_cookie())

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the HTML content using BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all <a> tags with the specified title and href attributes
            post_links = soup.find_all(
                'a', title="Show the link to this post", href="#")

            # Dictionary to store the post numbers and their corresponding content
            posts = {}

            for link in post_links:
                # Extract the post id from the onclick attribute
                onclick_attr = link.get('onclick')
                post_id = onclick_attr.split('(')[1].split(')')[0]

                # Extract the main key (e.g., #1, #2, #3)
                main_key = link.text.strip().lstrip('#')

                # Store the post id and main key in the dictionary
                posts[main_key] = post_id

            # Print the results
            # for key, value in posts.items():
            #     print(f"{key}: {value}")

            return posts[str(post_number)]
        else:
            print(f"Failed to fetch the URL. Status code: {
                  response.status_code}")
    else:
        print(f"{post_number} Not an integer greater than 0")


def get_md5check(threrd_url: str) -> str:
    """
    取得threrd的md5check值
    """

    # Send a GET request to the URL
    response = requests.get(threrd_url, cookies=get_cookie())

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the script tag containing the ipb_md5_check variable
        script_tag = soup.find(
            'script', string=lambda t: t and 'var ipb_md5_check' in t)

        if script_tag:
            # Extract the JavaScript code
            script_content = script_tag.string

            # Find the value of ipb_md5_check
            start_index = script_content.find(
                'var ipb_md5_check') + len('var ipb_md5_check') + 3
            end_index = script_content.find(';', start_index) - 1
            ipb_md5_check = script_content[start_index:end_index].strip().strip(
                '"').strip('= "')

            # print(ipb_md5_check)
            return ipb_md5_check
        else:
            print("Script tag containing 'var ipb_md5_check' not found.")
    else:
        print(f"Failed to fetch the URL. Status code: {response.status_code}")


def check_post_lenght(threrd_url: str, post_number: int):
    """
    檢查當前 Post 長度

    TODO 還要做預測或門檻提醒機制
    """

    # 發送帶有 Cookie 的請求
    response = requests.get(str(threrd_url), cookies=get_cookie())

    if response.status_code == 200:
        # 獲取網頁內容，並手動轉乘 utf-8
        html_content = response.text.encode('ISO-8859-1').decode('utf-8')
        # print(response.encoding)
    else:
        print(f"Request failed. Status code: {response.status_code}")

    # 確認請求成功
    if response.status_code == 200:
        # 解析 HTML 內容
        soup = BeautifulSoup(response.content, 'html.parser')

        # 使用 id 抓取目標元素
        element = soup.find(
            id="post-{}".format(get_post_id(str(threrd_url), int(post_number))))

        print('===========================================================================')

        if element:
            # 取得目標元素的原始 HTML
            raw_html = element.prettify()  # 使用 prettify 讓 HTML 更易讀

            # 取得目標元素的純文字內容
            # text_content = element.get_text(strip=True)
            # print("\n純文字內容:")
            # print(text_content)

            # 計算字節大小
            size_in_bytes = len(raw_html.encode('utf-8'))  # 計算 UTF-8 編碼的字節大小
            # print(size_in_bytes)

            # 檢查是否超過 65531 bytes
            if size_in_bytes > 65531:
                print(f"內容超過上限！大小：{size_in_bytes} bytes、上限為65531")
            else:
                print(f"內容大小：{size_in_bytes} bytes，未超過上限、上限為65531。")
        else:
            print("無法找到目標元素。")

    else:
        print(f"無法請求該網址，狀態碼：{response.status_code}")


# def main():
    # post_test()
    # temp = get_md5check(
    #     "https://forums.e-hentai.org/index.php?showtopic=283538")
    # print(temp)
    # post_id = get_post_id(
    #     'https://forums.e-hentai.org/index.php?showtopic=283538', 2)
    # print(post_id)

    # test = Forums(get_cookie())
    # body = '1'
    # test.post_edit('284176', 2, body)

    # for i in range(1, 10):

    #     check_post_lenght(
    #         'https://forums.e-hentai.org/index.php?showtopic=273752', i)

    # check_post_lenght(
    #     "https://forums.e-hentai.org/index.php?showtopic=284176&st=0&gopid=6648772&#entry6648772", 2)

    # pass


"""
修改字串 170 byte (This post has been edited by ericeric91: Yesterday, 23:59)
\n 9byte
數字 1byte

"""


# if __name__ == "__main__":
#     main()
