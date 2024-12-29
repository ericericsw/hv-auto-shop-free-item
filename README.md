# hv-auto-shop-free-item
這是HV免費店的執行腳本

# 目前功能
自動爬樓檢查 post 是否符合設定 order 要求，符合要求的會用 MM 發信，錯誤的會記錄在 warning log  
目前還沒有 MM check 與論壇 Post edit 功能

## 時間間隔計算
作為升級獎勵，不同的 item_suit_id 的時間獨立計算  

## 預佔post數量
程式預設中，前5個post會是店家post.  
可以更多，可自行更改 csv/free_shop_last_post.csv.

## config.ini 設定
請將 config_sample.ini 改名成 config_sample.ini 進行使用  
HV_Free_Shop_ID =  
HV_Free_Shop_UID =  
ipb_pass_hash =  
ipb_session_id =  
Check_Forums_URL:檢查的論壇Post，請提供主樓網址，例如:https://forums.e-hentai.org/index.php?showtopic=257252  
Check_Interval:執行間隔(Sec)。預設180秒  
Test_Mode:啟用測試模式後，不會發出MM。預設為啟用

## free_shop_order.csv 的格式
範例可參考 csv/free_shop_order_setting.csv  
若發現不在 csv/item_list.csv 上的道具，可回報

| 欄位名稱 | 說明 | 取值與限制 |
|----------|----------|----------|
| item_suit_id | 讓人請求order的ID | 不得有空白，必須是完整的字段 |
| item_name |  要寄出的item名稱 | 不區分大小寫，名稱列表可參考 csv/item_list.csv
| item_number | 要寄出的item數量 | 只能填入數字
| item_suit_cool_time_day | 請求order的間隔天數 | 只能填入數字，若同一筆item_suit_id有不同值，則取最大值
| item_suit_order_limit | 請求order的次數限制 | 只能填入數字，若同一筆item_suit_id有不同值，則取最小值
| item_suit_level_limit_min | 請求order的最小等級 | 只能填入數字，若同一筆item_suit_id有不同值，則取最大值
| item_suit_level_limit_max | 請求order的最大等級 | 只能填入數字，若同一筆item_suit_id有不同值，則取最小值

# 使用方法
## 如何使用
完成設定 config_sample.ini 的設定後：  
windows:打包後雙擊open_shop.bat

## 如何停止
關閉cmd或是使用ctrl+c進行終止

# 待開發
* 戰鬥狀態檢測
* post edit
* MM check
* item 數量 check