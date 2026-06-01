# Changelog

## [Unreleased]

### Added
- README 版本历史表格

---

## [V1.1] - 2026-06-02

### Added
- 微信重连机制（`monitor.py` 心跳检测 + 自动重连）
- 腾讯会议进程守护（`meeting.py` 后台检测 + 异常通知）
- 签到弹窗多模板支持（`assets/templates/` 目录，OpenCV 多模板匹配）
- 日志轮转（`RotatingFileHandler`，单文件 10MB，保留 5 个备份）

### Fixed
- `monitor.py` 语法错误（重复 try 块）
- `checkin.py` 文件截断问题
- `checkin.py` 使用 pywinauto 直接定位 UI 控件，替代脆弱的模板匹配

### Changed
- 签到流程改为 pywinauto UI 自动化（两步：点「加入」→ 输入学号姓名 → 提交）

---

## [V1.0] - 2026-06-01

### Added
- 微信群监控（`wxauto4` 读取群消息）
- 会议号解析（正则提取 txt/doc/docx 中的会议码 + 时间）
- 定时调度（APScheduler，会前 5 分钟自动入会）
- 自动入会（腾讯会议 URI Scheme 唤起客户端）
- 签到检测（OpenCV 模板匹配检测弹窗）
- 自动输入学号 + 姓名提交签到
- 签到成功自动离开会议
- 微信通知（签到失败发送到文件传输助手）
- 配置文件化管理（`config.yaml`）
- 日志系统（按日期存储到 `logs/`）
- 开机自启脚本（`install_autostart.bat`）

### Known Issues
- `wxauto4` 不支持 Python 3.13，需使用 Python 3.12
- 签到依赖截图模板，腾讯会议 UI 更新后需重新截图
- 仅支持"输入学号+姓名"类型的签到，不支持简单点击签到

---

## Version Numbering

- **Major（X.0.0）**：不兼容的架构变更
- **Minor（1.X.0）**：向后兼容的功能新增
- **Patch（1.0.X）**：向后兼容的问题修复

当前项目处于早期阶段，版本号从 V1.0 开始。
