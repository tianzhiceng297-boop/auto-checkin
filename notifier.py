"""
通知模块 - 通过微信发送签到结果通知
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class Notifier:
    """微信通知器"""

    def __init__(self, wechat_monitor=None, notify_target: str = "文件传输助手",
                 on_success: bool = True, on_failure: bool = True):
        """
        Args:
            wechat_monitor: WeChatMonitor 实例（复用微信连接）
            notify_target: 通知接收方
            on_success: 签到成功时是否通知
            on_failure: 签到失败时是否通知
        """
        self.monitor = wechat_monitor
        self.notify_target = notify_target
        self.on_success = on_success
        self.on_failure = on_failure

    def notify_checkin_success(self, meeting_info, checkin_time: datetime = None):
        """通知签到成功"""
        if not self.on_success:
            return

        msg = (
            f"[自动签到] 签到成功\n"
            f"课程: {meeting_info.course_name}\n"
            f"会议号: {meeting_info.meeting_code}\n"
            f"时间: {meeting_info.start_time}-{meeting_info.end_time}\n"
            f"签到时间: {(checkin_time or datetime.now()).strftime('%H:%M:%S')}\n"
            f"状态: 已自动离开会议"
        )
        self._send(msg)

    def notify_checkin_failure(self, meeting_info, reason: str = "未检测到签到弹窗"):
        """通知签到失败"""
        if not self.on_failure:
            return

        msg = (
            f"[自动签到] 签到失败\n"
            f"课程: {meeting_info.course_name}\n"
            f"会议号: {meeting_info.meeting_code}\n"
            f"时间: {meeting_info.start_time}-{meeting_info.end_time}\n"
            f"失败原因: {reason}\n"
            f"请手动签到!"
        )
        self._send(msg)

    def notify_join_success(self, meeting_info):
        """通知入会成功"""
        msg = (
            f"[自动签到] 已入会\n"
            f"课程: {meeting_info.course_name}\n"
            f"会议号: {meeting_info.meeting_code}\n"
            f"正在等待签到..."
        )
        self._send(msg)

    def notify_join_failure(self, meeting_code: str, reason: str):
        """通知入会失败"""
        msg = (
            f"[自动签到] 入会失败\n"
            f"会议号: {meeting_code}\n"
            f"原因: {reason}\n"
            f"请手动入会!"
        )
        self._send(msg)

    def notify_new_meeting_found(self, meeting_info):
        """通知发现新会议"""
        msg = (
            f"[自动签到] 发现新会议\n"
            f"课程: {meeting_info.course_name}\n"
            f"会议号: {meeting_info.meeting_code}\n"
            f"时间: {meeting_info.date_str} {meeting_info.start_time}-{meeting_info.end_time}\n"
            f"将于会议开始前自动入会"
        )
        self._send(msg)

    def _send(self, msg: str):
        """发送通知"""
        if self.monitor and self.monitor.is_connected():
            self.monitor.send_message(self.notify_target, msg)
        else:
            # 降级：使用系统通知
            logger.warning("微信未连接，使用系统日志代替通知")
            logger.info(f"[通知] {msg}")
