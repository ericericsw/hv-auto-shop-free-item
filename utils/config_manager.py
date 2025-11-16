import configparser
import os
import json
from cryptography.fernet import Fernet
import sys
import datetime
from utils.utils import get_current_directory, check_folder_path_exists

current_directory = get_current_directory()

if getattr(sys, 'frozen', False):
    confnig_folder_path = os.path.join(current_directory, 'config')
else:
    confnig_folder_path = os.path.join(
        os.path.dirname(current_directory), 'config')

check_folder_path_exists(confnig_folder_path)

config = configparser.ConfigParser()
config_file_name = 'config.ini'
config_file_path = os.path.join(confnig_folder_path, config_file_name)
secret_file_name = 'secret.key'
secret_file_path = os.path.join(confnig_folder_path, secret_file_name)
encrypted_file_name = 'config.encrypted'
encrypted_file_path = os.path.join(
    confnig_folder_path, encrypted_file_name)


class ConfigManager:
    """
    一個安全的設定檔管理器，功能如下：
    1. 讀取 config.ini 檔案。
    2. 根據 [Encryption] 區段的設定，自動加密新的敏感資訊。
    3. 將加密後的資訊儲存在獨立的檔案中。
    4. 若已存在加密資訊但 key 遺失會備份加密資訊並重新產生新 key 與加密資訊
    5. 提供一個統一的 get() 方法，自動解密並回傳需要的值。
    """

    def __init__(self, config_path=config_file_path, key_path=secret_file_path, encrypted_data_path=encrypted_file_path):
        """
        初始化設定管理器。
        :param config_path: config.ini 檔案的路徑。
        :param key_path: 加密金鑰檔案的路徑。
        :param encrypted_data_path: 加密後資料的儲存路徑。
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"設定檔 '{config_path}' 不存在。")

        self.config_path = config_path
        self.key_path = key_path
        self.encrypted_data_path = encrypted_data_path

        # 載入設定檔
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path, encoding='utf-8')

        # 載入或生成金鑰
        self.key = self._load_or_generate_key()
        self.fernet = Fernet(self.key)

        # 載入已加密的資料
        self.encrypted_data = self._load_encrypted_data()

        # 執行更新處理
        self.process_updates()

    def _load_or_generate_key(self):
        """如果金鑰存在則載入，否則生成一個新的金鑰並儲存。"""
        from utils.logger import setup_logger
        logger = setup_logger(__name__)

        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            # 在生成新金鑰之前，檢查是否存在舊的加密檔案
            if os.path.exists(self.encrypted_data_path):
                logger.critical(
                    f"警告：找不到金鑰檔案，但偵測到舊的加密檔案 '{self.encrypted_data_path}'。")
                # 產生一個帶有時間戳的備份檔名
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                backup_path = f"{self.encrypted_data_path}.bak{timestamp}"

                logger.critical(f"      正在將舊檔案備份至 '{backup_path}'...")
                # 執行重命名 (備份)
                os.rename(self.encrypted_data_path, backup_path)
                logger.critical("      備份完成。")

            logger.warning(f"提示：將在 '{self.key_path}' 生成一個新的金鑰。")
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)
            return key

    def _load_encrypted_data(self):
        """載入並解密已儲存的敏感資訊。"""
        if not os.path.exists(self.encrypted_data_path):
            return {}

        try:
            with open(self.encrypted_data_path, 'rb') as f:
                encrypted_blob = f.read()

            decrypted_blob = self.fernet.decrypt(encrypted_blob)
            return json.loads(decrypted_blob.decode('utf-8'))
        except Exception as e:
            from utils.logger import setup_logger
            logger = setup_logger(__name__)

            logger.critical(
                f"警告：無法載入或解密 '{self.encrypted_data_path}'。將視為空資料。錯誤：{e}")
            return {}

    def _save_encrypted_data(self):
        """將敏感資訊加密並儲存到檔案。"""
        data_blob = json.dumps(self.encrypted_data).encode('utf-8')
        encrypted_blob = self.fernet.encrypt(data_blob)
        with open(self.encrypted_data_path, 'wb') as f:
            f.write(encrypted_blob)

    def is_encryption_enabled(self, section, option):
        """檢查某個選項是否在 [Encryption] 區段中被標記為 True。"""
        encryption_key = f"{section}.{option}"
        if self.config.has_option('Encryption', encryption_key):
            return self.config.getboolean('Encryption', encryption_key)
        return False

    def process_updates(self):
        """
        處理 config.ini 中的更新值。
        如果一個被標記為加密的欄位有值，則加密該值，
        存入加密檔案，然後清空 config.ini 中的該值。
        """
        from utils.logger import setup_logger
        logger = setup_logger(__name__)

        needs_saving = False
        for section in self.config.sections():
            if section == 'Encryption':
                continue
            for option in self.config.options(section):
                if self.is_encryption_enabled(section, option):
                    value = self.config.get(section, option)
                    # 如果有值，代表需要更新
                    if value:
                        logger.warning(
                            f"偵測到更新：'{section}.{option}'，正在進行加密處理...")
                        encrypted_value = self.fernet.encrypt(
                            value.encode('utf-8')).decode('utf-8')
                        self.encrypted_data[f"{section}.{option}"] = encrypted_value

                        # 清空 config.ini 中的值
                        self.config.set(section, option, '')
                        needs_saving = True

        if needs_saving:
            logger.warning("正在儲存加密資料並更新 config.ini...")
            self._save_encrypted_data()
            with open(self.config_path, 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
            logger.warning("更新完成！")

    def get(self, section, option):
        """
        獲取設定值。如果該值被標記為加密，則自動解密後回傳。
        """
        if self.is_encryption_enabled(section, option):
            # 從加密資料中讀取
            key = f"{section}.{option}"
            encrypted_value = self.encrypted_data.get(key)
            if not encrypted_value:
                # 如果 config.ini 中是空的，加密檔案中也找不到，就回傳空字串
                return ""

            decrypted_value = self.fernet.decrypt(
                encrypted_value.encode('utf-8')).decode('utf-8')
            return decrypted_value
        else:
            # 直接從 config 物件中讀取
            return self.config.get(section, option)

    def getint(self, section, option):
        """
        獲取整數(int)型別的設定值。
        """
        value_str = self.get(section, option)
        try:
            return int(value_str)
        except (ValueError, TypeError):
            raise ValueError(
                f"設定值 '{section}.{option}' (值: '{value_str}') 無法轉換為整數。")

    def getboolean(self, section, option):
        """
        獲取布林(bool)型別的設定值。
        支援 'yes'/'no', 'true'/'false', 'on'/'off', '1'/'0'。
        """
        value_str = self.get(section, option)
        val_lower = value_str.lower()
        if val_lower in ('true', 'yes', 'on', '1'):
            return True
        elif val_lower in ('false', 'no', 'off', '0'):
            return False
        else:
            raise ValueError(
                f"設定值 '{section}.{option}' (值: '{value_str}') 無法轉換為布林值。")
