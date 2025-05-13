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

def normal_mode(cursor, cnx):
    """普通模式，保持原有输入模式"""
    while True:
        user_input = input("请输入查询 SQL (输入 'exit' 退出): ").strip()
        if user_input.lower() == "exit":
            print("退出查询")
            break
        try:
            cursor.execute(user_input)
            results = cursor.fetchall()
            if results:
                for row in results:
                    print(row)
            else:
                # 执行非查询语句时提交
                cnx.commit()
                print("执行成功")
        except mysql.connector.Error as err:
            print("执行查询时出错:", err)

def interactive_mode(cursor, cnx):
    """交互模式，提供更友好的菜单界面"""
    print("欢迎使用交互模式")
    while True:
        print("\n请选择操作:")
        print("1. 执行 SQL 查询")
        print("2. 退出")
        choice = input("请输入选项 (1/2): ").strip()
        if choice == "2":
            print("退出交互模式")
            break
        elif choice == "1":
            sql_query = input("请输入查询 SQL: ").strip()
            try:
                cursor.execute(sql_query)
                results = cursor.fetchall()
                if results:
                    for row in results:
                        print(row)
                else:
                    # 执行非查询语句时提交
                    cnx.commit()
                    print("执行成功")
            except mysql.connector.Error as err:
                print("执行查询时出错:", err)
        else:
            print("无效选项，请重新选择。")

def main():
    try:
        cnx = mysql.connector.connect(**config)
        print("数据库连接成功")
        cursor = cnx.cursor()

        print("请选择运行模式:")
        print("1. 普通模式")
        print("2. 交互模式")
        mode = input("请输入选项 (1/2): ").strip()
        if mode == "2":
            interactive_mode(cursor, cnx)
        else:
            normal_mode(cursor, cnx)

        cursor.close()
        cnx.close()
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("用户名或密码错误")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("数据库不存在")
        else:
            print(err)

if __name__ == "__main__":
    main()