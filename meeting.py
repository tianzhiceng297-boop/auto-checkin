"""
自动入会模块 - 通过 URI Scheme 唤起腾讯会议客户端入会

支持：
- URI Scheme: tencentmeeting://join?meeting_id=xxx
- 入会后自静音、关摄像头
"""

import os
import subprocess
import time
import logging
import pyautogui
import pywinauto

logger = logging.getLogger(__name__)

# 腾讯会议 URI Scheme
TMEETING_URI = "tencentmeeting://join?meeting_id={meeting_id}&meeting_code_type=0"


class MeetingJoiner:
    """腾讯会议自动入会"""

    def __init__(self, auto_mute: bool = True, auto_close_camera: bool = True):
        self.auto_mute = auto_mute
        self.auto_close_camera = auto_close_camera
        # 安全设置
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True

    def join(self, meeting_code: str) -> bool:
        """
        通过 URI Scheme 加入会议

        Args:
            meeting_code: 会议码，如 "415-968-791"
        """
        try:
            # 去掉连字符，转为纯数字
            meeting_id = meeting_code.replace("-", "")

            uri = TMEETING_URI.format(meeting_id=meeting_id)
            logger.info(f"正在通过 URI 入会: {meeting_code}")

            # Windows 下使用 start 命令打开 URI
            os.startfile(uri)

            # 等待腾讯会议客户端响应
            time.sleep(3)

            # 尝试找到腾讯会议窗口并操作
            return self._post_join_actions(meeting_code)

        except Exception as e:
            logger.error(f"入会失败: {e}")
            return False

    def _post_join_actions(self, meeting_code: str) -> bool:
        """
        入会后的操作：点击加入会议、静音、关摄像头
        """
        try:
            app = pywinauto.Application(backend="uia").connect(
                path="WeMeet.exe", timeout=10
            )
        except Exception:
            logger.warning("未找到腾讯会议窗口，尝试继续...")
            return True

        try:
            # 查找"加入会议"按钮并点击
            main_window = app.window(class_name="WeMeetMainWnd")
            if main_window.exists(timeout=5):
                logger.info("找到腾讯会议主窗口")

                # 尝试点击"加入会议"按钮
                join_btn = main_window.child_window(
                    title="加入会议",
                    control_type="Button"
                )
                if join_btn.exists(timeout=5):
                    join_btn.click()
                    logger.info("已点击加入会议")
                    time.sleep(2)

            # 入会后静音和关摄像头
            if self.auto_mute:
                self._mute()
            if self.auto_close_camera:
                self._close_camera()

            logger.info(f"成功入会 {meeting_code}")
            return True

        except Exception as e:
            logger.warning(f"入会后操作失败（可能已成功入会）: {e}")
            return True  # URI 唤起本身就可能已经入会了

    def _mute(self):
        """静音"""
        try:
            # Alt+M 快捷键静音
            pyautogui.hotkey('alt', 'm')
            logger.info("已执行静音")
        except Exception as e:
            logger.warning(f"静音失败: {e}")

    def _close_camera(self):
        """关闭摄像头"""
        try:
            # Alt+V 快捷键关闭视频
            pyautogui.hotkey('alt', 'v')
            logger.info("已关闭摄像头")
        except Exception as e:
            logger.warning(f"关闭摄像头失败: {e}")

    def leave_meeting(self) -> bool:
        """离开当前会议"""
        try:
            # Alt+Q 或 Ctrl+W 退出会议
            pyautogui.hotkey('alt', 'q')
            time.sleep(1)
            # 确认退出
            pyautogui.press('enter')
            logger.info("已退出会议")
            return True
        except Exception as e:
            logger.error(f"退出会议失败: {e}")
            return False


# --- 测试 ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # 注意：运行测试会实际打开腾讯会议！
    # joiner = MeetingJoiner()
    # joiner.join("415-968-791")
    print("入会模块测试 - 不会实际入会（取消代码注释以测试）")
