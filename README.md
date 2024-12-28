# hv-auto-shop-free-item
for hentaiverse free item shop

# 預佔post數量
程式預設中，前5個post會是店家post
可以更多，可自行更改 csv/free_shop_last_post.csv

# config.ini 設定
HV_Equip_Rental_Shop_ID:
HV_Equip_Rental_Shop_UID = 
ipb_pass_hash = 
ipb_session_id

# free_shop_order.csv 的格式
item_suit_id:讓人叫號的ID
item_name
item_number
item_suit_cool_time_day
item_suit_order_limit
item_suit_level_limit_min
item_suit_level_limit_max


| 欄位名稱 | 說明 | 取值與限制 |
|----------|----------|----------|
| item_suit_id | 讓人請求order的ID | 不得有空白，必須是完整的字段 |
| item_name |  要寄出的item名稱 | 不區分大小寫，名稱列表可參考 csv/item_list.csv
| item_number | 要寄出的item數量 | 只能填入數字
| item_suit_cool_time_day | 請求order的間隔天數 | 只能填入數字，若同一筆item_suit_id有不同值，則取最大值
| item_suit_order_limit | 請求order的次數限制 | 只能填入數字，若同一筆item_suit_id有不同值，則取最小值
| item_suit_level_limit_min | 請求order的最小等級 | 只能填入數字，若同一筆item_suit_id有不同值，則取最大值
| item_suit_level_limit_max | 請求order的最大等級 | 只能填入數字，若同一筆item_suit_id有不同值，則取最小值