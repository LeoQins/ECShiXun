import mysql.connector
from mysql.connector import errorcode

config = {
    'user': 'root',
    'password': 'root2004@',
    'host': '127.0.0.1',
    'port': 3307,
    'database': 'mydb',    # 如果还没建库，可以先连接不带 database，然后 cursor.execute("CREATE DATABASE …")
    'charset': 'utf8mb4',
    'use_pure': True,
}
# 连接数据库
try:
    cnx = mysql.connector.connect(**config)
    print("数据库连接成功")
    cursor = cnx.cursor()

    while True:
        # 提示用户输入 SQL 查询
        # 这里可以使用 input() 函数来获取用户输入的 SQL 查询语句
        user_input = input("请输入查询 SQL (输入 'exit' 退出): ").strip()
        if user_input.lower() == "exit":
            print("退出查询")
            break
        try:
            cursor.execute(user_input)
            # 如果查询返回多行
            results = cursor.fetchall()
            if results:
                for row in results:
                    print(row)
            else:
                # 如果执行的是非查询语句
                cnx.commit()
                print("执行成功")
        except mysql.connector.Error as err:
            print("执行查询时出错:", err)
    
    cursor.close()
    cnx.close()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("用户名或密码错误")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("数据库不存在")
    else:
        print(err)
