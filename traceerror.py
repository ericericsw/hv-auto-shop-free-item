import traceback

results = 123

try:
    # 你的程式碼
    latest_record = max(results, key=lambda x: x['Change Date'])
except Exception as e:
    print("遇到錯誤：", e)
    print("完整錯誤追蹤：")
    print(traceback.format_exc())
