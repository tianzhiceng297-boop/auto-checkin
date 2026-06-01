"""
微信群消息监控模块 (wxauto)

通过 Windows UI Automation 读取微信群消息。
微信窗口可最小化，但必须已打开过目标群聊。
"""

import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class WeChatMonitor:
    """微信群消息监控器"""

    def __init__(self, group_name: str, poll_interval: int = 5):
        """
        Args:
            group_name: 要监控的微信群名称
            poll_interval: 轮询间隔（秒）
        """
        self.group_name = group_name
        self.poll_interval = poll_interval
        self._wx = None
        self._last_message_time = None  # 上次已处理的消息时间，用于增量读取

    def connect(self):
        """连接到微信客户端"""
        try:
            from wxauto import WeChat
            self._wx = WeChat()
            logger.info("成功连接到微信客户端")
            return True
        except ImportError:
            logger.error("wxauto 未安装，请运行: pip install wxauto")
            return False
        except Exception as e:
            logger.error(f"连接微信失败: {e}")
            logger.error("请确保微信桌面客户端已打开并登录")
            return False

    def get_new_messages(self) -> list[dict]:
        """
        获取群内新消息（增量）

        Returns:
            [{"sender": "HL", "content": "腾讯会议号:415-968-791", "time": datetime}, ...]
        """
        if not self._wx:
            logger.error("微信未连接，请先调用 connect()")
            return []

        try:
            # 获取群聊消息
            messages = self._wx.GetGroupMessage(self.group_name)

            # 过滤出未处理的新消息
            new_messages = []
            for msg in messages:
                msg_time = self._parse_msg_time(msg)
                if self._last_message_time is None or msg_time > self._last_message_time:
                    new_messages.append({
                        "sender": msg.get("sender", ""),
                        "content": msg.get("content", ""),
                        "time": msg_time,
                    })

            if new_messages:
                self._last_message_time = new_messages[-1]["time"]
                logger.info(f"获取到 {len(new_messages)} 条新消息")

            return new_messages

        except Exception as e:
            logger.error(f"获取群消息失败: {e}")
            return []

    def get_recent_messages(self, minutes: int = 30) -> list[dict]:
        """
        获取最近N分钟内的消息（首次启动时使用）

        Args:
            minutes: 回溯多少分钟
        """
        if not self._wx:
            logger.error("微信未连接")
            return []

        try:
            messages = self._wx.GetGroupMessage(self.group_name)
            cutoff = datetime.now() - timedelta(minutes=minutes)

            recent = []
            for msg in messages:
                msg_time = self._parse_msg_time(msg)
                if msg_time >= cutoff:
                    recent.append({
                        "sender": msg.get("sender", ""),
                        "content": msg.get("content", ""),
                        "time": msg_time,
                    })

            if recent:
                self._last_message_time = recent[-1]["time"]
                logger.info(f"回溯到 {len(recent)} 条最近消息")

            return recent

        except Exception as e:
            logger.error(f"获取历史消息失败: {e}")
            return []

    def send_message(self, target: str, content: str) -> bool:
        """
        发送微信消息（用于通知）

        Args:
            target: 接收方（如 "文件传输助手"）
            content: 消息内容
        """
        if not self._wx:
            return False
        try:
            self._wx.SendMsg(content, target)
            logger.info(f"已发送消息到 {target}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

    def _parse_msg_time(self, msg) -> datetime:
        """解析消息时间"""
        if isinstance(msg, dict):
            t = msg.get("time", msg.get("msg_time", None))
            if isinstance(t, datetime):
                return t
            if isinstance(t, str):
                try:
                    return datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
        return datetime.now()

    def is_connected(self) -> bool:
        return self._wx is not None


# --- 测试 ---
if __name__ == "__main__":
    import yaml

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # 加载配置
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    group = config["wechat_group"]
    print(f"开始监控群: {group}")

    monitor = WeChatMonitor(group)
    if monitor.connect():
        print("连接成功！正在获取最近消息...")
        msgs = monitor.get_recent_messages(minutes=60)
        for m in msgs:
            print(f"  [{m['time']}] {m['sender']}: {m['content'][:80]}")
    else:
        print("连接失败，请检查微信是否已打开")
