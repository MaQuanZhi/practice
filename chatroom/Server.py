import socket
from threading import Thread
import math

# 维护一个在线用户的连接列表，用于群发消息
online_conn = list()
# 存储socket连接和用户的对应关系
conn2user = dict()


# 发送带长度的字符串
def send_string_with_length(_conn, content):
    # 先发送内容的长度
    _conn.sendall(bytes(content, encoding='utf-8').__len__().to_bytes(4, byteorder='big'))
    # 再发送内容
    _conn.sendall(bytes(content, encoding='utf-8'))


def send_number(_conn, number):
    _conn.sendall(int(number).to_bytes(4, byteorder='big'))


def recv_number(_conn):
    return int.from_bytes(_conn.recv(4), byteorder='big')


# 获取定长字符串
def recv_string_by_length(_conn, len):
    return str(_conn.recv(len), "utf-8")


# 获取变长字符串
def recv_all_string(_conn):
    # 获取消息长度
    length = int.from_bytes(_conn.recv(4), byteorder='big')
    b_size = 3 * 1024  # 注意utf8编码中汉字占3字节，英文占1字节
    times = math.ceil(length / b_size)
    content = ''
    for i in range(times):
        if i == times - 1:
            seg_b = _conn.recv(length % b_size)
        else:
            seg_b = _conn.recv(b_size)
        content += str(seg_b, encoding='utf-8')
    return content


# 检查用户名密码是否正确
def check_user(user, key):
    print("login: user: " + user + ", key: " + key)
    with open("data\\user.txt", 'r', encoding="utf-8") as f:
        user_data = f.read().split('\n')[:-1]
        for line in user_data:
            user_name,user_key = line.split(',')
            if user == user_name :
                return key == user_key
    return False

# 添加用户数据
def add_user(user, key):
    try:
        print("register: user: " + user + ", key: " + key)
        with open("data\\user.txt", 'r', encoding="utf-8") as f:
            user_data = f.read().split('\n')[:-1]
            print(user_data)
            for line in user_data:
                if user == line.split(',')[0]:
                    # 用户名存在
                    return "1"
        # 添加用户和密码md5
        with open("data\\user.txt", 'a', encoding="utf-8") as user_data:
            user_data.write(user + "," + key +'\n')
        return "0"
    except Exception as e:
        print("添加用户数据出错：" + str(e))
        return "2"


# 处理刷新列表的请求
def handle_online_list(_conn, addr):
    print("online_conn.__len__()=" + str(online_conn.__len__()))
    print("conn2user.__len__()=" + str(conn2user.__len__()))
    for con in online_conn:
        send_string_with_length(con, "#!onlinelist#!")
        # 先发送列表人数
        send_number(con, online_conn.__len__())
        for c in online_conn:
            send_string_with_length(con, conn2user[c])
    return True


# 处理登录请求
def handle_login(_conn, addr):
    user = recv_all_string(_conn)
    key = recv_all_string(_conn)
    check_result = check_user(user, key)
    if check_result:
        _conn.sendall(bytes("1", "utf-8"))
        conn2user[_conn] = user
        online_conn.append(_conn)
        handle_online_list(_conn, addr)
    else:
        _conn.sendall(bytes("0", "utf-8"))
    return True


# 处理注册请求
def handle_register(_conn, addr):
    user = recv_all_string(_conn)
    key = recv_all_string(_conn)
    _conn.sendall(bytes(add_user(user, key), "utf-8"))
    return True


# 处理消息发送请求
def handle_message(_conn, addr):
    content = recv_all_string(_conn)
    # 发送给所有在线客户端
    for c in online_conn:
        # 先发一个字符串告诉客户端接下来是消息
        send_string_with_length(c, "#!message#!")
        send_string_with_length(c, conn2user[_conn])
        send_string_with_length(c, content)

    return True


# 处理请求线程的执行方法
def handle(_conn, addr):
    try:
        while True:
            # 获取请求类型
            _type = str(_conn.recv(1), "utf-8")
            # 是否继续处理
            _goon = True
            if _type == "1":  # 登录请求
                print("开始处理登录请求")
                _goon = handle_login(_conn, addr)
            elif _type == "2":  # 注册请求
                print("开始处理注册请求")
                _goon = handle_register(_conn, addr)
            elif _type == "3":  # 发送消息
                print("开始处理发送消息请求")
                _goon = handle_message(_conn, addr)
            elif _type == "4":  # 发送在线用户列表
                print("开始处理刷新列表请求")
                _goon = handle_online_list(_conn, addr)
            if not _goon:
                break
    except Exception as e:
        print(str(addr) + " 连接异常，准备断开: " + str(e))
    finally:
        try:
            _conn.close()
            online_conn.remove(_conn)
            conn2user.pop(_conn)
            handle_online_list(_conn, addr)
        except:
            print(str(addr) + "连接关闭异常")


if __name__ == "__main__":
    try:
        sk = socket.socket()
        sk.bind(('127.0.0.1', 12323))
        # 最大挂起数
        sk.listen(10)
        print("服务器启动成功，开始监听...")
        while True:
            conn, addr = sk.accept()
            Thread(target=handle, args=(conn, addr)).start()
    except Exception as e:
        print("服务器出错: " + str(e))
