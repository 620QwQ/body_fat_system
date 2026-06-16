import pymysql

try:
    conn = pymysql.connect(
        host='localhost',
        user='appuser',
        password='123456',
        database='body_fat_system',
        charset='utf8mb4'
    )
    print("✅ pymysql 连接成功！")
    conn.close()
except Exception as e:
    print(f"❌ 连接失败：{e}")