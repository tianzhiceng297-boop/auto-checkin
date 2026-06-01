"""
自动入会模块 - 通过 URI Scheme 唤起腾讯会议客户端入会

支持：
- URI Scheme: tencentmeeting://join?meeting_id=xxx
- 入会后自静音、关摄像头
- 进程守护：自动检测并重启退出的腾讯会议
"""

import os
import subprocess
import time
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入 psutil，用于检测进程
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil 未安装，进程守护功能将不可用")
    logger.warning("请运行: pip install psutil")

# 腾讯会议 URI Scheme
MEETING_URI = "tencentmeeting://join?meeting_id={meeting_id}&meeting_code_type=0"

# 腾讯会议进程名
MEETING_PROCESS_NAMES = ["WeMeet.exe", "TencentMeeting.exe", "wemeet.exe"]

# 腾讯会议安装路径（常见）
MEETING_PATHS = [
    r"C:\Program Files (x86)\Tencent\WeMeet\WeMeet.exe",
    r"C:\Program Files\Tencent\WeMeet\WeMeet.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tencent\WeMeet\WeMeet.exe"),
]


class MeetingJoiner:
    """腾讯会议自动入会（支持进程守护）"""

    def __init__(self, auto_mute: bool = True, auto_close_camera: bool = True):
        self.auto_mute = auto_mute
        self.auto_close_camera = auto_close_camera
        self._current_meeting_code = None  # 当前会议码，用于重连
        self._daemon_running = False
        self._daemon_thread = None
        # 安全设置
        import pyautogui
        pyautogui.PAUSE = 0.5
        pyautogui.FAILSAFE = True

    def _check_meeting_process(self) -> bool:
        """
        检测腾讯会议进程是否在运行
        
        Returns:
            bool: 进程运行中返回 True
        """
        if not HAS_PSUTIL:
            logger.warning("psutil 未安装，无法检测进程")
            return True  # 假设进程正常运行

        try:
            for proc in psutil.process_iter(['name']):
                proc_name = proc.info['name']
                if proc_name and any(name.lower() in proc_name.lower() for name in MEETING_PROCESS_NAMES):
                    return True
            return False
        except Exception as e:
            logger.warning(f"检测腾讯会议进程失败: {e}")
            return True  # 检测失败时假设进程正常

    def _find_meeting_path(self) -> Optional[str]:
        """
        查找腾讯会议可执行文件路径
        
        Returns:
            str: 可执行文件路径，未找到返回 None
        """
        for path in MEETING_PATHS:
            if os.path.exists(path):
                return path
        return None

    def _start_meeting(self) -> bool:
        """
        启动腾讯会议客户端
        
        Returns:
            bool: 启动成功返回 True
        """
        meeting_path = self._find_meeting_path()
        if not meeting_path:
            logger.error("未找到腾讯会议安装路径")
            return False

        try:
            subprocess.Popen(meeting_path)
            logger.info(f"已启动腾讯会议: {meeting_path}")
            time.sleep(5)  # 等待客户端启动
            return True
        except Exception as e:
            logger.error(f"启动腾讯会议失败: {e}")
            return False

    def _rejoin_meeting(self) -> bool:
        """
        重新加入之前的会议
        
        Returns:
            bool: 重连成功返回 True
        """
        if not self._current_meeting_code:
            logger.warning("没有记录 previous 会议码，无法重连")
            return False

        logger.info(f"尝试重新加入会议: {self._current_meeting_code}")
        return self.join(self._current_meeting_code, is_rejoin=True)

    def start_daemon(self, check_interval: int = 30):
        """
        启动进程守护线程
        
        Args:
            check_interval: 检测间隔（秒）
        """
        if not HAS_PSUTIL:
            logger.error("psutil 未安装，无法启动进程守护")
            return

        if self._daemon_running:
            logger.warning("进程守护已在运行")
            return

        self._daemon_running = True

        def _daemon_loop():
            logger.info(f"腾讯会议进程守护已启动，检测间隔 {check_interval} 秒")
            while self._daemon_running:
                try:
                    if not self._check_meeting_process():
                        logger.warning("检测到腾讯会议进程已退出")
                        # 尝试重启
                        if self._start_meeting():
                            logger.info("腾讯会议已重启，尝试重新入会...")
                            time.sleep(10)  # 等待客户端完全启动
                            self._rejoin_meeting()
                        else:
                            logger.error("重启腾讯会议失败")
                except Exception as e:
                    logger.error(f"进程守护出错: {e}")

                # 等待下次检测
                for _ in range(check_interval):
                    if not self._daemon_running:
                        break
                    time.sleep(1)

            logger.info("腾讯会议进程守护已停止")

        self._daemon_thread = threading.Thread(target=_daemon_loop, daemon=True)
        self._daemon_thread.start()

    def stop_daemon(self):
        """停止进程守护"""
        self._daemon_running = False
        if self._daemon_thread:
            self._daemon_thread.join(timeout=5)
            logger.info("进程守护已停止")

    def join(self, meeting_code: str, is_rejoin: bool = False) -> bool:
        """
        通过 URI Scheme 加入会议
        
        Args:
            meeting_code: 会议码，如 "415-968-791"
            is_rejoin: 是否为重连入会
        """
        try:
            # 去掉连字符，转为纯数字
            meeting_id = meeting_code.replace("-", "")

            uri = MEETING_URI.format(meeting_id=meeting_id)
            logger.info(f"正在通过 URI 入会: {meeting_code}")

            # Windows 下使用 start 命令打开 URI
            os.startfile(uri)

            # 等待腾讯会议客户端响应
            time.sleep(3)

            # 尝试找到腾讯会议窗口并操作
            success = self._post_join_actions(meeting_code)

            # 记录当前会议码（用于重连）
            if success and not is_rejoin:
                self._current_meeting_code = meeting_code
                # 启动进程守护
                if HAS_PSUTIL and not self._daemon_running:
                    self.start_daemon()

            return success

        except Exception as e:
            logger.error(f"入会失败: {e}")
            return False

    def _post_join_actions(self, meeting_code: str) -> bool:
        """
        入会后的操作：点击加入会议、静音、关摄像头
        """
        try:
            import pywinauto
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
            import pyautogui
            # Alt+M 快捷键静音
            pyautogui.hotkey('alt', 'm')
            logger.info("已执行静音")
        except Exception as e:
            logger.warning(f"静音失败: {e}")

    def _close_camera(self):
        """关闭摄像头"""
        try:
            import pyautogui
            # Alt+V 快捷键关闭视频
            pyautogui.hotkey('alt', 'v')
            logger.info("已关闭摄像头")
        except Exception as e:
            logger.warning(f"关闭摄像头失败: {e}")

    def leave_meeting(self) -> bool:
        """离开当前会议"""
        try:
            import pyautogui
            # Alt+Q 或 Ctrl+W 退出会议
            pyautogui.hotkey('alt', 'q')
            time.sleep(1)
            # 确认退出
            pyautogui.press('enter')
            logger.info("已退出会议")
            # 清除当前会议记录
            self._current_meeting_code = None
            # 停止进程守护
            self.stop_daemon()
            return True
        except Exception as e:
            logger.error(f"退出会议失败: {e}")
            return False


# --- 测试 ---
if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # 注意：运行测试会实际打开腾讯会议！
    # joiner = MeetingJoiner()
    # joiner.join("415-968-791")
    print("入会模块测试 - 不会实际入会（取消代码注释以测试）")
