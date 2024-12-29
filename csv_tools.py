# import libary
import csv
import os
import re
import datetime
import configparser
import shutil
import pytz
import logging
# endregion


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
Log_Format = '%(asctime)s | %(filename)s | %(funcName)s | %(levelname)s:%(message)s'
log_file_path = os.path.join(
    current_directory, 'log', 'csv_tools.log')
logging.basicConfig(level=getattr(logging, Log_Mode.upper()),
                    format=Log_Format,
                    handlers=[logging.FileHandler(log_file_path, 'a', 'utf-8'),
                              logging.StreamHandler()])


def check_folder_path_exists(folder_Path: os.path):
    if not os.path.exists(folder_Path):
        os.makedirs(folder_Path)
        logging.warning(f"資料夾 '{folder_Path}' 已建立。")


# 讀取配置文件
config.read('config.ini')
HV_Free_Shop_ID = config.get('Account', 'HV_Free_Shop_ID')
HV_Free_Shop_UID = config.get('Account', 'HV_Free_Shop_UID')


def check_csv_exists(file_path: os.path, default_headers: list):
    """
    檢查csv是否存在，不存在則寫入填入的預設欄位

    輸入:
        file_path:csv路徑
        default_headers:讀取的預設欄位
    """
    if not os.path.exists(file_path):
        check_folder_path_exists('csv')
        # 建立並寫入預設欄位到檔案
        with open(file_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(default_headers)
        logging.warning(f"檔案 '{file_path}' 不存在，已建立並寫入預設欄位 '{
                        default_headers}'。")
        return False
    else:
        return True


def Get_Black_List_Reason_From_User_UID(User_UID: int):
    """
    透過user_id來取得blck_list資訊
    """
    # 檔案路徑
    file_path = os.path.join(csv_directory,
                             'free_shop_black_list.csv')
    headers = ['Time', 'User_UID', 'Root_Cause']
    check_csv_exists(file_path, headers)

    events = []
    new_events = {}

    # 開啟 CSV 檔案
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # 逐行讀取 CSV 檔案中的資料
        for row in reader:
            if str(User_UID) == row['User_UID']:
                new_events = {
                    'Time': row['Time'],
                    'User_UID': row['User_UID'],
                    'Root_Cause': row['Root_Cause']
                }
                events.append(new_events)

    return events


def Get_User_From_Black_List():
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Black_List.csv')

    # 使用集合儲存使用者 ID，以排除重複的項目
    user_ids_set = set()
    user_uid_set = set()

    # 開啟 CSV 檔案
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # 逐行讀取 CSV 檔案中的資料
        for row in reader:
            # 將每一行的 User_ID 加入集合
            user_ids_set.add(row['User_ID'])
            user_uid_set.add(row['User_UID'])

    zipped = zip(user_ids_set, user_uid_set)
    # 將集合轉換回列表並返回
    return list(zipped)

# 追加黑名單紀錄


def Add_User_To_Black_List(User_ID, User_UID, Equip_ID, Equip_URL, Equip_Name, Root_Cause, Time=None):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Black_List.csv')

    # 如果未提供時間，則使用當前時間
    if Time is None:
        Time = datetime.datetime.now().isoformat()

    log_entry = [Time, User_ID, User_UID, Equip_ID,
                 Equip_URL, Equip_Name, Root_Cause]

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Time", "User_ID", "User_UID", "Equip_ID", "Equip_URL", "Equip_Name", "Root_Cause"])

        writer.writerow(log_entry)

    Write_Raw_Log('Benerate_Black_List', 'Write', log_entry)


class Check_Transaction():
    """
    進行備份、還原系統
    """

    def __init__(self):
        """
        初始化備份系統路徑
        """
        # 取得當前目錄
        self.current_directory = os.path.dirname(os.path.abspath(__file__))
        # csv 資料夾路徑
        self.csv_folder_path = os.path.join(self.current_directory, 'csv')
        # 檔案路徑
        self.file_path = os.path.join(
            self.csv_folder_path, 'Check_Transaction.csv')

        # csv_back 資料夾路徑
        self.csv_back_folder_path = os.path.join(
            self.current_directory, 'csv_back')
        check_folder_path_exists(self.current_directory)
        check_folder_path_exists(self.csv_back_folder_path)

        headers = ['Time', 'Start', 'End']
        check_csv_exists(self.file_path, headers)

        self.current_time = datetime.datetime.now().isoformat()

    def Start(self):
        """
        程式運作開始的標記
        """

        log_entry = [self.current_time, True, False]

        # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
        with open(self.file_path, mode='a', newline='') as csv_file:
            writer = csv.writer(csv_file)

            # 如果檔案是空的，就寫入欄位名稱
            if csv_file.tell() == 0:
                writer.writerow('Time', 'Start', 'End')

            writer.writerow(log_entry)

        logging.info('completion start tag')

    def End(self):
        """
        程式運作結束的標記
        """

        # 讀取 CSV 文件
        with open(self.file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # 讀取 CSV 文件內容
            csvreader = csv.DictReader(csvfile)

            # 將所有行存入一個列表
            rows = list(csvreader)

        # 如果有行資料，則修改最後一行的 'End' 值
        if rows:  # 檢查 rows 是否為空
            last_row = rows[-1]
            if last_row.get('Time') and last_row.get('Start') == 'True' and last_row.get('End') == 'False':
                last_row['End'] = 'True'

            # 將修改後的內容寫回 CSV 文件
            with open(self.file_path, 'w', newline='', encoding='utf-8') as csvfile:
                # 寫入 CSV 文件
                csvwriter = csv.DictWriter(
                    csvfile, fieldnames=csvreader.fieldnames)
                csvwriter.writeheader()
                csvwriter.writerows(rows)

        logging.info('completion end tag')

    def Check(self):
        """
        進行標記狀態檢查，
        retrun:
            若前一次有完整的開始與結束標記，則回應ture，沒有則回應false
        """

        # 讀取 CSV 文件
        with open(self.file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # 讀取 CSV 文件內容
            csvreader = csv.DictReader(csvfile)

            # 將所有行存入一個列表
            rows = list(csvreader)

        if not rows:
            logging.info('Check (No data, returning True)')
            return True

        # 檢查是否有行
        if rows:
            last_row = rows[-1]
            # 使用 get 方法安全地獲取值，提供默認值
            if last_row.get('Time'):
                if last_row.get('Start') == 'True':
                    if last_row.get('End') == 'True':
                        # 有開始有結束，則回傳 True
                        logging.info('tag check pass')
                        return True
                    elif last_row.get('End') == 'False':
                        # 有開始沒有結束，則回傳 False
                        logging.warning('tag check fail')
                        return False

        logging.info('Perform start/end tag checks')

    def Backup(self):
        """
        進行備份
        """
        # 取得來源資料夾中的所有檔案
        files = os.listdir(self.csv_folder_path)
        exclude_file = [
            'Check_Transaction.csv',
        ]

        # 遍歷所有檔案，排除指定檔案，進行複製
        for file in files:
            if file not in exclude_file and file.endswith('.csv'):
                source_path = os.path.join(self.csv_folder_path, file)
                destination_path = os.path.join(
                    self.csv_back_folder_path, file)
                shutil.copyfile(source_path, destination_path)

        logging.info('Backup Finish')

    def Rollback(self):
        # 取得來源資料夾中的所有檔案
        files = os.listdir(self.csv_back_folder_path)

        for file in files:
            source_path = os.path.join(self.csv_back_folder_path, file)
            destination_path = os.path.join(self.csv_folder_path, file)
            shutil.copyfile(source_path, destination_path)

        logging.warning('Rollback Finish')


# 檢查"已入黑單的通知信"是否發過
def Check_Ticket_Expire_Notification3(Ticket_No: str):

    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Ticket_Expire_Notification3.csv')

    Check_Switch = False

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        # 建立 CSV 讀取器
        csv_reader = csv.DictReader(csv_file)

        # 遍歷每一行
        for row in csv_reader:
            # 檢查 Equip_URL 是否存在於該行
            if row['Ticket_No'] == str(Ticket_No):
                Check_Switch = True

    return Check_Switch


# 已入黑單的通知信
def Tag_Ticket_Expire_Notification3(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Ticket_Expire_Notification3.csv')

    log_entry = [Ticket_No]

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Ticket_No"])

        writer.writerow(log_entry)

    Write_Raw_Log('Tag_Ticket_Expire_Notification3', 'Add', log_entry)


# 檢查"黑單剩下一天的通知信"是否發過
def Check_Ticket_Expire_Notification2(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Ticket_Expire_Notification2.csv')

    Check_Switch = False

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        # 建立 CSV 讀取器
        csv_reader = csv.DictReader(csv_file)

        # 遍歷每一行
        for row in csv_reader:
            # 檢查 Equip_URL 是否存在於該行
            if row['Ticket_No'] == str(Ticket_No):
                Check_Switch = True

    return Check_Switch


# 黑單剩下一天的通知信
def Tag_Ticket_Expire_Notification2(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Ticket_Expire_Notification2.csv')

    log_entry = [Ticket_No]

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Ticket_No"])

        writer.writerow(log_entry)

    Write_Raw_Log('Tag_Ticket_Expire_Notification2', 'Add', log_entry)


# 檢查"剩下一天的通知信"是否發過
def Check_Ticket_Expire_Notification(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Ticket_Expire_Notification.csv')

    Check_Switch = False

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        # 建立 CSV 讀取器
        csv_reader = csv.DictReader(csv_file)

        # 遍歷每一行
        for row in csv_reader:
            # 檢查 Equip_URL 是否存在於該行
            if row['Ticket_No'] == str(Ticket_No):
                Check_Switch = True

    return Check_Switch


# 剩下一天的通知信紀錄
def Tag_Ticket_Expire_Notification(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Ticket_Expire_Notification.csv')

    log_entry = [Ticket_No]

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Ticket_No"])

        writer.writerow(log_entry)

    Write_Raw_Log('Tag_Ticket_Expire_Notification', 'Add', log_entry)


# 回傳開啟中的 Ticket 資訊
def Get_Opening_Ticket():
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')
    Ticket_Info = {}
    Ticket_No_list = []

    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 迭代每一行
        for row in csv_reader:
            # 檢查 Ticket_Status 是否符合目標
            if row['Ticket_Status'] == 'Open':
                Ticket_No = row['Ticket_No']
                Ticket_No_list.append(Ticket_No)
                Ticket_Info[Ticket_No] = {}
                Ticket_Info[Ticket_No]['User_ID'] = row['User_ID']
                Ticket_Info[Ticket_No]['User_UID'] = row['User_UID']
                Ticket_Info[Ticket_No]['Rental_Date'] = row['Rental_Date']
                Ticket_Info[Ticket_No]['Expiry_Date'] = row['Expiry_Date']
                Ticket_Info[Ticket_No]['Equip_ID'] = row['Equip_ID']
                Ticket_Info[Ticket_No]['Equip_URL'] = row['Equip_URL']

    return Ticket_No_list, Ticket_Info


# 紀錄 MM 中的裝備的領取時間紀錄
def Add_MM_Take_Date(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    # 取得當前時間
    current_time = datetime.datetime.now().isoformat()

    # 檢查檔案是否存在
    if os.path.exists(file_path):
        # 開啟檔案，使用 'r+' 模式
        with open(file_path, 'r+', newline='') as file:
            # 建立 CSV 讀寫物件
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames

            # 找到指定 Ticket_No 的行
            rows = list(reader)
            for row in rows:
                if row['Ticket_No'] == str(Ticket_No):
                    # 追加時間資訊
                    row['MM_Take_Date'] = current_time
                    break

            # 將檔案指標移至開頭，清空檔案內容
            file.seek(0)
            file.truncate()

            # 寫入標題行
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            # 寫入新的資料
            writer.writerows(rows)

        print(f"已為Ticket_No {Ticket_No} 追加 MM_Take_Date 資訊：{current_time}")

        # 記錄操作
        Write_Raw_Log('Add_MM_Take_Date', 'Edit', Ticket_No)

    else:
        print(f"檔案 {file_path} 不存在。")


# 回傳 MM 未收清單
def Get_In_MM_Ticket_List():
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_In_MM_List.csv')

    In_MM_List = []

    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 遍歷每一列，並列印 'Ticket_No' 欄位的值
        for row in csv_reader:
            In_MM_List.append(row['Ticket_No'])

        return In_MM_List


def Untag_In_MM_Ticket(Ticket_No):
    """
    移除 MM 還沒收的 Ticket_No 標記
    """
    # 檔案路徑
    file_path = os.path.join(csv_directory,
                             'HV_Equip_In_MM_List.csv')
    temp_file_path = os.path.join(csv_directory,
                                  'HV_Equip_In_MM_List_temp.csv')

    # 開啟 CSV 檔案，讀取資料，並在暫存文件中寫入不包含指定 Ticket_No 的行
    with open(file_path, mode='r', newline='') as csv_file, \
            open(temp_file_path, mode='w', newline='') as temp_csv_file:

        reader = csv.reader(csv_file)
        writer = csv.writer(temp_csv_file)

        # 寫入欄位名稱
        writer.writerow(next(reader))

        # 查找指定 Ticket_No，並跳過這一行
        for row in reader:
            if row[0] != str(Ticket_No):
                writer.writerow(row)

    # 將暫存文件覆蓋原始 CSV 文件
    os.replace(temp_file_path, file_path)

    # 記錄移除操作
    logging.info('untag Ticket_No:{}'.format(Ticket_No))


def Tag_In_MM_Ticket(Ticket_No):
    """
    標記 MM 還沒收的 Ticket_No
    """
    # 檔案路徑
    file_path = os.path.join(csv_directory,
                             'HV_Equip_In_MM_List.csv')

    log_entry = [Ticket_No]

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Ticket_No"])

        writer.writerow(log_entry)

    logging.info('tag Ticket_No:{}'.format(Ticket_No))


# 透過裝備網址取得當前租借者UID
def get_user_uid_from_equip_url(equip_url):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip.csv')
    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 迭代每一行
        for row in csv_reader:
            # 檢查 Ticket_No 是否符合目標
            if row['Equip_URL'] == equip_url:
                Equip_Current_Owner_UID = row['Equip_Current_Owner_UID']
    return Equip_Current_Owner_UID


# 透過 Ticket No 取得過期時間
def Get_Expiry_Date_From_Ticket_No(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    # 設定預設值
    Expiry_Date = None

    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 迭代每一行
        for row in csv_reader:
            # 檢查 Ticket_No 是否符合目標
            if row['Ticket_No'] == Ticket_No:
                Expiry_Date = row['Expiry_Date']

    return Expiry_Date


# 從 Ticket List 透過 User_ID 查詢 User_UID
def Get_User_UID_From_User_ID(User_ID, ticket_number):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 迭代每一行
        for row in csv_reader:
            # 檢查 User_ID 是否符合目標
            if row['User_ID'] == User_ID:
                if row['Ticket_No'] == ticket_number:
                    User_UID = row['User_UID']

    return User_UID


# 檢查灰名單 Counter 狀態，2 周內超過 5 分回 False
def Get_Grey_List_Pass_Check(User_UID):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Grey_List.csv')

    # 設定閾值和時間範圍
    threshold_score = 5
    time_range = datetime.timedelta(weeks=2)

    # 設定 Reason_Type 的權重
    reason_weights = {
        "輕微": 1,
        "中等": 2,
        "嚴重": 3,
        "Critical_Expiry": 10,
        "Equip_RTS": 1
    }

    total_score = 0
    current_time = datetime.datetime.now()

    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['User_UID'] == str(User_UID):
                    record_time = datetime.datetime.strptime(
                        row['Time'], '%Y-%m-%dT%H:%M:%S.%f')
                    if current_time - record_time <= time_range:
                        reason_type = row['Reason_Type']
                        weight = reason_weights.get(
                            reason_type, 1)  # 如果沒有對應的權重，默認為 1
                        total_score += weight

    except FileNotFoundError:
        print(f"找不到文件：{file_path}")
        Write_Raw_Log('Get_Grey_List_Pass_Check', 'Check',
                      'file not found:{}'.format(file_path))
        return True
    except Exception as e:
        print(f"讀取文件時發生錯誤：{e}")
        Write_Raw_Log('Get_Grey_List_Pass_Check',
                      'Check', 'error code:{}'.format(e))
        return True

    return total_score <= threshold_score


# 對 BOT 發送 CoD
def Equip_MM_CoD_Counter_Add(User_ID, User_UID, Ticket_No, Time=None):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Grey_List.csv')

    # 如果未提供時間，則使用當前時間
    if Time is None:
        Time = datetime.datetime.now().isoformat()

    log_entry = [Time, User_ID, User_UID, Ticket_No, 'Send_CoD']

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Time", "User_ID", "User_UID", "Ticket_No", "Reason_Type"])

        writer.writerow(log_entry)

    Write_Raw_Log('Equip_MM_CoD_Counter_Add', 'Write', log_entry)


# 無故退回裝備之紀錄
def Equip_MM_RTS_Counter_Add(User_ID, User_UID, Ticket_No, Time=None):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Grey_List.csv')

    # 如果未提供時間，則使用當前時間
    if Time is None:
        Time = datetime.datetime.now().isoformat()

    log_entry = [Time, User_ID, User_UID, Ticket_No, 'Equip_RTS']

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Time", "User_ID", "User_UID", "Ticket_No", "Reason_Type"])

        writer.writerow(log_entry)

    Write_Raw_Log('Equip_MM_RTS_Counter_Add', 'Write', log_entry)


# 透過 User_UID 取得 Open 狀態的 Ticket 數量
def Get_Open_Ticket_Count_From_User_UID(User_UID):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 初始化計數器
        count = 0

        # 迭代每一行
        for row in csv_reader:
            # 檢查 User_UID 是否符合目標
            if row['User_UID'] == User_UID:
                if row['Ticket_Status'] == 'Open':
                    count += 1

    return count


# 用於記錄異常歸還紀錄
def Add_Error_Return_Log(Ticker_No, Ticket_Owner, Input_Error_Type, Time=None):
    '''
    Abnormal-Return
    Critically-Expired
    MM-Not-Received
    '''

    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Error_Return_Log.csv')

    # 建立 CSV 檔案夾，如果不存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 如果未提供時間，則使用當前時間
    if Time is None:
        Time = datetime.datetime.now().isoformat()

    log_entry = [Time, Ticker_No, Ticket_Owner, Input_Error_Type]

    Write_Raw_Log('Add_Error_Return_Log', 'write', log_entry)

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Time", "Ticker_No", "Ticket_Owner", "Input_Error_Type"])

        writer.writerow(log_entry)


# 用於記錄錯誤的 Ticket
def Add_Error_Ticket_Log(Post_Number, Post_ID, User_ID, Input_Error_Type, Time=None):
    '''
    type list:
        Unrecognized-Format-Part-Not-1:回應是多段的字詞
        Too-Many-Order:order數量超過限制
        Need-Wait-Cool-Time:還沒長於cooltime
        Player-Level-Is-Higher-Than-Order-Require:等於高於item_suit要求等級
        Player-Level-Is-Lower-Than-Order-Require:等於低於item_suit要求等級
        Unrecognized-Format:錯誤格式
        Already-Edited:編輯過
        On-List-User:黑名單
        Unknown-Error:還沒定義的錯誤
    '''

    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Error_Ticket_Log.csv')

    # 建立 CSV 檔案夾，如果不存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 如果未提供時間，則使用當前時間
    if Time is None:
        Time = datetime.datetime.now().isoformat()

    log_entry = [Time, Post_Number, Post_ID,
                 User_ID, Input_Error_Type]

    # Write_Raw_Log('Add_Error_Ticket_Log', 'write', log_entry)
    logging.warning('Add_Error_Ticket_Log Post_Number:{}'.format(Post_Number))

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(
                ["Time", "Post_Number", "Post_ID", "User_ID", "Input_Error_Type"])

        writer.writerow(log_entry)


# 用於 Ticket 建立後發貨處理
def Equip_MM_Send_Archiving(User_ID, User_UID, Equip_URL, Expiry_Date):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv', 'HV_Equip.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)
            rows = list(csv_reader)

        # 找到 Equip_URL 對應的索引
        index_to_modify = None
        for i, row in enumerate(rows):
            if row['Equip_URL'] == Equip_URL:
                index_to_modify = i
                break

        if rows[index_to_modify]['Equip_URL'] == Equip_URL:
            if rows[index_to_modify]['Rental_Status'] == 'Free':
                if index_to_modify is not None:
                    # 修改找到的資訊
                    rows[index_to_modify]['Equip_Current_Owner_ID'] = User_ID
                    rows[index_to_modify]['Equip_Current_Owner_UID'] = User_UID
                    rows[index_to_modify]['Rental_Status'] = 'Rental'
                    rows[index_to_modify]['Expiry_Date'] = Expiry_Date

                    # 將修改後的資訊寫回 CSV 檔案
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = csv_reader.fieldnames
                        csv_writer = csv.DictWriter(
                            csvfile, fieldnames=fieldnames)

                        # 寫入標題
                        csv_writer.writeheader()

                        # 寫入所有資料，包括修改後的那一行
                        csv_writer.writerows(rows)

                    # print(f"成功修改 Equip_URL {Equip_URL} 的資訊")
                    Write_Raw_Log('Equip_MM_Receive_Archiving_Check_Found',
                                  'Checking', f"Check Ticket Equip_URL {Equip_URL}")
                    return True

        else:
            print(f"Equip_URL {Equip_URL} 未找到相應的資訊")
            return {'Archiving_Pass': 'False'}

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# 輸入 Equip ID 確認租借狀態
def Get_Equip_Rental_Status_And_Deposit_From_Equip_ID(Equip_ID):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)

            # 遍歷每一行
            for row in csv_reader:
                # 檢查 Equip_ID 是否存在於該行
                if row['Equip_ID'] == Equip_ID:
                    # 回傳 Rental_Status
                    return {
                        'Check_Pass': 'True',
                        'Rental_Status': row['Rental_Status'],
                        'Deposit': row['Deposit'],
                        'Equip_URL': row['Equip_URL'],
                        'Equip_Level': row['Equip_Level'],
                        'Equip_Current_Owner_ID': row['Equip_Current_Owner_ID']
                    }

        # 如果迴圈結束仍未找到，顯示找不到的訊息
        # print(f"Equip with URL {Equip_URL} not found in the CSV file.")
        return {
            'Check_Pass': 'False'
        }

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def Get_Equip_Name_By_Equip_ID(Equip_ID):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip.csv')

    Equip_Name = None

    # 讀取 CSV 檔案
    with open(file_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)

        # 迭代每一行
        for row in csv_reader:
            # 檢查 Equip_ID 是否符合目標
            if row['Equip_ID'] == Equip_ID:
                Equip_Name = row['Equip_Name']

    return Equip_Name


def Get_Equip_ID_From_URL(equip_url):
    # 使用正則表達式從 Equip_URL 中提取 Equip_ID
    pattern = re.compile(r'/equip/(\d+)/')
    match = pattern.search(equip_url)

    if match:
        equip_id = match.group(1)
        return equip_id
    else:
        return None


# 用於寫未處理通用 log
def Write_Raw_Log(Def_Name, Action, Raw_Log, Time=None):
    # 如果未提供時間，則使用當前時間
    if Time is None:
        Time = datetime.datetime.now().isoformat()

    log_entry = [Time, Def_Name, Action, Raw_Log]

    # 跨平台的檔案路徑
    csv_file_path = os.path.join("csv", "raw_log.csv")

    # 建立 CSV 檔案夾，如果不存在
    os.makedirs(os.path.dirname(csv_file_path), exist_ok=True)

    # 開啟 CSV 檔案，如果不存在就建立新檔案，並寫入資料
    with open(csv_file_path, mode='a', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # 如果檔案是空的，就寫入欄位名稱
        if csv_file.tell() == 0:
            writer.writerow(["Time", "Def_Name", "Action", "Raw_Log"])

        writer.writerow(log_entry)


# 確認 RTS 內容是否為訂單內容
def Equip_MM_Receive_RTS_Check(User_ID, Equip_URL):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)

            # 遍歷每一行
            for row in csv_reader:
                # 檢查 Equip_URL 是否存在於該行
                if row['Equip_URL'] == Equip_URL:

                    # 比對確認 User_ID 與 User_ID 是否一致
                    if User_ID == row['User_ID']:

                        # 比對確認 Ticket_Status 狀態為 Open
                        if row['Ticket_Status'] == 'Open':
                            # 如果找到，回傳檢查狀態，並傳回 Ticket_No
                            return {
                                'Check_Pass': 'True',
                                'Ticket_No': row['Ticket_No'],
                                'User_UID': row['User_UID']
                            }

        # 如果迴圈結束仍未找到，顯示找不到的訊息
        # print(f"Equip with URL {Equip_URL} not found in the CSV file.")
        return {
            'Check_Pass': 'False'
        }

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# 輸入 Ticket_No 得知並回傳 Equip_URL
def Get_Equip_URL_By_Ticket_No(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)

            # 遍歷每一行
            for row in csv_reader:
                # 檢查 Ticket_No 是否存在於該行
                if row['Ticket_No'] == str(Ticket_No):
                    return row['Equip_URL']

        # 如果迴圈結束仍未找到，顯示找不到的訊息
        # print(f"Equip with URL {Equip_URL} not found in the CSV file.")
        return {
            'Check_Pass': 'False'
        }

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# 輸入 Ticket_No 得知並回傳 User_ID
def Get_Ticket_User_ID_By_Ticket_No(Ticket_No):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv',
                             'HV_Equip_Shop_Ticket.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)

            # 遍歷每一行
            for row in csv_reader:
                # 檢查 Ticket_No 是否存在於該行
                if row['Ticket_No'] == str(Ticket_No):
                    return row['User_ID']

        # 如果迴圈結束仍未找到，顯示找不到的訊息
        # print(f"Equip with URL {Equip_URL} not found in the CSV file.")
        return {
            'Check_Pass': 'False'
        }

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# 用於檢查收到的 MM 中的裝備是否為清單上裝備
def Equip_MM_Receive_Archiving_Check(User_ID, Equip_URL):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv', 'HV_Equip.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)

            # 遍歷每一行
            for row in csv_reader:
                # 檢查 Equip_URL 是否存在於該行
                if row['Equip_URL'] == Equip_URL:

                    # 比對確認 User_ID 與 Equip_Current_Owner_ID 是否一致
                    if User_ID == row['Equip_Current_Owner_ID']:
                        # 如果找到，列印相關資訊
                        # print(f"Equip_Current_Owner_ID: {
                        #     row['Equip_Current_Owner_ID']}")
                        # print(f"Rental_Status: {row['Rental_Status']}")
                        # print(f"Expiry_Date: {row['Expiry_Date']}")
                        # print(f"Deposit: {row['Deposit']}")
                        return {
                            'Check_Pass': 'True',
                            'Rental_Status': row['Rental_Status'],
                            'Expiry_Date': row['Expiry_Date'],
                            'Deposit': row['Deposit']
                        }

        # 如果迴圈結束仍未找到，顯示找不到的訊息
        # print(f"Equip with URL {Equip_URL} not found in the CSV file.")
        return {
            'Check_Pass': 'False'
        }

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


# 紀錄收下 RTS 的 Credit
def Credits_MM_Receive_Archiving(User_ID, Credits):
    # 取得當前時間，並使用 ISO 格式
    current_time = datetime.datetime.now().isoformat()

    # 資料
    data = [current_time, User_ID, Credits]

    # CSV 檔案路徑
    current_directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(
        current_directory, 'csv', 'HV_RTS_Credits.csv')

    # 寫入資料到 CSV 檔案
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)

        # 如果檔案是空的，先寫入欄位名稱
        if file.tell() == 0:
            writer.writerow(['Time', 'User_ID', 'Credits'])

        # 寫入資料
        writer.writerow(data)


# 用於紀錄收到的"未在清單上裝備"
def Equip_MM_Receive_Archiving_Check_Not_Find(User_ID, Equip_URL):
    # 取得當前時間，並使用 ISO 格式
    current_time = datetime.datetime.now().isoformat()

    # 資料
    data = [current_time, User_ID, Equip_URL]

    # CSV 檔案路徑
    current_directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(
        current_directory, 'csv', 'HV_Equip_Not_Find_List.csv')

    # 寫入資料到 CSV 檔案
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)

        # 如果檔案是空的，先寫入欄位名稱
        if file.tell() == 0:
            writer.writerow(['Time', 'User_ID', 'Equip_URL'])

        # 寫入資料
        writer.writerow(data)


# 用於紀錄收到的"清單上裝備"的處理
# 檢查收到的裝備，並進行 Archiving 處理
# 比對 Equip_Current_Owner_ID 與 Equip_URL 做確認
def Equip_MM_Receive_Archiving_Check_Found(User_ID, Equip_URL):
    # 取得當前目錄
    current_directory = os.path.dirname(os.path.abspath(__file__))

    # 檔案路徑
    file_path = os.path.join(current_directory, 'csv', 'HV_Equip.csv')

    try:
        # 開啟 CSV 檔案
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # 建立 CSV 讀取器
            csv_reader = csv.DictReader(csvfile)
            rows = list(csv_reader)

        # 找到 Equip_URL 對應的索引
        index_to_modify = None
        for i, row in enumerate(rows):
            if row['Equip_URL'] == Equip_URL:
                index_to_modify = i
                break

        if rows[index_to_modify]['Equip_Current_Owner_ID'] == User_ID:
            if rows[index_to_modify]['Rental_Status'] == 'Rental':
                if index_to_modify is not None:
                    # 修改找到的資訊
                    rows[index_to_modify]['Equip_Current_Owner_ID'] = HV_Free_Shop_ID
                    rows[index_to_modify]['Equip_Current_Owner_UID'] = HV_Free_Shop_UID
                    rows[index_to_modify]['Rental_Status'] = 'Free'
                    del rows[index_to_modify]['Expiry_Date']

                    # 將修改後的資訊寫回 CSV 檔案
                    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = csv_reader.fieldnames
                        csv_writer = csv.DictWriter(
                            csvfile, fieldnames=fieldnames)

                        # 寫入標題
                        csv_writer.writeheader()

                        # 寫入所有資料，包括修改後的那一行
                        csv_writer.writerows(rows)

                    # print(f"成功修改 Equip_URL {Equip_URL} 的資訊")
                    Write_Raw_Log('Equip_MM_Receive_Archiving_Check_Found',
                                  'Archiving', f"成功歸檔 Equip_URL {Equip_URL}")
                    return True

        else:
            print(f"Equip_URL {Equip_URL} 未找到相應的資訊")
            return {'Archiving_Pass': 'False'}

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def check_user_has_ticket_number(user_uid: str,  item_suit_id: str, item_suit_order_limit: int):
    """
    使用user-uid、item_suit_id做索引，是否超過領取次數，若有則回應false，沒有會回應true

    輸入:
        user_uid:E變態的UID
        item_suit_id:贈送品名編號
        item_suit_order_limit:贈送品名領取次數限制
    """
    csv_file_path = os.path.join(csv_directory, 'free_shop_ticket.csv')
    headers = ['Ticket_No', 'Time', 'User_ID',
               'User_UID', 'User_Level', 'Item_Suit']
    check_csv_exists(csv_file_path, headers)

    ticket_counter: int = 0

    # 讀取CSV文件並找到最新的Ticket_No
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if int(row['User_UID']) == user_uid:
                if row['item_suit_id'] == item_suit_id:
                    ticket_counter = +1

    if ticket_counter < item_suit_order_limit:
        return True
    else:
        return False


def check_user_has_ticket_in_time_list(user_uid: str, time_limit: int, item_suit_id: str):
    """
    使用user-uid、item_suit_id做索引，確認時間限制內有無ticket，若有則回應false，沒有會回應true

    輸入:
        user_uid:E變態的UID
        time_limit:單位為天
        item_suit_id:贈送品名編號
    """
    csv_file_path = os.path.join(csv_directory, 'free_shop_ticket.csv')
    headers = ['Ticket_No', 'Time', 'User_ID',
               'User_UID', 'User_Level', 'Item_Suit']
    check_csv_exists(csv_file_path, headers)

    # 設定時間初始值
    last_ticket_time = '2000-01-01T00:00:00.00000'

    # 讀取CSV文件並找到最新的Ticket_No
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        max_ticket_no = 0
        for row in reader:
            if int(row['User_UID']) == user_uid:
                if row['item_suit_id'] == item_suit_id:
                    last_ticket_time = row['Time']

    # 取得當前時間
    current_time = datetime.datetime.now()
    last_ticket_time = datetime.datetime.fromisoformat(last_ticket_time)

    if last_ticket_time:
        if last_ticket_time < (current_time - datetime.timedelta(days=time_limit)):
            return True
        else:
            return False
    else:
        return True


def add_free_shop_ticket(User_ID: str, User_UID: int, User_Level: int, Item_Suit_ID: str):
    csv_file_path = os.path.join(csv_directory, 'free_shop_ticket.csv')
    headers = ['Ticket_No', 'Time', 'User_ID',
               'User_UID', 'User_Level', 'Item_Suit']
    check_csv_exists(csv_file_path, headers)

    # 讀取CSV文件並找到最新的Ticket_No
    with open(csv_file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        max_ticket_no = 0
        for row in reader:
            ticket_no = int(row['Ticket_No'])
            if ticket_no > max_ticket_no:
                max_ticket_no = ticket_no

    # 將最新的Ticket_No加1
    new_ticket_no = max_ticket_no + 1
    # 取得當前時間
    current_time = datetime.datetime.now().isoformat()

    # 要寫入的新資料
    new_data = {
        'Ticket_No': new_ticket_no,
        'Time': current_time,
        'User_ID': User_ID,
        'User_UID': User_UID,
        'User_Level': User_Level,
        'Item_Suit': Item_Suit_ID
    }

    # 將新資料寫入CSV文件
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writerow(new_data)

    logging.info('成功新增 Ticket {}'.format(new_ticket_no))
    return new_ticket_no

    # print(rows)
    # print(type(rows))
    # # 計算新的Ticket_No，即目前條目數加1
    # Ticket_No = len(rows) + 1

    # # 取得當前時間
    # current_time = datetime.datetime.now().isoformat()

    # # 創建新的資料行
    # new_row = {
    #     'Ticket_No': Ticket_No,
    #     'Time': current_time,
    #     'User_ID': User_ID,
    #     'User_UID': User_UID,
    #     'User_Level': User_Level,
    #     'Item_Suit': Item_Suit_ID
    # }

    # # 添加新的資料行到原有資料中
    # rows.append(new_row)

    # # 寫回CSV檔案
    # with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
    #     writer = csv.DictWriter(file, fieldnames=csv_file_path)

    #     # 寫入標頭（如果檔案是空的）
    #     if not file.tell():
    #         writer.writeheader()

    #     # 寫入所有資料行
    #     writer.writerows(rows)

    # logging.info('成功新增 Ticket {}'.format(Ticket_No))
    # return Ticket_No


# 根據 User_ID 與 Equip_URL 搜尋並關閉 Ticket
def Close_HV_Equip_Shop_Ticket(User_ID, Equip_URL):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(
        current_directory, 'csv', 'HV_Equip_Shop_Ticket.csv')

    Ticket_No = 0

    try:
        # 開啟CSV文件進行讀取
        with open(csv_file_path, 'r', newline='') as file:
            # 讀取CSV文件
            reader = csv.DictReader(file)
            rows = list(reader)
            # 建立 CSV 讀寫物件
            fieldnames = reader.fieldnames

        # 尋找符合條件資料
        for row in rows:
            if row['Equip_URL'] == Equip_URL and row['Ticket_Status'] == 'Open' and row['User_ID'] == User_ID:
                Ticket_No = row['Ticket_No']
                row['Return_Date'] = datetime.datetime.now().isoformat()
                row['Ticket_Status'] = 'Close'

        # 寫回CSV文件
        with open(csv_file_path, 'w', newline='') as file:

            # 建立寫入器
            writer = csv.DictWriter(file, fieldnames=fieldnames)

            # 寫入標頭
            writer.writeheader()

            # 寫入更新資料
            writer.writerows(rows)

        if Ticket_No != 0:
            Write_Raw_Log('Close_HV_Equip_Shop_Ticket',
                          'Close_Ticket', f"成功關閉 Ticket {Ticket_No}")
            return Ticket_No

    except FileNotFoundError:
        print(f"找不到檔案: {csv_file_path}")

    return None  # 如果找不到相應的Equip_URL，返回None


# HV_Equip.csv 的裝備清單重新排序
# 排序邏輯：類別排序、各類別中按照 Equip_ID 從小到大排序
def Equip_Order_sort_Equip_ID():
    # 設定路徑
    current_directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_directory, 'csv', 'HV_Equip.csv')

    # 讀取 CSV 檔案
    with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        # 將資料轉為列表
        data = list(reader)

    # 定義排序的優先順序
    category_order_priority = {
        'One-handed': 1,
        'Two-handed': 2,
        'Staff': 3,
        'Shield': 4,
        'Cloth': 5,
        'Light': 6,
        'Heavy': 7
    }

    # 先按照 'Equip_Category' 進行排序，再在每個類別中按照 'Equip_ID' 進行升序排序
    sorted_data = sorted(data, key=lambda row: (
        category_order_priority[row['Equip_Category']], int(row['Equip_ID'])))

    # 將排序後的資料寫回 CSV 檔案
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_data)


# HV_Equip.csv 的裝備清單重新排序
# 排序邏輯：類別排序、各類別中按照 Equip_Level 從小到大排序
def Equip_Order_sort_Equip_Level():
    # 設定路徑
    current_directory = os.path.dirname(os.path.abspath(__file__))
    csv_file_path = os.path.join(current_directory, 'csv', 'HV_Equip.csv')

    # 讀取 CSV 檔案
    with open(csv_file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        # 將資料轉為列表
        data = list(reader)

    # 定義排序的優先順序
    category_order_priority = {
        'One-handed': 1,
        'Two-handed': 2,
        'Staff': 3,
        'Shield': 4,
        'Cloth': 5,
        'Light': 6,
        'Heavy': 7
    }

    # 先按照 'Equip_Category' 進行排序，再在每個類別中按照 'Equip_Level' 進行升序排序
    sorted_data = sorted(data, key=lambda row: (
        category_order_priority[row['Equip_Category']], int(row['Equip_Level'])))

    # 將排序後的資料寫回 CSV 檔案
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as file:
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_data)


# print(Get_Expiry_Date_From_Ticket_No(str(7)))

# Equip_MM_Send_Archiving('test000', '1111111111111111',
#                         'https://hentaiverse.org/equip/288599280/6170b54cf3', '2023-12-10T17:32:44.836884')

# print(Get_Equip_Rental_Status_And_Deposit_From_Equip_ID('161349058'))

# print(Get_Ticket_User_ID_By_Ticket_No(1))

# print(Equip_MM_Receive_RTS_Check(
#     'VVFGV', 'https://hentaiverse.org/equip/292015813/bc0c58d297'))


# # 使用範例
# equip_url_to_search = "https://hentaiverse.org/equip/250454217/61bc8281b9"
# Close_HV_Equip_Shop_Ticket('testuser', equip_url_to_search)

# if latest_ticket:
#     print(f"找到最新的 Ticket: {latest_ticket}")
# else:
#     print(f"找不到 Equip_URL 為 {equip_url_to_search} 的 Ticket")

# print(Get_Equip_ID_From_URL('https://hentaiverse.org/equip/250454217/61bc8281b9'))
# 使用範例


# # 測試
# Archiveing_Status = Equip_MM_Receive_Archiving_Check_Found(
#     'ericeric91', 'https://hentaiverse.org/equip/284352050/204a6af6dd')
# print(Archiveing_Status)

# # 測試
# Write_Raw_Log('Equip_MM_Receive_Archiving_Check_Found',
#               'Archiving', f"成功修改 Equip_URL '1111' 的資訊")

# # 測試
# expiry_date = "2023-12-04T00:59:59"  # 替換成你的到期日
# deposit_amount = 1000  # 替換成你的押金金額

# result_process, result_fee = Rental_Fee_Calc(expiry_date, deposit_amount)
# print("Rental Fee:", result_fee)
# print("Calculation Process:")
# print(result_process)

# # 測試函式
# expiry_date = "2023-12-01T12:00:00"  # 替換為你的到期日期
# deposit_amount = 100  # 替換為你的押金金額

# fee_result = Rental_Fee_Calc(expiry_date, deposit_amount)
# print(f"The rental fee is: {fee_result}")


# # 使用範例
# user_id_example = 'example_user'
# equip_url_example = 'example_url'
# Equip_MM_Receive_Archiving_Check_Not_Find(user_id_example, equip_url_example)


# 使用範例
# equip_info = Equip_MM_Receive_Archiving_Check(
#     'ericeric91', 'https://hentaiverse.org/equip/284352050/204a6af6dd1')
# if equip_info['Check_Pass'] == True:
#     print(f"Rental_Status: {equip_info['Rental_Status']}")
#     print(f"Expiry_Date: {equip_info['Expiry_Date']}")
#     print(f"Deposit: {equip_info['Deposit']}")
# else:
#     print("Equip not found.")


# # 使用範例
# Write_Raw_Log("Function_Name", "Action_Performed", "Some_Raw_Log_Content")

# Temp_ID = 777
# Tag_In_MM_Ticket(Temp_ID)
# Untag_In_MM_Ticket(Temp_ID)

# Add_MM_Take_Date(16)
# print(datetime.datetime.now().replace(microsecond=0).isoformat())

# Close_HV_Equip_Shop_Ticket(
#     'testuser', 'https://hentaiverse.org/equip/250454217/61bc8281b9')

# Add_HV_Equip_Shop_Ticket("testuser", "1111111",
#                          "https://hentaiverse.org/equip/250454217/61bc8281b9", "2023-12-31", "50000")

# print(Get_In_MM_Ticket_List())

# Equip_Order_sort_Equip_Level()


# print(Rental_Fee_Calc('2024-01-27 19:22:36.731017', '300'))

# check_transaction = Check_Transaction()
# check_transaction.Start()
# check_transaction.End()

# if check_transaction.Check():
#     print('111')
# else:
#     print('222')
# check_transaction.Backup()
# check_transaction.rollback()


# Add_User_To_Black_List('jacktherabbits', '5443762',
#                        'Selling rental store equipment without explanation,Exquisite Rapier of Slaughter,https://hentaiverse.org/equip/293223566/76bae32185', Time=None)

# print(Get_User_From_Black_List())


# print(Get_Black_List_Reason_From_User_ID('iugi'))
# events = Get_Black_List_Reason_From_User_ID('iugi')
# for event in events:
#     print(event['Time'])
#     print(event['User_UID'])
#     print(event['Equip_URL'])
#     print(event['Equip_Name'])
#     print(event['Root_Cause'])

# print(Get_User_From_Black_List())
# for ojb in Get_User_From_Black_List():
#     print(ojb)
#     user_id, user_uid = ojb
#     print(user_id)
#     print(user_uid)


# if Get_Grey_List_Pass_Check('2780100'):
#     print('123')
# else:
#     print('456')


# add_free_shop_ticket('userid', 10030, 101, 'suitid')
# temp = check_user_has_ticket_in_time_list(10010, 0)
# print(temp)
