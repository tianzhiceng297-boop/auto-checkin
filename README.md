# 腾讯会议自动签到 (Auto Check-in)

自动监控微信群中的腾讯会议通知 → 定时入会 → 签到 → 自动离开

## 功能

- 监控微信群消息，自动提取会议码和会议时间
- 定时自动入会（提前 8 分钟）
- 入会后自静音、关摄像头
- 签到窗口（开始前5分钟~开始后5分钟）内自动检测弹窗
- 自动输入学号+姓名完成签到
- 签到成功后自动离开会议
- 签到失败通过微信通知

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，填入你的信息：

```yaml
student_id: "2024312250"
name: "曾天智"
wechat_group: "你的群名"
```

### 3. 提供签到弹窗截图

将腾讯会议签到弹窗截图保存为 `assets/checkin_popup.png`（模板匹配用）

### 4. 运行

```bash
python main.py
```

## 开机自启

运行 `install_autostart.bat`（需管理员权限），会将程序注册为 Windows 开机启动项。

## 项目结构

```
auto-checkin/
├── main.py              # 主程序入口
├── config.yaml          # 配置文件（学号、姓名、群名等）
├── requirements.txt     # Python 依赖
├── monitor.py           # 微信群消息监控 (wxauto)
├── parser.py            # 消息解析（正则提取会议信息）
├── scheduler.py         # 定时调度（创建/管理入会任务）
├── meeting.py           # 自动入会（URI Scheme）
├── checkin.py           # 签到检测与执行（OpenCV + pyautogui）
├── notifier.py          # 微信通知
├── assets/              # 模板图片
│   └── checkin_popup.png  # 签到弹窗截图（需要你提供）
├── logs/                # 运行日志
├── install_autostart.bat  # 开机自启安装脚本
└── start.bat            # 手动启动脚本
```
