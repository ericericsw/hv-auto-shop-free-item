pyinstaller -D forums_shop_main.py

copy config_sample.ini dist\forums_shop_main\config_sample.ini
mkdir dist\forums_shop_main\csv
copy csv\free_shop_last_post_sample.csv dist\forums_shop_main\csv\free_shop_last_post_sample.csv
copy csv\item_list.csv dist\forums_shop_main\csv\item_list.csv
copy csv\free_shop_order_setting.csv dist\forums_shop_main\csv\free_shop_order_setting.csv
copy open_shop.bat dist\forums_shop_main\open_shop.bat
copy README.md dist\forums_shop_main\README.md

pause