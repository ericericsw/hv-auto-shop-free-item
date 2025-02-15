import requests
import re
import csv
from bs4 import BeautifulSoup
import os
import configparser
import sys
import logging
from typing import List, Dict, TypedDict

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


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


# 設定 logging
Log_Mode = config.get('Log', 'Log_Mode')
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_directory, 'log', 'hv_mmlib.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])


class CookieDict(TypedDict):
    ipb_member_id: str
    ipb_pass_hash: str
    ipb_session_id: str


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


def Get_Equip_Level(soup):
    try:
        # 找到包含Level的<div>標籤，然後獲取其文字內容
        level_text = soup.text.split('Level')[1].strip()
        Equip_Level = level_text.split()[0]
        return Equip_Level
    except:
        return None


def Get_Equip_Category(soup):

    # 找到包含裝備類型的元素
    equip_Category_element = soup.find('div', class_='eq et')

    if equip_Category_element:
        # 從元素中取得裝備類型文本
        equip_Category = equip_Category_element.find(
            'div').text.strip().split()[0]
    else:
        equip_Category_element = soup.find('div', class_='eq es')
        equip_Category = equip_Category_element.find(
            'div').text.strip().split()[0]

    return equip_Category


def Get_Equip_Status_Tradable(soup):
    try:
        # 定位目標信息
        tradeable_span = soup.find('div', id='equip_extended').find(
            'span', string=lambda text: text and ('Tradeable' in text or 'Untradeable' in text))

        if tradeable_span:
            tradeable_status = tradeable_span.text
            return tradeable_status
    except:
        return None


def Get_Equip_Status_Upgrades(soup):
    upgrades_and_enchantments_div = soup.find(
        'div', string='Upgrades and Enchantments')

    if upgrades_and_enchantments_div:
        enchantments_span = upgrades_and_enchantments_div.find_next(
            'span', id='eu')

        if enchantments_span:
            enchantments_text = enchantments_span.text.replace(
                '   ', '、')  # 使用 replace 替換掉空行
            return enchantments_text
        else:
            enchantments_text = 'None'
            return enchantments_text
    else:
        print("Upgrades and Enchantments section not found.")


def Get_Equip_Status_IW(soup):
    IW_div = soup.find(
        'div', string='Upgrades and Enchantments')

    if IW_div:
        IW_span = IW_div.find_next(
            'span', id='ep')

        if IW_span:
            IW_text = IW_span.text.replace(
                '   ', '、')  # 使用 replace 替換掉空行
            return IW_text
        else:
            IW_text = 'None'
            return IW_text
    else:
        print("IW section not found.")


def Get_Equip_Status_Owner(soup):
    current_owner_element = soup.find(
        string=lambda string: string and 'Current Owner:' in string)

    if current_owner_element:
        # 獲取包含 "Current Owner:" 的元素之後的第一個 a 元素
        a_element = current_owner_element.find_next('a')

        if a_element:
            user_id = a_element.text
            urer_url = a_element['href']
            urer_uid = re.search(
                r'https://forums\.e-hentai\.org/index\.php\?showuser=(\d+)', urer_url).group(1)
            return user_id, urer_uid
        else:
            print("未找到 'Current Owner:' 後的 a 元素")
    else:
        print("未找到包含 'Current Owner:' 的元素")


def Get_Equip_Status_Name(soup):
    Name_div = soup.select('div.fc4.fac.fcb > div')
    result = ' '.join(div.get_text() for div in Name_div)

    # print('Name_div:', Name_div)
    # print('result:', result)
    return result


def Get_Equip_Status_Soulbound(soup):
    try:
        target_span = soup.select_one(
            '#equip_extended > div.eq.es > div:nth-child(1) > span')
        result = target_span.get_text()
        # print('target_span:', result)
        return result
    except:
        return None


def Get_Equip_Status(Equip_URL):

    # 發送帶有 Cookie 的請求
    response = requests.get(Equip_URL, cookies=get_cookie())

    if response.status_code == 200:
        # 獲取網頁內容
        html_content = response.text
    else:
        print(f"Request failed. Status code: {response.status_code}")

    # 使用Beautiful Soup解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    user_id, user_uid = Get_Equip_Status_Owner(soup)

    Equip_Level = Get_Equip_Level(soup)
    Equip_Category = Get_Equip_Category(soup)
    Equip_Status_Tradable = Get_Equip_Status_Tradable(soup)
    Equip_Status_IW = Get_Equip_Status_IW(soup)
    Equip_Status_Upgrades = Get_Equip_Status_Upgrades(soup)
    Equip_Name = Get_Equip_Status_Name(soup)
    Equip_Status_Soulbound = Get_Equip_Status_Soulbound(soup)

    if Equip_Status_Soulbound:
        Equip_Level = Equip_Status_Soulbound
        Equip_Status_Tradable = Equip_Status_Soulbound

    return Equip_Name, Equip_Level, Equip_Category, Equip_Status_Tradable, Equip_Status_IW, Equip_Status_Upgrades, user_id, user_uid
