# Dr.COM 校园网自动登录工具

## 文件说明

| 文件 | 说明 |
|------|------|
| `auto_login py.exe` | 可执行程序（双击运行，已内置 Edge 驱动） |
| `auto_login py.py` | Python 源代码 |

## 使用方式

1. 双击 `auto_login py.exe`
2. 首次运行输入用户名、密码
3. 凭据自动保存到 `auto_login_config.json`，以后直接双击即可自动登录

## 功能特性

- ✅ 自动填写用户名密码
- ✅ 自动勾选同意协议
- ✅ 检测"终端IP已在线"（避免重复登录）
- ✅ **内置 Edge 驱动，无需额外配置驱动文件**
- ✅ 支持离线环境

## 系统要求

- Windows 10/11
- 已安装 Microsoft Edge 浏览器

## 注意事项

- 配置文件 `auto_login_config.json` 会在首次运行时生成（与 exe 同级目录）
- **请勿将包含个人凭据的配置文件分享给他人**
- `auto_login py.exe` 已内置 `msedgedriver.exe`，无需额外放置驱动文件
