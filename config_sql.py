config = {
    'user': 'root',
    'password': 'MySQL2004@',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'mydb',    # 如果还没建库，可以先连接不带 database，然后 cursor.execute("CREATE DATABASE …")
    'charset': 'utf8mb4',
    'use_pure': True,
}