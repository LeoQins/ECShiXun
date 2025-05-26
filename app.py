# filepath: c:\Users\LeoQin\Desktop\网络调试助手制作\app.py
# 导入所需模块，包含网络通信、多线程、命令行参数解析、系统交互、日期处理、数据库操作、队列支持和GUI相关模块
import socket  # 导入 socket 模块，用于网络通信
import threading  # 导入 threading 模块，用于多线程处理
import argparse  # 导入 argparse 模块，用于解析命令行参数
import sys  # 导入 sys 模块，提供与 Python 解释器交互的函数
from datetime import datetime  # 用于处理日期和时间
from sqlapp import sql_query_to_database  # 导入数据库插入数据函数
import queue  # 新增队列模块，用于线程间通信
import tkinter as tk  # 用于 update_chat_window 更新GUI聊天窗口
from init_sql import initsql  # 导入初始化数据库函数
# 全局变量：存储所有已连接的客户端套接字（用于TCP服务器广播）
clients = []
ENCODING = "utf-8"  # 默认编码
current_service_stop_event = None  # 全局变量，用于保存当前运行功能的停止事件
current_service_thread = None  # 新增：记录当前运行的线程

# 新增：GUI 模式相关标志与输入队列
IS_GUI_MODE = False  
gui_input_queue = None

# 定义全局变量，保存 GUI 聊天窗口对象
g_chat_text = None

# ---------------------------------------------------------------------
# 功能：更新GUI中聊天窗口显示内容（线程安全方式）
def update_chat_window(msg):
    """
    在 GUI 聊天窗口中追加消息，保证线程安全更新。
    """
    global g_chat_text
    if g_chat_text is not None:
        g_chat_text.after(0, lambda: (g_chat_text.insert(tk.END, msg + "\n"),
                                       g_chat_text.see(tk.END)))


# ---------------------------------------------------------------------
# 功能：统一输入函数，根据工作模式选择命令行或GUI输入
def unified_input(prompt):
    """
    统一输入函数：在 GUI 模式下从 gui_input_queue 中读取输入，
    若等待过程中检测到停止事件则及时中断，否则使用命令行 input() 完成输入。
    """
    if IS_GUI_MODE and gui_input_queue is not None:
        print(prompt)  # 控制台打印提示信息
        while True:
            if current_service_stop_event and current_service_stop_event.is_set():
                raise Exception("操作已停止")
            try:
                return gui_input_queue.get(timeout=0.5)
            except queue.Empty:
                continue
    else:
        return input(prompt)


# ---------------------------------------------------------------------
# 功能：TCP 客户端，实现与服务器进行数据收发
def tcp_client(host, port, stop_event=None):
    """
    实现 TCP 客户端，连接服务器后既能发送数据也能接收数据。
    
    参数：
        host：服务器主机地址
        port：服务器端口
    """
    if stop_event is None:
        stop_event = threading.Event()

    # 内部函数：接收来自服务器的数据
    def receive_from_server(sock):
        """
        客户端专用：接收来自服务器的数据并打印显示。
        
        参数：
            sock：已连接的服务器端 socket 对象
        """
        try:
            peer = sock.getpeername()  # 获取服务器地址和端口
        except Exception:
            peer = ("unknown", "unknown")
        while not stop_event.is_set():
            try:
                sock.settimeout(1)
                response = sock.recv(1024)
                if not response:
                    msg = f"[TCP 客户端] 服务器 {peer[0]}:{peer[1]} 关闭连接。"
                    print(msg)
                    if IS_GUI_MODE:
                        update_chat_window(msg)
                    break
                decoded = response.decode(ENCODING)
                msg = f"[TCP 客户端] 从 {peer[0]}:{peer[1]} 收到: {decoded}"
                print(msg)
                if IS_GUI_MODE:
                    update_chat_window(msg)
                log_network_event("tcp", peer, sock.getsockname(), decoded)
            except socket.timeout:
                continue
            except Exception as e:
                err_msg = f"[TCP 客户端] 接收数据错误: {e}"
                print(err_msg)
                if IS_GUI_MODE:
                    update_chat_window(err_msg)
                break

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        conn_msg = f"[TCP 客户端] 已连接到 {host}:{port}"
        print(conn_msg)
        if IS_GUI_MODE:
            update_chat_window(conn_msg)

        # 创建并启动接收数据线程
        recv_thread = threading.Thread(target=receive_from_server, args=(sock,))
        recv_thread.daemon = True
        recv_thread.start()

        # 主循环：等待用户输入数据发送给服务器
        while not stop_event.is_set():
            try:
                data = unified_input("请输入发送内容（输入 exit 退出）：")
            except Exception:
                break
            if stop_event.is_set():
                break
            if data.lower() == 'exit':
                break
            try:
                sock.sendall(data.encode(ENCODING))
                local_addr = sock.getsockname()
                send_msg = f"[TCP 客户端] 从 {local_addr[0]}:{local_addr[1]} 发送: {data}"
                print(send_msg)
                if IS_GUI_MODE:
                    update_chat_window(send_msg)
                log_network_event("tcp", local_addr, sock.getpeername(), data)
            except Exception as e:
                err_msg = f"[TCP 客户端] 发送数据错误: {e}"
                print(err_msg)
                if IS_GUI_MODE:
                    update_chat_window(err_msg)
                break
    except Exception as e:
        err_msg = f"TCP 客户端错误: {e}"
        print(err_msg)
        if IS_GUI_MODE:
            update_chat_window(err_msg)
    finally:
        sock.close()
        end_msg = "[TCP 客户端] 已关闭。"
        print(end_msg)
        if IS_GUI_MODE:
            update_chat_window(end_msg)


# ---------------------------------------------------------------------
# 功能：TCP 服务器，支持多客户端连接、消息转发与广播
def tcp_server(host, port, stop_event):
    """
    实现 TCP 服务器，支持多客户端同时连接，并能进行消息回显与广播。
    
    参数：
        host：绑定的主机地址
        port：监听的端口号
    """
    # 内部函数：从操作员处获取输入并向所有客户端广播消息
    def server_input_broadcast():
        """
        服务器端专用线程：从操作员处读取输入，并向所有连接中的客户端广播该消息。
        """
        while not stop_event.is_set():
            try:
                msg = unified_input("请输入服务器发送内容（输入 exit 可结束输入）：")
            except Exception:
                break
            if msg.lower() == "exit":
                print("服务器退出输入广播模式。")
                break
            for client in clients:
                try:
                    client.sendall(f"[服务器] {msg}".encode(ENCODING))
                    try:
                        server_addr = client.getsockname()
                        client_addr = client.getpeername()
                        log_network_event("tcp", server_addr, client_addr, f"{msg}")
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[TCP 服务器] 向客户端发送消息错误: {e}")

    # 内部函数：处理每个TCP客户端连接，接收数据并回显
    def handle_tcp_client(client_sock, addr):
        """
        为每个连接的TCP客户端创建一个处理线程，负责处理接收和回显消息。
        """
        global clients
        print(f"[TCP 服务端] 与 {addr} 建立连接。")
        clients.append(client_sock)
        try:
            while True:
                data = client_sock.recv(1024)
                if not data:
                    break
                decoded = data.decode(ENCODING)
                # 记录收到数据事件
                log_network_event("tcp", addr, client_sock.getsockname(), decoded)
                msg = f"[TCP 服务端] 来自 {addr} 的消息: {decoded}"
                print(msg)
                if IS_GUI_MODE:
                    update_chat_window(msg)
        except Exception as e:
            print(f"[TCP 服务端] 错误 ({addr}): {e}")
        finally:
            if client_sock in clients:
                clients.remove(client_sock)
            client_sock.close()
            print(f"[TCP 服务端] {addr} 连接已关闭。")
    # 创建TCP服务器套接字
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 TCP 套接字
    try:
        server.bind((host, port))  # 绑定到指定主机地址和端口
        server.listen(5)  # 开始监听，最多允许5个等待连接
        server.settimeout(1)  # 设置超时以便定期检测 stop_event
        print(f"[TCP 服务端] 服务器启动，正在监听 {host}:{port}")
    except Exception as e:
        print(f"TCP 服务端启动失败: {e}")
        return

    # 启动广播输入线程
    input_thread = threading.Thread(target=server_input_broadcast)
    input_thread.daemon = True
    input_thread.start()

    try:
        # 循环等待客户端连接
        while not stop_event.is_set():
            try:
                client_sock, addr = server.accept()
            except socket.timeout:
                continue
            client_thread = threading.Thread(target=handle_tcp_client, args=(client_sock, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[TCP 服务端] 正在关闭服务器...")
    except Exception as e:
        print(f"TCP 服务端错误: {e}")
    finally:
        server.close()
        print("[TCP 服务端] 服务已停止。")


# ---------------------------------------------------------------------
# 功能：UDP 客户端，实现与服务器进行数据收发
def udp_client(host, port, stop_event=None):
    if stop_event is None:
        stop_event = threading.Event()

    # 内部函数：接收来自UDP服务器的数据
    def receive_from_udp(sock, stop_event):
        sock.settimeout(1)
        while not stop_event.is_set():
            try:
                data, server_addr = sock.recvfrom(1024)
                decoded = data.decode(ENCODING)
                log_network_event("udp", server_addr, sock.getsockname(), decoded)
                msg = f"[UDP 客户端] 收到 {server_addr} 的消息: {decoded}"
                print(msg)
                if IS_GUI_MODE:
                    update_chat_window(msg)
            except socket.timeout:
                continue
            except Exception as e:
                err_msg = f"[UDP 客户端] 接收数据错误: {e}"
                print(err_msg)
                if IS_GUI_MODE:
                    update_chat_window(err_msg)
                break

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[UDP 客户端] 准备向 {host}:{port} 发送数据")
        recv_thread = threading.Thread(target=receive_from_udp, args=(sock, stop_event), daemon=True)
        recv_thread.start()

        # 循环等待用户输入数据，并发送到UDP服务器
        while not stop_event.is_set():
            try:
                data = unified_input("请输入发送内容（输入 exit 退出）：")
            except Exception:
                break
            if stop_event.is_set():
                break
            if data.lower() == 'exit':
                stop_event.set()
                break
            try:
                sock.sendto(data.encode(ENCODING), (host, port))
                log_network_event("udp", sock.getsockname(), (host, port), data)
            except Exception as e:
                print(f"[UDP 客户端] 发送数据错误: {e}")
                break
    except Exception as e:
        print(f"UDP 客户端错误: {e}")
    finally:
        stop_event.set()
        sock.close()
        print("[UDP 客户端] 已关闭。")


# ---------------------------------------------------------------------
# 功能：UDP 服务器，支持广播消息并收发数据
def udp_server(host, port, stop_event=None):
    if stop_event is None:
        stop_event = threading.Event()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_clients = set()
    try:
        sock.bind((host, port))
        sock.settimeout(1)
        print(f"[UDP 服务端] 服务器启动，正在监听 {host}:{port}")
    except Exception as e:
        print(f"UDP 服务端启动失败: {e}")
        sys.exit(1)
    
    # 内部函数：用于通过输入广播消息给所有UDP客户端
    def udp_server_broadcast():
        while not stop_event.is_set():
            try:
                msg = unified_input("请输入服务器广播消息（输入 exit 退出广播）：")
            except Exception:
                break
            if msg.lower() == "exit":
                print("退出广播模式。")
                break
            for client_addr in udp_clients:
                try:
                    sock.sendto(f"[服务器] {msg}".encode(ENCODING), client_addr)
                    log_network_event("udp", sock.getsockname(), client_addr, msg)
                except Exception as e:
                    print(f"[UDP 服务端] 广播给 {client_addr} 错误: {e}")
    
    # 启动广播线程
    broadcast_thread = threading.Thread(target=udp_server_broadcast, daemon=True)
    broadcast_thread.start()
    
    try:
        # 循环接收UDP客户端发送的数据
        while not stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue
            udp_clients.add(addr)
            decoded = data.decode(ENCODING)
            log_network_event("udp", addr, sock.getsockname(), decoded)
            msg = f"[UDP 服务端] 来自 {addr} 的消息: {decoded}"
            print(msg)
            if IS_GUI_MODE:
                update_chat_window(msg)
    except KeyboardInterrupt:
        print("\n[UDP 服务端] 正在关闭服务器...")
    except Exception as e:
        print(f"UDP 服务端错误: {e}")
    finally:
        sock.close()
        print("[UDP 服务端] 服务已停止。")


# ---------------------------------------------------------------------
# 功能：交互式菜单，根据输入参数选择不同的运行模式
def interactive_menu():
    """
    提供一个交互式菜单，使用户可以选择运行模式和输入必要的参数。
    """
    global ENCODING
    print("请选择运行模式：")
    print("1. TCP 服务器")
    print("2. TCP 客户端")
    print("3. UDP 服务器")
    print("4. UDP 客户端")
    print("5. GUI 界面")
    choice = unified_input("输入选项编号 (1-5): ")
    host = unified_input("请输入主机地址 (默认 127.0.0.1): ") or "127.0.0.1"
    port_input = unified_input("请输入端口号 (默认 8000): ") or "8000"
    try:
        port = int(port_input)
    except ValueError:
        print("端口号必须为数字!")
        sys.exit(1)
    encoding_input = input("请输入编码模式 (默认 utf-8，选项：utf-8/gbk): ") or "utf-8"
    ENCODING = encoding_input.lower()
    # 根据用户选择启动对应的功能模块
    if choice == '1':
        tcp_server(host, port)
    elif choice == '2':
        tcp_client(host, port)
    elif choice == '3':
        udp_server(host, port)
    elif choice == '4':
        udp_client(host, port)
    elif choice == '5':
        gui_interface(host, port)
    else:
        print("无效的选项, 程序退出。")
        sys.exit(1)


# ---------------------------------------------------------------------
# 功能：图形界面（GUI）入口，构建基于tkinter的网络调试助手界面
def gui_interface(inputhost, inputport):
    import tkinter as tk
    from tkinter import ttk
    import threading
    global g_chat_text, current_service_thread

    root = tk.Tk()
    root.title("网络调试助手 GUI")

    # ---------------- 配置区 ----------------
    config_frame = ttk.Frame(root, padding=10)
    config_frame.grid(row=0, column=0, sticky="NSEW")
    ttk.Label(config_frame, text="主机地址:").grid(row=0, column=0, sticky="W")
    host_entry = ttk.Entry(config_frame)
    host_entry.insert(0, inputhost)
    host_entry.grid(row=0, column=1, sticky="EW", padx=5, pady=5)
    ttk.Label(config_frame, text="端口号:").grid(row=1, column=0, sticky="W")
    port_entry = ttk.Entry(config_frame)
    port_entry.insert(0, inputport)
    port_entry.grid(row=1, column=1, sticky="EW", padx=5, pady=5)
    ttk.Label(config_frame, text="编码:").grid(row=2, column=0, sticky="W")
    encoding_entry = ttk.Entry(config_frame)
    encoding_entry.insert(0, "utf-8")
    encoding_entry.grid(row=2, column=1, sticky="EW", padx=5, pady=5)

    # ---------------- 功能按钮区 ----------------
    button_frame = ttk.Frame(config_frame, padding=(0,10))
    button_frame.grid(row=3, column=0, columnspan=2, sticky="EW")
    ttk.Button(button_frame, text="TCP 服务器", command=lambda: start_mode("tcp_server")).grid(row=0, column=0, padx=5)
    ttk.Button(button_frame, text="TCP 客户端", command=lambda: start_mode("tcp_client")).grid(row=0, column=1, padx=5)
    ttk.Button(button_frame, text="UDP 服务器", command=lambda: start_mode("udp_server")).grid(row=0, column=2, padx=5)
    ttk.Button(button_frame, text="UDP 客户端", command=lambda: start_mode("udp_client")).grid(row=0, column=3, padx=5)

    # ---------------- 聊天窗口区 ----------------
    chat_frame = ttk.Frame(root, padding=10)
    chat_frame.grid(row=1, column=0, sticky="NSEW")
    chat_text = tk.Text(chat_frame, height=15, width=80)
    chat_text.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
    g_chat_text = chat_text  # 全局赋值，便于 update_chat_window 进行调用
    chat_entry = ttk.Entry(chat_frame, width=60)
    chat_entry.grid(row=1, column=0, padx=5, pady=5, sticky="EW")
    # 内部函数：处理聊天消息发送
    def send_chat():
        content = chat_entry.get().strip()
        if content:
            gui_input_queue.put(content)
            # 使用配置里的 host:port 显示发送者信息
            send_msg = f"[{host_entry.get()}:{port_entry.get()}] 发送: {content}"
            chat_text.insert(tk.END, send_msg + "\n")
            chat_text.see(tk.END)
            chat_entry.delete(0, tk.END)
    ttk.Button(chat_frame, text="发送", command=send_chat).grid(row=1, column=1, padx=5, pady=5)

    # ---------------- 启动模式函数 ----------------
    def start_mode(mode):
        global current_service_stop_event, current_service_thread, ENCODING
        # 如果有正在运行的功能，先停止并等待退出
        if current_service_stop_event is not None and current_service_thread is not None:
            current_service_stop_event.set()
            current_service_thread.join(2)  # 等待最多2秒让线程退出
        # 新功能开始前，新建停止标志和线程变量
        current_service_stop_event = threading.Event()
        stop_event = current_service_stop_event

        host_val = host_entry.get() or inputhost
        try:
            port_val = int(port_entry.get() or inputport)
        except ValueError:
            chat_text.insert(tk.END, "端口号必须为数字!\n")
            return
        encoding_val = encoding_entry.get() or "utf-8"
        start_msg = f"启动 {mode}，地址: {host_val}:{port_val}，编码: {encoding_val}"
        chat_text.insert(tk.END, start_msg + "\n")
        chat_text.see(tk.END)
        ENCODING = encoding_val.lower()

        # 根据模式创建对应线程，并记录到全局变量 current_service_thread
        if mode == "tcp_server":
            t = threading.Thread(target=tcp_server, args=(host_val, port_val, stop_event))
        elif mode == "tcp_client":
            t = threading.Thread(target=tcp_client, args=(host_val, port_val, stop_event))
        elif mode == "udp_server":
            t = threading.Thread(target=udp_server, args=(host_val, port_val, stop_event))
        elif mode == "udp_client":
            t = threading.Thread(target=udp_client, args=(host_val, port_val, stop_event))
        t.daemon = True
        current_service_thread = t
        t.start()

    root.mainloop()


# ---------------------------------------------------------------------
# 功能：日志记录，将网络数据收发事件写入日志文件并写入数据库
def log_network_event(service_type, sender, receiver, data=""):
    """
    记录网络数据收发事件，存储时间戳、服务类型（udp或tcp）、发送方和接收方以及数据内容。

    参数：
        service_type (str): 服务类型，如 "tcp" 或 "udp"
        sender (str): 发送方标识，例如 "127.0.0.1:8000"
        receiver (str): 接收方标识，例如 "192.168.1.10:54321"
        data (str): 发送或接收的数据内容，默认为空字符串
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - {service_type} - 发送方: {sender} - 接收方: {receiver} - 数据: {data}\n"
    # 内部函数：格式化地址输出，转换为 "IP:端口" 格式
    def format_address(s: str) -> str:
        """
        将形如 "('10.21.88.183', 8000)" 的字符串转换为 "10.21.88.183:8000" 格式。
        """
        # 去掉左右括号
        s = s.strip("()")
        # 按逗号拆分
        parts = s.split(",")
        # 去掉每部分的空白和引号
        ip = parts[0].strip().strip("'")
        port = parts[1].strip()
        # 拼接结果，中间用冒号连接
        return ip + ":" + port
    try:
        with open("network_events.log", "a", encoding=ENCODING) as logfile:
            logfile.write(log_entry)
            # sender1=str(sender).replace("'", '"')
            # receiver1=str(receiver).replace("'", '"')
            sender1 = format_address(str(sender))
            receiver1 = format_address(str(receiver))
            args=f"INSERT INTO 通讯记录 (`时间`, `类型`, `发送方`, `接收方`, `数据`)\nVALUES ('{timestamp}','{service_type}','{sender1}', '{receiver1}', '{data}');"
            sql_query_to_database(args)  # 将日志写入数据库

    except Exception as e:
        print(f"日志写入错误: {e}")


# ---------------------------------------------------------------------
# 功能：程序入口，根据配置项启动对应模式
def main():
    global ENCODING, IS_GUI_MODE, gui_input_queue
    # 配置项设置运行模式及参数
    # config = {
    #     "mode": "gui",    # 可选项："tcp_server", "tcp_client", "udp_server", "udp_client", "gui"
    #     "host": "10.21.163.147",
    #     "port": 8000,
    #     "encoding": "utf-8"
    # }
    from config_app import config
    ENCODING = config.get("encoding", "utf-8").lower()
    mode = config.get("mode", "")
    host = config.get("host", "10.21.88.183")
    port = config.get("port", 8000)
    initsql()  # 初始化数据库
    if mode == "gui":
        IS_GUI_MODE = True
        gui_input_queue = queue.Queue()  # 初始化 GUI 输入队列
        gui_interface(host, port)
    elif mode == "tcp_server":
        stop_event = threading.Event()
        tcp_server(host, port, stop_event)
    elif mode == "tcp_client":
        stop_event = threading.Event()
        tcp_client(host, port, stop_event)
    elif mode == "udp_server":
        stop_event = threading.Event()
        udp_server(host, port, stop_event)
    elif mode == "udp_client":
        stop_event = threading.Event()
        udp_client(host, port, stop_event)
    else:
        print("无效的运行模式。")
        sys.exit(1)

if __name__ == "__main__":
    main()  # 程序入口，调用主函数


