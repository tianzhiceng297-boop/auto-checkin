# 腾讯会议自动签到 (Auto Check-in)

![GitHub](https://img.shields.io/badge/license-MIT-green)
![GitHub stars](https://img.shields.io/github/stars/tianzhiceng297-boop/auto-checkin)
[![GitHub](https://img.shields.io/badge/View%20on%20GitHub-black?logo=github)](https://github.com/tianzhiceng297-boop/auto-checkin)

自动监控微信群中的腾讯会议通知 → 定时入会 → 签到 → 自动离开。

## 功能

- 监控微信群消息，自动提取会议码和会议时间
- 定时自动入会（提前 8 分钟）
- 入会后自静音、关摄像头
- 签到窗口（开始前5分钟 ~ 开始后5分钟）内自动检测弹窗
- 自动输入学号+姓名完成签到
- 签到成功后自动离开会议
- 签到失败通过微信通知

## 工作流程

```
微信群消息 → wxauto4 读取 → 正则解析会议码+时间
                                    │
                                    ▼
                            APScheduler 定时调度
                                    │
                                    ▼
                             URI Scheme 入会
                                    │
                                    ▼
                          OpenCV 检测签到弹窗
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
             签到成功                           签到失败
             输入学号+姓名 → 提交              等待超时（开始后5分钟）
                  │                               │
                  ▼                               ▼
             自动离开会议                     微信通知你
```

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Python | 3.9 - 3.12 | wxauto4 不支持 3.13+ |
| Windows | 10/11 | 需要微信桌面客户端 + 腾讯会议客户端 |
| 微信 | 最新版 | 桌面客户端，需已登录 |
| 腾讯会议 | 最新版 | 桌面客户端 |

## 快速开始

### 1. 安装 Python 3.12

如果已有 Python 3.13，需要额外安装 3.12（[下载地址](https://www.python.org/downloads/)）。

推荐使用虚拟环境：

```bash
# 创建虚拟环境（Python 3.12）
python3.12 -m venv venv

# Windows
venv\Scripts\activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

依赖清单：

| 包 | 用途 |
|---|------|
| wxauto4 | 微信 UI Automation，读取群消息 |
| pyautogui | 截图、模拟点击、键盘输入 |
| pywinauto | Windows 窗口操作备用方案 |
| opencv-python | 签到弹窗图像识别 |
| numpy | 图像处理 |
| PyYAML | 配置文件解析 |
| APScheduler | 定时任务调度 |

### 3. 配置

复制示例配置文件并填入你的信息：

```bash
cp config.example.yaml config.yaml
```

编辑 `config.yaml`：

```yaml
# === 个人信息 ===
student_id: "你的学号"
name: "你的姓名"

# === 微信群设置 ===
wechat_group: "你的微信群名"

# === 签到设置 ===
checkin_advance_minutes: 8    # 提前多少分钟入会
checkin_window_before: 5       # 会议开始前多久开始检测签到
checkin_window_after: 5       # 会议开始后多久停止检测
poll_interval: 5              # 微信群消息轮询间隔（秒）
screenshot_interval: 1        # 签到弹窗检测间隔（秒）
```

### 4. 提供签到弹窗截图

将腾讯会议签到弹窗截图保存为 `assets/checkin_popup.png`。

> 这是 OpenCV 模板匹配的关键文件，脚本会对比屏幕截图与该模板来判定签到弹窗是否出现。

### 5. 运行

**手动启动：**

```bash
python main.py
```

**或双击启动脚本：**

```
start.bat
```

## 开机自启

运行 `install_autostart.bat`（需管理员权限），将程序注册为 Windows 开机启动项。

## 项目结构

```
auto-checkin/
├── main.py              # 主程序入口，协调各模块
├── config.yaml          # 配置文件（个人信息、群名等）
├── config.example.yaml  # 配置文件模板
├── requirements.txt      # Python 依赖
├── monitor.py           # 微信群消息监控 (wxauto4)
├── parser.py            # 消息解析（正则提取会议码、时间、课程名）
├── scheduler.py         # 定时调度（创建/管理入会任务）
├── meeting.py           # 自动入会（URI Scheme 唤起客户端）
├── checkin.py           # 签到检测与执行（OpenCV + pyautogui）
├── notifier.py          # 微信通知（发送到文件传输助手）
├── assets/              # 资源文件
│   └── checkin_popup.png  # 签到弹窗截图（需用户提供）
├── logs/                # 运行日志（自动生成）
├── start.bat            # 手动启动脚本
├── install_autostart.bat # 开机自启安装脚本
└── .gitignore
```

## 版本历史

| 版本 | 发布日期 | 核心功能 | Tag |
|------|---------|---------|-----|
| V1.1 | 2026-06-02 | 稳定性加固：微信重连 + 会议进程守护 + 多模板支持 + 日志轮转 | [v1.1](https://github.com/tianzhiceng297-boop/auto-checkin/tree/v1.1) |
| V1.0 | 2026-06-01 | 基础功能：群监控 + 解析 + 定时入会 + pywinauto签到 + 微信通知 | [v1.0](https://github.com/tianzhiceng297-boop/auto-checkin/tree/v1.0) |

> 💡 如需回退到旧版本：`git checkout v1.0`

## 注意事项

- 微信窗口必须保持打开（可最小化），且目标群聊至少打开过一次
- 腾讯会议客户端需要提前安装好
- 签到弹窗截图需要手动提供（腾讯会议 UI 更新后需重新截图）
- config.yaml 包含个人信息，已被 .gitignore 排除

## 免责声明

本项目仅供学习交流使用。自动签到行为可能违反腾讯会议服务条款，使用者需自行承担相关风险。
