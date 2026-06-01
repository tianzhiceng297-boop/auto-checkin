"""
主程序入口 - 腾讯会议自动签到

运行流程:
1. 加载配置
2. 连接微信，开始监控群消息
3. 解析消息中的会议信息
4. 定时自动入会
5. 入会后检测签到弹窗并自动签到
6. 签到成功后自动离开，失败则通知
"""

import os
import sys
import signal
import time
import logging
import yaml
from datetime import datetime

from monitor import WeChatMonitor
from parser import parse_message, is_meeting_notification, MeetingInfo
from scheduler import MeetingScheduler
from meeting import MeetingJoiner
from checkin import CheckinDetector
from notifier import Notifier


def load_config(path: str = "config.yaml") -> dict:
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), path)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging():
    """配置日志"""
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"auto_checkin_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return logging.getLogger(__name__)


class AutoCheckin:
    """自动签到主控制器"""

    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 初始化各模块
        self.monitor = WeChatMonitor(
            group_name=config["wechat_group"],
            poll_interval=config["monitor"]["poll_interval"],
        )
        self.scheduler = MeetingScheduler(
            join_advance_minutes=config["meeting"]["join_advance_minutes"],
        )
        self.joiner = MeetingJoiner(
            auto_mute=config["meeting"]["auto_mute"],
            auto_close_camera=config["meeting"]["auto_close_camera"],
        )
        self.detector = CheckinDetector(
            checkin_text=config["checkin_text"],
            check_interval=config["checkin"]["check_interval"],
            window_before_minutes=config["checkin"]["window_before_minutes"],
            window_after_minutes=config["checkin"]["window_after_minutes"],
            template_threshold=config["checkin"]["template_threshold"],
            auto_leave=config["checkin"]["auto_leave_after_checkin"],
        )
        self.notifier = Notifier(
            wechat_monitor=self.monitor,
            notify_target=config["notify"]["notify_target"],
            on_success=config["notify"]["on_success"],
            on_failure=config["notify"]["on_failure"],
        )

        self._running = False

    def start(self):
        """启动自动签到"""
        self.logger.info("=" * 60)
        self.logger.info("腾讯会议自动签到 启动")
        self.logger.info(f"学号: {self.config['student_id']}")
        self.logger.info(f"姓名: {self.config['name']}")
        self.logger.info(f"监控群: {self.config['wechat_group']}")
        self.logger.info("=" * 60)

        # 检查模板图片
        if not self.detector.is_template_ready():
            self.logger.warning(
                "签到弹窗模板图片未准备好! "
                "请将真实截图保存为 assets/checkin_popup.png"
            )
            self.logger.warning("监控和调度功能仍可正常工作，但签到检测需要模板图片")

        # 连接微信
        if not self.monitor.connect():
            self.logger.error("无法连接微信，程序退出")
            return

        # 首次启动：回溯检查最近消息
        lookback = self.config["monitor"]["lookback_minutes"]
        self.logger.info(f"回溯检查最近 {lookback} 分钟的消息...")
        recent_msgs = self.monitor.get_recent_messages(minutes=lookback)
        self._process_messages(recent_msgs)

        # 进入主循环
        self._running = True
        self._main_loop()

    def _main_loop(self):
        """主监控循环"""
        self.logger.info("进入主监控循环...")

        while self._running:
            try:
                # 轮询新消息
                new_msgs = self.monitor.get_new_messages()
                if new_msgs:
                    self._process_messages(new_msgs)

                # 打印已调度的会议
                scheduled = self.scheduler.get_scheduled_meetings()
                if scheduled:
                    for code, info in scheduled.items():
                        remain = (info.datetime_obj - datetime.now()).total_seconds() / 60
                        if remain > 0:
                            self.logger.info(
                                f"待入会: [{info.course_name}] {code} "
                                f"还有 {remain:.0f} 分钟"
                            )

                time.sleep(self.config["monitor"]["poll_interval"])

            except KeyboardInterrupt:
                self.logger.info("收到中断信号，正在停止...")
                break
            except Exception as e:
                self.logger.error(f"主循环异常: {e}", exc_info=True)
                time.sleep(10)  # 出错后等待10秒再继续

        self.shutdown()

    def _process_messages(self, messages: list[dict]):
        """处理消息列表，提取会议信息"""
        for msg in messages:
            content = msg["content"]
            if not is_meeting_notification(content):
                continue

            self.logger.info(f"发现会议相关消息: {content[:80]}...")
            meetings = parse_message(content)

            for meeting in meetings:
                self._on_meeting_found(meeting)

    def _on_meeting_found(self, meeting: MeetingInfo):
        """发现新会议"""
        self.logger.info(f"解析到会议: {meeting}")

        # 添加到调度
        added = self.scheduler.add_meeting(meeting, join_callback=self._on_join_trigger)
        if added:
            self.notifier.notify_new_meeting_found(meeting)

    def _on_join_trigger(self, meeting: MeetingInfo):
        """定时触发入会"""
        self.logger.info(f"触发入会: {meeting.meeting_code}")

        success = self.joiner.join(meeting.meeting_code)
        if success:
            self.notifier.notify_join_success(meeting)

            # 开始检测签到
            checkin_success = self.detector.watch_and_checkin(
                meeting_start=meeting.datetime_obj,
                leave_callback=lambda: self.joiner.leave_meeting(),
            )

            if checkin_success:
                self.notifier.notify_checkin_success(meeting)
            else:
                self.notifier.notify_checkin_failure(meeting)
                self.joiner.leave_meeting()

            # 从调度中移除
            self.scheduler.remove_meeting(meeting.meeting_code)
        else:
            self.notifier.notify_join_failure(meeting.meeting_code, "URI 唤起失败")

    def shutdown(self):
        """关闭程序"""
        self._running = False
        self.scheduler.shutdown()
        self.logger.info("程序已停止")


def main():
    logger = setup_logging()

    # 加载配置
    try:
        config = load_config()
    except FileNotFoundError:
        logger.error("配置文件 config.yaml 不存在! 请从 config.example.yaml 复制并修改")
        sys.exit(1)
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        sys.exit(1)

    # 启动
    app = AutoCheckin(config)

    # 优雅退出
    def signal_handler(sig, frame):
        logger.info("收到退出信号")
        app.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app.start()


if __name__ == "__main__":
    main()
