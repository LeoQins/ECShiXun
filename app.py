import socket  # 导入 socket 模块，用于网络通信
import threading  # 导入 threading 模块，用于多线程处理
import argparse  # 导入 argparse 模块，用于解析命令行参数
import sys  # 导入 sys 模块，提供与 Python 解释器交互的函数

# 全局变量：存储所有已连接的客户端套接字，用于后续广播消息
clients = []

# 默认编码方式，可能的值有 "utf-8" 或 "gbk"；这里设置为 "utf-8"
ENCODING = "utf-8"

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
            # 解码接收到的数据并打印
            print(f"[TCP 客户端] 来自 {peer[0]}:{peer[1]} 收到: {response.decode(ENCODING)}")
        except Exception as e:
            print(f"[TCP 客户端] 接收数据错误: {e}")
            break

def tcp_client(host, port):
    """
    实现 TCP 客户端，连接服务器后既能发送数据也能接收数据。
    
    参数：
        host：服务器主机地址
        port：服务器端口
    """
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
    except Exception as e:
        print(f"TCP 客户端错误: {e}")
    finally:
        sock.close()  # 确保连接被关闭
        print("[TCP 客户端] 已关闭。")

def server_input_broadcast():
    """
    服务器端专用线程：从操作员处读取输入，并向所有连接中的客户端广播该消息。
    """
    while True:
        msg = input("请输入服务器发送内容（输入 exit 可结束输入）：")
        if msg.lower() == "exit":
            print("服务器退出输入广播模式。")
            break  # 退出广播输入模式
        for client in clients:
            try:
                # 对每个客户端发送消息，这里加入了"[服务器]"前缀以标识消息来源
                client.sendall(f"[服务器] {msg}".encode(ENCODING))
            except Exception as e:
                print(f"[TCP 服务器] 向客户端发送消息错误: {e}")

def handle_tcp_client(client_sock, addr):
    """
    为每个连接的TCP客户端创建一个处理线程，负责处理接收和回显消息。
    
    参数：
        client_sock：与客户端进行通信的套接字对象
        addr：客户端的地址信息（IP 和端口）
    """
    global clients
    print(f"[TCP 服务端] 与 {addr} 建立连接。")
    clients.append(client_sock)  # 添加新客户端到全局列表中
    try:
        while True:
            data = client_sock.recv(1024)  # 接收客户端数据
            if not data:
                break  # 如果未接收到数据，则认为连接已断开
            # 解码并打印来自客户端的消息
            print(f"[TCP 服务端] 来自 {addr} 的消息: {data.decode(ENCODING)}")
            # 回显接收到的数据给客户端
            client_sock.sendall(f"回显: {data.decode(ENCODING)}".encode(ENCODING))
    except Exception as e:
        print(f"[TCP 服务端] 错误 ({addr}): {e}")
    finally:
        if client_sock in clients:
            clients.remove(client_sock)  # 清理已关闭的客户端连接
        client_sock.close()  # 关闭对应的socket连接
        print(f"[TCP 服务端] {addr} 连接已关闭。")

def tcp_server(host, port):
    """
    实现 TCP 服务器，支持多客户端同时连接，并能进行消息回显与广播。
    
    参数：
        host：绑定的主机地址
        port：监听的端口号
    """
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
    """
    实现 UDP 客户端：发送消息给服务器，并接收服务器的回显消息。
    
    参数：
        host：服务器主机地址
        port：服务器端口号
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建 UDP 套接字
        print(f"[UDP 客户端] 准备向 {host}:{port} 发送数据")
        while True:
            data = input("请输入发送内容（输入 exit 退出）：")
            if data.lower() == 'exit':
                break  # 输入 exit 退出发送环节
            # 发送数据到指定地址
            sock.sendto(data.encode(ENCODING), (host, port))
            try:
                sock.settimeout(2.0)  # 设置接收响应的超时时间为2秒
                response, server_addr = sock.recvfrom(1024)  # 等待接收回显数据
                print(f"[UDP 客户端] 来自 {server_addr} 的回响: {response.decode(ENCODING)}")
            except socket.timeout:
                print("[UDP 客户端] 未收到响应。")
    except Exception as e:
        print(f"UDP 客户端错误: {e}")
    finally:
        sock.close()  # 关闭 UDP 套接字
        print("[UDP 客户端] 已关闭。")

def udp_server(host, port):
    """
    实现 UDP 服务器：接收客户端消息并返回相应的回显信息。
    
    参数：
        host：绑定的主机地址
        port：监听的端口号
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 创建 UDP 套接字
    try:
        sock.bind((host, port))  # 将 socket 绑定到指定地址和端口
        print(f"[UDP 服务端] 服务器启动，正在监听 {host}:{port}")
    except Exception as e:
        print(f"UDP 服务端启动失败: {e}")
        sys.exit(1)
    try:
        while True:
            data, addr = sock.recvfrom(1024)  # 接收来自客户端的数据及其地址
            print(f"[UDP 服务端] 来自 {addr} 的消息: {data.decode(ENCODING)}")
            # 将接收到的数据原样回送，实现回显
            sock.sendto(f"回显: {data.decode(ENCODING)}".encode(ENCODING), addr)
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
    choice = input("输入选项编号 (1-4): ")
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
    else:
        print("无效的选项, 程序退出。")
        sys.exit(1)

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


