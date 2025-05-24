###################################################此代码仅用于学习使用，作为连接数据库的原始示例，不被调用###################################################

import mysql.connector
from mysql.connector import errorcode

config = {
    'user': 'root',
    'password': 'MySQL2004@',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'mydb',    # 如果还没建库，可以先连接不带 database，然后 cursor.execute("CREATE DATABASE …")
    'charset': 'utf8mb4',
    'use_pure': True,
}

try:
    cnx = mysql.connector.connect(**config)
    print("数据库连接成功")
    cursor = cnx.cursor()
    query = "SELECT * FROM customer;"
    cursor.execute("SELECT NOW();")

    print(cursor.fetchone())
    cursor.execute(query)
    for row in cursor.fetchall():
        print(row)
    cursor.close()
    cnx.close()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("用户名或密码错误")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("数据库不存在")
    else:
        print(err)
