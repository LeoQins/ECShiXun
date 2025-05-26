import mysql.connector
from mysql.connector import errorcode
from config_sql import config
# config = {
#     'user': 'root',
#     'password': 'MySQL2004@',
#     'host': '127.0.0.1',
#     'port': 3306,
#     'database': 'mydb',    # 如果还没建库，可以先连接不带 database，然后 cursor.execute("CREATE DATABASE …")
#     'charset': 'utf8mb4',
#     'use_pure': True,
# }
def show_tables(cursor, cnx):
    """显示数据库中的所有表"""
    try:
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        if tables:
            print("数据库中的表:")
            for table in tables:
                print(table[0])
        else:
            print("数据库中没有表")
    except mysql.connector.Error as err:
        print("查询表时出错:", err)

def describe_table(cursor, cnx):
    """查看指定表内容"""
    table_name = input("请输入要查看结构的表名: ").strip()
    sql = f"SELECT * FROM {table_name}"
    try:
        cursor.execute(sql)
        results = cursor.fetchall()
        if results:
            print(f"表 {table_name} 的内容:")
            for row in results:
                print(row)
        else:
            print("没有结果")
    except mysql.connector.Error as err:
        print("查询表内容时出错:", err)

def create_table(cursor, cnx):
    """创建新表"""
    table_name = input("请输入要创建的表名: ").strip()
    columns = input("请输入列定义 (如: id INT PRIMARY KEY, name VARCHAR(255)): ").strip()
    sql = f"CREATE TABLE {table_name} ({columns})"
    try:
        cursor.execute(sql)
        cnx.commit()
        print("表创建成功")
    except mysql.connector.Error as err:
        print("创建表时出错:", err)

def insert_data(cursor, cnx):
    """插入数据到表"""
    table_name = input("请输入要插入数据的表名: ").strip()
    columns = input("请输入要插入的列 (逗号分隔): ").strip()
    values = input("请输入对应的值 (逗号分隔，注意字符串需加引号): ").strip()
    sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
    try:
        cursor.execute(sql)
        cnx.commit()
        print("数据插入成功")
    except mysql.connector.Error as err:
        print("插入数据时出错:", err)

def update_data(cursor, cnx):
    """更新表中的数据"""
    table_name = input("请输入要更新数据的表名: ").strip()
    update_clause = input("请输入更新内容 (如: name='newName'): ").strip()
    condition = input("请输入更新条件 (WHERE 子句，不需要输入 WHERE): ").strip()
    sql = f"UPDATE {table_name} SET {update_clause} WHERE {condition}"
    try:
        cursor.execute(sql)
        cnx.commit()
        print("数据更新成功")
    except mysql.connector.Error as err:
        print("更新数据时出错:", err)

def delete_data(cursor, cnx):
    """删除表中的数据"""
    table_name = input("请输入要删除数据的表名: ").strip()
    condition = input("请输入删除条件 (WHERE 子句，不需要输入 WHERE): ").strip()
    sql = f"DELETE FROM {table_name} WHERE {condition}"
    try:
        cursor.execute(sql)
        cnx.commit()
        print("数据删除成功")
    except mysql.connector.Error as err:
        print("删除数据时出错:", err)

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
        print("1. 执行自定义 SQL 查询")
        print("2. 显示所有表")
        print("3. 查看表结构")
        print("4. 创建新表")
        print("5. 插入数据")
        print("6. 更新数据")
        print("7. 删除数据")
        print("8. 退出")
        choice = input("请输入选项 (1-8): ").strip()
        if choice == "8":
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
                    cnx.commit()
                    print("执行成功")
            except mysql.connector.Error as err:
                print("执行查询时出错:", err)
        elif choice == "2":
            show_tables(cursor, cnx)
        elif choice == "3":
            describe_table(cursor, cnx)
        elif choice == "4":
            create_table(cursor, cnx)
        elif choice == "5":
            insert_data(cursor, cnx)
        elif choice == "6":
            update_data(cursor, cnx)
        elif choice == "7":
            delete_data(cursor, cnx)
        else:
            print("无效选项，请重新选择。")

def connect_to_database():
    cnx=mysql.connector.connect(**config)
    return cnx

def sql_query_to_database(user_input):
    results=None
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
    return results
def main():
    try:
        #cnx = mysql.connector.connect(**config)
        cnx = connect_to_database()
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