import mysql.connector
from mysql.connector import errorcode   

config = {
    'user': 'root',
    'password': 'MySQL2004@',
    'host': '127.0.0.1',
    'port': 3306,
    'database': '',    # 如果还没建库，可以先连接不带 database，然后 cursor.execute("CREATE DATABASE …")
    'charset': 'utf8mb4',
    'use_pure': True,
}
def connect_to_database():
    cnx=mysql.connector.connect(**config)
    return cnx

def insert_for_app(user_input):
    cnx = connect_to_database()
    cursor = cnx.cursor()
    if user_input.lower() == "exit":
        print("退出查询")
    try:
        cursor.execute(user_input)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(row)
        else:
            # 执行非查询语句时提交
                cnx.commit()
                #print("插入数据执行成功")
    except mysql.connector.Error as err:
            print("执行查询时出错:", err)

    
def initsql():
    args= (" CREATE DATABASE IF NOT EXISTS mydb DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
            "USE mydb;\n"
            "CREATE TABLE IF NOT EXISTS 通讯记录 (\n"
            "   id INT AUTO_INCREMENT PRIMARY KEY,\n"
            "   时间 DATETIME NOT NULL,\n"
            "   类型 VARCHAR(10) NOT NULL,\n"
            "   发送方 VARCHAR(50) NOT NULL,\n"
            "   接收方 VARCHAR(50) NOT NULL,\n"
            "   数据 TEXT\n"
        ");\n"
        )
    #     """更新表中的数据"""
    insert_for_app(args)

def insert_for_app(user_input):
    cnx = connect_to_database()
    cursor = cnx.cursor()
    if user_input.lower() == "exit":
        print("退出查询")
    try:
        cursor.execute(user_input)
        results = cursor.fetchall()
        if results:
            for row in results:
                print(row)
        else:
            # 执行非查询语句时提交
                cnx.commit()
                #print("插入数据执行成功")
    except mysql.connector.Error as err:
            print("执行查询时出错:", err)

       