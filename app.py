import socket  # 导入 socket 模块，用于网络通信
import threading  # 导入 threading 模块，用于多线程处理
import argparse  # 导入 argparse 模块，用于解析命令行参数
import sys  # 导入 sys 模块，提供与 Python 解释器交互的函数
from datetime import datetime
from sqlapp import insert_for_app  # 导入数据库插入数据
# 全局变量：存储所有已连接的客户端套接字，用于后续广播消息
clients = []

# 默认编码方式，可能的值有 "utf-8" 或 "gbk"；这里设置为 "utf-8"
ENCODING = "utf-8"



def tcp_client(host, port):
    """
    实现 TCP 客户端，连接服务器后既能发送数据也能接收数据。
    
    参数：
        host：服务器主机地址
        port：服务器端口
    """
    def receive_from_server(sock):
        """
        客户端专用：接收来自服务器的数据并打印显示。
        
        参数：
            sock：已连接的服务器端 socket 对象
        """
        try:
            peer = sock.getpeername()  # 尝试获取服务器的地址和端口
        except Exception as e:
            peer = ("unknown", "unknown")  # 如果获取失败，则设置为未知
        while True:
            try:
                response = sock.recv(1024)  # 从服务器接收最多1024字节的数据
                if not response:
                    # 当 recv() 返回空字节时，表示服务器已经关闭连接
                    print(f"[TCP 客户端] 服务器 {peer[0]}:{peer[1]} 关闭连接。")
                    break
                # 记录收到数据事件，将接收的数据传入 data 参数
                log_network_event("tcp", peer, sock.getsockname(), response.decode(ENCODING))
                # 解码接收到的数据并打印
                print(f"[TCP 客户端] 来自 {peer[0]}:{peer[1]} 收到: {response.decode(ENCODING)}")
            except Exception as e:
                print(f"[TCP 客户端] 接收数据错误: {e}")
                break
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 TCP 套接字
        sock.connect((host, port))  # 连接到指定的服务器
        print(f"[TCP 客户端] 已连接到 {host}:{port}")

        # 启动一个线程专门接收服务器数据，因为接收与发送要并行进行
        recv_thread = threading.Thread(target=receive_from_server, args=(sock,))
        recv_thread.daemon = True  # 设置为守护线程，在主线程退出时自动结束
        recv_thread.start()

        # 主线程用于读取用户输入，并将数据发送到服务器
        while True:
            data = input("请输入发送内容（输入 exit 退出）：")
            if data.lower() == 'exit':
                break  # 输入 exit 即退出客户端
            sock.sendall(data.encode(ENCODING))  # 将用户输入编码后发送出去
            # 记录发送数据事件，将发送的内容传入 data 参数
            log_network_event("tcp", sock.getsockname(), sock.getpeername(), data)
    except Exception as e:
        print(f"TCP 客户端错误: {e}")
    finally:
        sock.close()  # 确保连接被关闭
        print("[TCP 客户端] 已关闭。")


def tcp_server(host, port):
    """
    实现 TCP 服务器，支持多客户端同时连接，并能进行消息回显与广播。
    
    参数：
        host：绑定的主机地址
        port：监听的端口号
    """
        
    def server_input_broadcast():
        """
        服务器端专用线程：从操作员处读取输入，并向所有连接中的客户端广播该消息。
        """
        while True:
            msg = input("请输入服务器发送内容（输入 exit 可结束输入）：")
            if msg.lower() == "exit":
                print("服务器退出输入广播模式。")
                break
            for client in clients:
                try:
                    client.sendall(f"[服务器] {msg}".encode(ENCODING))
                    try:
                        server_addr = client.getsockname()
                        client_addr = client.getpeername()
                        # 记录广播发送事件，将广播消息内容传入 data 参数
                        log_network_event("tcp", server_addr, client_addr, f"{msg}")
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[TCP 服务器] 向客户端发送消息错误: {e}")
    
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
                # 记录收到数据事件，将接收到的数据传入 data 参数
                log_network_event("tcp", addr, client_sock.getsockname(), data.decode(ENCODING))
                print(f"[TCP 服务端] 来自 {addr} 的消息: {data.decode(ENCODING)}")
                                    ##############################不需要回显操作#############################################################################
                                    #
                                    #    
                                    #   # client_sock.sendall(f"[回显确认收到]: {data.decode(ENCODING)}".encode(ENCODING))
                                    #   # # 记录回显发送事件，将回显内容作为 data 参数传入
                                    #   # log_network_event("tcp", client_sock.getsockname(), addr, f"[回显确认收到]: {data.decode(ENCODING)}")
                                    #   ########################################################################################################################
        except Exception as e:
            print(f"[TCP 服务端] 错误 ({addr}): {e}")
        finally:
            if client_sock in clients:
                clients.remove(client_sock)
            client_sock.close()
            print(f"[TCP 服务端] {addr} 连接已关闭。")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建 TCP 套接字
    try:
        server.bind((host, port))  # 绑定到指定主机地址和端口
        server.listen(5)  # 开始监听，最多允许5个等待连接
        print(f"[TCP 服务端] 服务器启动，正在监听 {host}:{port}")
    except Exception as e:
        print(f"TCP 服务端启动失败: {e}")
        sys.exit(1)
    
    # 启动一个线程，用于接收服务器操作员输入并向客户端广播消息
    input_thread = threading.Thread(target=server_input_broadcast)
    input_thread.daemon = True  # 设置为守护线程
    input_thread.start()
    
    try:
        while True:
            # 阻塞等待客户端连接
            client_sock, addr = server.accept()
            # 为每个连接创建一个线程处理数据收发
            client_thread = threading.Thread(target=handle_tcp_client, args=(client_sock, addr))
            client_thread.daemon = True  # 设置线程为守护线程
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[TCP 服务端] 正在关闭服务器...")
    except Exception as e:
        print(f"TCP 服务端错误: {e}")
    finally:
        server.close()  # 关闭服务器套接字



def udp_client(host, port):
    def receive_from_udp(sock, stop_event):
        """
        在独立线程中持续接收 UDP 消息，检测 stop_event 来退出循环。
        """
        sock.settimeout(1)  # 设置1秒超时
        while not stop_event.is_set():
            try:
                data, server_addr = sock.recvfrom(1024)
                log_network_event("udp", server_addr, sock.getsockname(), data.decode(ENCODING))
                print(f"[UDP 客户端] 收到 {server_addr} 的消息: {data.decode(ENCODING)}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[UDP 客户端] 接收数据错误: {e}")
                break

    """
    实现 UDP 客户端：发送消息给服务器，并在独立线程中持续接收服务器消息
    """
    stop_event = threading.Event()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"[UDP 客户端] 准备向 {host}:{port} 发送数据")
        
        # 启动接收线程
        recv_thread = threading.Thread(target=receive_from_udp, args=(sock, stop_event), daemon=True)
        recv_thread.start()

        while True:
            data = input("请输入发送内容（输入 exit 退出）：")
            if data.lower() == 'exit':
                stop_event.set()
                break
            sock.sendto(data.encode(ENCODING), (host, port))
            log_network_event("udp", sock.getsockname(), (host, port), data)
    except Exception as e:
        print(f"UDP 客户端错误: {e}")
    finally:
        stop_event.set()
        sock.close()
        print("[UDP 客户端] 已关闭。")

def udp_server(host, port):
    """
    实现 UDP 服务器：接收客户端消息并可以向客户端广播消息。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_clients = set()  # 用于保存已知的客户端地址
    try:
        sock.bind((host, port))
        print(f"[UDP 服务端] 服务器启动，正在监听 {host}:{port}")
    except Exception as e:
        print(f"UDP 服务端启动失败: {e}")
        sys.exit(1)

    # 独立线程用于广播消息给所有已知客户端
    def udp_server_broadcast():
        while True:
            msg = input("请输入服务器广播消息（输入 exit 退出广播）：")
            if msg.lower() == "exit":
                print("退出广播模式。")
                break
            for client_addr in udp_clients:
                try:
                    sock.sendto(f"[服务器] {msg}".encode(ENCODING), client_addr)
                    log_network_event("udp", sock.getsockname(), client_addr, f"{msg}")
                except Exception as e:
                    print(f"[UDP 服务端] 广播给 {client_addr} 错误: {e}")

    broadcast_thread = threading.Thread(target=udp_server_broadcast, daemon=True)
    broadcast_thread.start()

    try:
        while True:
            data, addr = sock.recvfrom(1024)
            # 保存最近的客户端地址
            udp_clients.add(addr)
            log_network_event("udp", addr, sock.getsockname(), data.decode(ENCODING))
            print(f"[UDP 服务端] 来自 {addr} 的消息: {data.decode(ENCODING)}")
            # 如果需要回显或其他操作，可在此处添加（目前保持不做回显）
    except KeyboardInterrupt:
        print("\n[UDP 服务端] 正在关闭服务器...")
    except Exception as e:
        print(f"UDP 服务端错误: {e}")
    finally:
        sock.close()  # 关闭 UDP 套接字

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
    choice = input("输入选项编号 (1-5): ")
    # 获取主机地址，若未输入则默认为127.0.0.1
    host = input("请输入主机地址 (默认 127.0.0.1): ") or "127.0.0.1"
    # 获取端口号，若未输入则默认为8000
    port_input = input("请输入端口号 (默认 8000): ") or "8000"
    try:
        port = int(port_input)
    except ValueError:
        print("端口号必须为数字!")
        sys.exit(1)
    # 获取编码方式，默认使用 utf-8
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



def gui_interface(inputhost, inputport):
    """
    启动一个简单的 Tkinter GUI 界面，实现网络调试助手的可视化操作。
    """
    import tkinter as tk
    from tkinter import ttk
    import threading

    root = tk.Tk()
    root.title("网络调试助手 GUI")

    def start_mode(mode):
        host = host_entry.get() or inputhost
        try:
            port = int(port_entry.get() or inputport)
        except ValueError:
            log_text.insert(tk.END, "端口号必须为数字!\n")
            return
        encoding = encoding_entry.get() or "utf-8"
        log_text.insert(tk.END, f"启动 {mode}，地址: {host}:{port}，编码: {encoding}\n")
        # 更新全局编码变量
        global ENCODING
        ENCODING = encoding.lower()
        # 根据选择启动对应功能，放在后台线程中启动避免阻塞GUI
        if mode == "tcp_server":
            t = threading.Thread(target=tcp_server, args=(host, port))
        elif mode == "tcp_client":
            t = threading.Thread(target=tcp_client, args=(host, port))
        elif mode == "udp_server":
            t = threading.Thread(target=udp_server, args=(host, port))
        elif mode == "udp_client":
            t = threading.Thread(target=udp_client, args=(host, port))
        t.daemon = True
        t.start()

    # 创建输入框
    frame = ttk.Frame(root, padding=10)
    frame.grid(row=0, column=0, sticky="NSEW")

    ttk.Label(frame, text="主机地址:").grid(row=0, column=0, sticky="W")
    host_entry = ttk.Entry(frame)
    host_entry.insert(0, inputhost)
    host_entry.grid(row=0, column=1, sticky="EW")

    ttk.Label(frame, text="端口号:").grid(row=1, column=0, sticky="W")
    port_entry = ttk.Entry(frame)
    port_entry.insert(0, inputport)
    port_entry.grid(row=1, column=1, sticky="EW")

    ttk.Label(frame, text="编码:").grid(row=2, column=0, sticky="W")
    encoding_entry = ttk.Entry(frame)
    encoding_entry.insert(0, "utf-8")
    encoding_entry.grid(row=2, column=1, sticky="EW")

    # 创建功能按钮
    button_frame = ttk.Frame(frame, padding=(0,10))
    button_frame.grid(row=3, column=0, columnspan=2, sticky="EW")
    ttk.Button(button_frame, text="TCP 服务器", command=lambda: start_mode("tcp_server")).grid(row=0, column=0, padx=5)
    ttk.Button(button_frame, text="TCP 客户端", command=lambda: start_mode("tcp_client")).grid(row=0, column=1, padx=5)
    ttk.Button(button_frame, text="UDP 服务器", command=lambda: start_mode("udp_server")).grid(row=0, column=2, padx=5)
    ttk.Button(button_frame, text="UDP 客户端", command=lambda: start_mode("udp_client")).grid(row=0, column=3, padx=5)

    # 创建日志输出框
    log_text = tk.Text(root, height=10, width=60)
    log_text.grid(row=1, column=0, padx=10, pady=10)

    root.mainloop()

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
            insert_for_app(args)  # 将日志写入数据库

    except Exception as e:
        print(f"日志写入错误: {e}")



def main():
    """
    主函数：根据命令行参数或交互式菜单确定程序的运行模式并启动相应功能。
    """
    global ENCODING
    if len(sys.argv) > 1:
        # 如果传入了命令行参数，则使用 argparse 进行参数解析
        parser = argparse.ArgumentParser(description="网络调试助手: 实现多种网络功能")
        parser.add_argument("mode", choices=["tcp_server", "tcp_client", "udp_server", "udp_client"], help="选择运行的模式")
        parser.add_argument("--host", default="127.0.0.1", help="绑定/连接的主机地址，默认127.0.0.1")
        parser.add_argument("--port", type=int, default=8000, help="端口号，默认8000")
        parser.add_argument("--encoding", default="utf-8", help="编码模式，默认 utf-8，可设置为 gbk")
        args = parser.parse_args()
        ENCODING = args.encoding.lower()

        # 根据 mode 参数调用对应的功能函数
        if args.mode == "tcp_server":
            tcp_server(args.host, args.port)
        elif args.mode == "tcp_client":
            tcp_client(args.host, args.port)
        elif args.mode == "udp_server":
            udp_server(args.host, args.port)
        elif args.mode == "udp_client":
            udp_client(args.host, args.port)
    else:
        # 没有命令行参数时，启动交互式菜单
        interactive_menu()

if __name__ == "__main__":
    main()  # 程序入口，调用主函数


