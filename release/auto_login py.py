import sys
import time
import os
import json
import msvcrt

# 禁用 Selenium Manager 自动下载驱动（确保离线环境正常工作）
# 注意：SE_MANAGER_PATH 必须指向实际文件或删除，不能设为 0
os.environ.pop('SE_MANAGER_PATH', None)  # 删除可能存在的错误配置
os.environ['SE_MANAGER_LOG_LEVEL'] = 'error'  # 只显示错误日志

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException


# --- 配置 ---
# 支持 PyInstaller 打包后的临时目录
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后，资源文件在 _MEIPASS 临时目录
    BUNDLE_DIR = sys._MEIPASS
    # 配置文件放在 exe 同级目录（持久化保存）
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR = BUNDLE_DIR

CONFIG_FILE = os.path.join(CONFIG_DIR, 'auto_login_config.json')
LOGIN_URL = 'http://172.16.253.3/'
MAX_RETRIES = 3
WAIT_TIMEOUT = 10  # 单个元素等待上限


def get_password_with_mask(prompt='密码: '):
    """使用 * 号回显的方式获取密码输入（Windows）"""
    print(prompt, end='', flush=True)
    password = ''
    while True:
        ch = msvcrt.getch().decode('utf-8', errors='ignore')
        if ch == '\r' or ch == '\n':  # Enter 键
            print()
            break
        elif ch == '\x08' or ch == '\x7f':  # Backspace 键
            if password:
                password = password[:-1]
                print('\b \b', end='', flush=True)
        elif ch == '\x03':  # Ctrl+C
            raise KeyboardInterrupt
        elif ch.isprintable():
            password += ch
            print('*', end='', flush=True)
    return password


def load_or_create_config():
    """加载已保存的凭据，首次运行时提示用户输入并保存。"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)

    print('首次使用，请输入登录凭据：')
    username = input('用户名: ').strip()
    password = get_password_with_mask('密码: ')
    confirm_password = get_password_with_mask('确认密码: ')
    while password != confirm_password:
        print('两次输入的密码不一致，请重新输入！')
        password = get_password_with_mask('密码: ')
        confirm_password = get_password_with_mask('确认密码: ')

    config = {'username': username, 'password': password}
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)
    try:
        os.chmod(CONFIG_FILE, 0o600)  # Unix: 仅当前用户可读写
    except (AttributeError, NotImplementedError):
        pass  # Windows 下忽略
    print(f'凭据已保存到 {CONFIG_FILE}')
    return config


def login(username, password):
    options = Options()
    # 优先查找打包内置的 Edge 便携版/便携驱动
    edge_binary = os.path.join(BUNDLE_DIR, 'edge', 'msedge.exe')
    edgedriver_path = os.path.join(BUNDLE_DIR, 'edgedriver', 'msedgedriver.exe')

    if os.path.exists(edge_binary):
        options.binary_location = edge_binary
    # 页面交互元素就绪即继续，不等图片/样式等资源
    options.page_load_strategy = 'eager'

    # 使用本地 msedgedriver（exe 同级目录优先，支持离线/便携环境）
    if os.path.exists(edgedriver_path):
        service = Service(executable_path=edgedriver_path)
        print('即将自动打开浏览器，请勿关闭脚本...')
        driver = webdriver.Edge(service=service, options=options)
    else:
        # 若同级目录没有内置驱动，让 Selenium 自动从 PATH/SeleniumManager 获取
        print('即将自动打开浏览器，请勿关闭脚本...')
        driver = webdriver.Edge(options=options)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        for attempt in range(1, MAX_RETRIES + 1):
            print(f'[尝试 {attempt}/{MAX_RETRIES}] 打开登录页面...')
            driver.get(LOGIN_URL)

            # 等待用户名输入框出现，替代固定 sleep(5)
            try:
                # 查找可见的用户名输入框（排除 type=hidden）
                username_field = wait.until(
                    lambda d: d.find_element(By.XPATH, '//input[@name="DDDDD" and @type!="hidden"]')
                )
            except TimeoutException:
                # 如果找不到用户名输入框，检查是否真的已登录（成功页面特征）
                page = driver.page_source
                current_url = driver.current_url
                print(f'超时！当前URL: {current_url}')
                print(f'页面内容前500字符: {page[:500]}')
                
                # 严格判断：必须同时满足 URL 包含 3.htm 且页面有明确的登录成功标识
                is_really_logged_in = (
                    '3.htm' in current_url and
                    'Dr.COMWebLoginID_3' in page and
                    'DDDDD' not in page  # 登录成功页不应该有用户名输入框
                ) or '终端ip已在线' in page or '终端IP已在线' in page  # 重复登录/终端已在线也视为已登录
                if is_really_logged_in:
                    print('已经处于登录状态，无需重新登录。')
                    return True
                print('错误: 页面加载超时，找不到用户名输入框')
                continue

            # 填写用户名
            username_field.clear()
            username_field.send_keys(username)
            print('已填写用户名')

            # 填写密码
            password_field = wait.until(
                lambda d: d.find_element(By.XPATH, '//input[@name="upass" and @type!="hidden"]')
            )
            password_field.clear()
            password_field.send_keys(password)
            print('已填写密码')

            # 勾选同意协议复选框（如果存在）
            try:
                checkbox = driver.find_element(By.NAME, 'C1')
                if checkbox.is_displayed() and not checkbox.is_selected():
                    checkbox.click()
                    print('已勾选同意协议')
            except Exception:
                pass

            # 点击登录按钮
            login_btn = wait.until(
                lambda d: d.find_element(By.XPATH, '//input[@name="0MKKey" and @type!="hidden"]')
            )
            login_btn.click()
            print('已点击登录按钮')

            # 等待结果页出现，替代固定 sleep(3)
            try:
                wait.until(
                    lambda d: any(kw in d.page_source for kw in ('Dr.COMWebLoginID_3', 'Dr.COMWebLoginID_2'))
                )
            except TimeoutException:
                pass

            page = driver.page_source
            current_url = driver.current_url

            # 新增：检测"终端ip已在线"（重复登录）
            if '终端ip已在线' in page or '终端IP已在线' in page:
                print('检测到终端IP已在线（重复登录），当前设备已处于登录状态。')
                return True  # 视为成功，不需要重新登录

            if 'Dr.COMWebLoginID_3' in page or '3.htm' in page or '3.htm' in current_url:
                print('登录成功!')
                return True
            elif 'Dr.COMWebLoginID_2' in page or '2.htm' in page:
                print('登录失败，页面返回错误。')
                body_text = driver.find_element(By.TAG_NAME, 'body').text
                if '验证码' in body_text:
                    print('检测到验证码，无法自动处理。请手动输入验证码后重试。')
                print(f'页面提示: {body_text[:300]}')
            else:
                print(f'未知响应，当前URL: {current_url}')

            if attempt < MAX_RETRIES:
                print('等待 2 秒后重试...')
                time.sleep(2)

        print(f'已尝试 {MAX_RETRIES} 次，登录失败。')
        return False

    except WebDriverException as e:
        print(f'浏览器错误: {e}')
        return False
    finally:
        print('浏览器即将关闭...')
        time.sleep(2)
        driver.quit()


if __name__ == '__main__':
    print('=' * 40)
    print('Dr.COM 校园网自动登录')
    print('=' * 40)
    config = load_or_create_config()
    success = login(config['username'], config['password'])
    sys.exit(0 if success else 1)
