# 导入所需的库
# 导入requests库，它是一个专门用来发送HTTP请求的强大工具
# 如果你还没有安装它，请在PyCharm的终端里运行: pip install requests
import requests

# --- 配置区 ---
# 设置服务器的地址。
# !! 重要 !!
# 1. 在本地测试app.py时，请使用 'http://127.0.0.1:5000/detect'
# 2. 当你把app.py部署到云服务器后，请将 '127.0.0.1' 替换成你的【服务器公网IP地址】
SERVER_URL = 'http://127.0.0.1:5000/detect'

# 要发送进行分析的本地图片文件的路径
IMAGE_PATH = 'test_image.jpg'

# 从服务器接收到的结果，要保存的文件名
RESULT_PATH = 'result_from_server.jpg'


# ------------

def analyze_image(server_url, image_path):
    """
    发送一张图片到服务器进行分析，并保存返回的结果。

    Args:
        server_url (str): 服务器API的完整URL。
        image_path (str): 本地图片文件的路径。
    """
    print(f"准备向服务器 {server_url} 发送图片 '{image_path}'...")

    try:
        # 1. 以二进制读取模式('rb')打开图片文件。
        #    使用 'with' 语句可以确保文件在使用完毕后被自动关闭。
        with open(image_path, 'rb') as image_file:

            # 2. 构建要发送的文件数据。
            #    这是一个字典，键 'file' 必须和服务器端 app.py 中
            #    request.files['file'] 的 'file' 完全对应。
            #    值是一个元组，包含(文件名, 文件对象, 内容类型)。
            files_to_send = {'file': (image_path, image_file, 'image/jpeg')}

            # 3. 【核心步骤】使用 requests.post() 发送一个HTTP POST请求。
            #    - 第一个参数是服务器URL。
            #    - files参数是我们准备好的文件数据。
            #    - timeout=20 设置一个20秒的超时，防止服务器处理慢或无响应时无限等待。
            print("正在发送请求，请稍候...")
            response = requests.post(server_url, files=files_to_send, timeout=20)

            # 4. 检查服务器的HTTP响应状态码。
            #    - response.raise_for_status() 是一个便捷函数，
            #      如果状态码是 4xx (客户端错误) 或 5xx (服务器错误)，它会自动抛出异常。
            response.raise_for_status()

            # 5. 如果代码能执行到这里，说明状态码是 2xx (成功)。
            #    以二进制写入模式('wb')打开一个新文件，并将响应内容(图片数据)写入。
            with open(RESULT_PATH, 'wb') as output_file:
                output_file.write(response.content)
            print(f"成功！分析结果已从服务器接收并保存为 '{RESULT_PATH}'")

    except FileNotFoundError:
        print(f"客户端错误：无法找到要发送的图片文件 '{image_path}'。请检查文件名和路径是否正确。")
    except requests.exceptions.ConnectionError:
        print(f"网络错误：无法连接到服务器 {server_url}。")
        print("请确认：")
        print("1. 你的服务器脚本 app.py 是否正在运行？")
        print("2. URL地址和端口是否正确？")
        print("3. 如果是云服务器，防火墙/安全组是否已开放相应端口？")
    except requests.exceptions.Timeout:
        print("请求超时：服务器在规定时间内没有响应。服务器可能正在处理一个非常大的文件，或者负载过高。")
    except requests.exceptions.HTTPError as e:
        # 捕获由 raise_for_status() 抛出的异常
        print(f"请求失败！服务器返回了一个错误状态码: {e.response.status_code}")
        # 尝试以JSON格式打印服务器返回的具体错误信息
        try:
            print(f"服务器错误详情: {e.response.json()}")
        except ValueError:
            print(f"无法解析服务器返回的错误信息: {e.response.text}")
    except Exception as e:
        # 捕获其他所有未知错误
        print(f"发生了一个未知错误: {e}")


# --- 主程序入口 ---
# 确保当这个脚本被直接执行时，才运行下面的代码
if __name__ == '__main__':
    # 调用函数，传入配置好的参数，开始执行测试流程
    analyze_image(SERVER_URL, IMAGE_PATH)
# --------------------

