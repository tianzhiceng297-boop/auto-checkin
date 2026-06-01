"""
签到检测与执行模块

在会议中通过 OpenCV 模板匹配检测签到弹窗，
识别到后自动输入学号+姓名并提交。
"""

import os
import time
import logging
import pyautogui
import cv2
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 签到弹窗模板图片路径
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "assets", "checkin_popup.png")

# 占位模板（TODO: 替换为真实截图）
# 生成一个简单的占位图，提醒用户替换
def _create_placeholder_template():
    """创建占位模板图片"""
    if os.path.exists(TEMPLATE_PATH):
        return
    os.makedirs(os.path.dirname(TEMPLATE_PATH), exist_ok=True)
    # 创建一个空白占位图
    placeholder = np.zeros((100, 400, 3), dtype=np.uint8)
    cv2.putText(
        placeholder,
        "TODO: replace with real checkin popup screenshot",
        (10, 55),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (255, 255, 255),
        1,
    )
    cv2.imwrite(TEMPLATE_PATH, placeholder)
    logger.warning(f"已创建占位模板图片: {TEMPLATE_PATH}")
    logger.warning("请用真实的腾讯会议签到弹窗截图替换此文件！")


class CheckinDetector:
    """签到检测器"""

    def __init__(
        self,
        checkin_text: str,
        check_interval: int = 1,
        window_before_minutes: int = 5,
        window_after_minutes: int = 5,
        template_threshold: float = 0.8,
        auto_leave: bool = True,
    ):
        """
        Args:
            checkin_text: 签到时输入的文本（学号+姓名）
            check_interval: 检测间隔（秒）
            window_before_minutes: 会议开始前几分钟开始检测
            window_after_minutes: 会议开始后几分钟停止检测
            template_threshold: 模板匹配置信度阈值
            auto_leave: 签到成功后是否自动离开
        """
        self.checkin_text = checkin_text
        self.check_interval = check_interval
        self.window_before_minutes = window_before_minutes
        self.window_after_minutes = window_after_minutes
        self.template_threshold = template_threshold
        self.auto_leave = auto_leave

        # pyautogui 安全设置
        pyautogui.PAUSE = 0.3
        pyautogui.FAILSAFE = True

        # 加载模板图片
        self.template = None
        self.template_h = 0
        self.template_w = 0
        _create_placeholder_template()
        self._load_template()

    def _load_template(self):
        """加载签到弹窗模板图片"""
        if not os.path.exists(TEMPLATE_PATH):
            logger.error(f"模板图片不存在: {TEMPLATE_PATH}")
            return

        self.template = cv2.imread(TEMPLATE_PATH)
        if self.template is None:
            logger.error("模板图片加载失败")
            return

        self.template_h, self.template_w = self.template.shape[:2]
        logger.info(f"模板图片已加载: {self.template_w}x{self.template_h}")

    def is_template_ready(self) -> bool:
        """检查模板图片是否为真实截图（非占位图）"""
        if self.template is None:
            return False
        # 占位图是 100x400 的黑底白字
        if self.template_h == 100 and self.template_w == 400:
            return False
        return True

    def detect_popup(self) -> tuple[int, int] | None:
        """
        检测屏幕上是否存在签到弹窗

        Returns:
            弹窗左上角坐标 (x, y)，如果未检测到返回 None
        """
        if self.template is None:
            return None

        # 截取全屏
        screenshot = pyautogui.screenshot()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # 模板匹配
        result = cv2.matchTemplate(screen, self.template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= self.template_threshold:
            logger.info(f"检测到签到弹窗! 置信度: {max_val:.2f}, 位置: {max_loc}")
            return max_loc  # (x, y) 左上角

        return None

    def do_checkin(self, popup_pos: tuple[int, int]) -> bool:
        """
        执行签到操作

        Args:
            popup_pos: 签到弹窗左上角坐标 (x, y)

        Returns:
            是否签到成功
        """
        try:
            x, y = popup_pos

            # 点击弹窗中的输入框（弹窗中间偏下的位置）
            input_x = x + self.template_w // 2
            input_y = y + self.template_h // 2 + 30  # 偏移到输入框

            pyautogui.click(input_x, input_y)
            time.sleep(0.5)

            # 清空已有内容并输入学号+姓名
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.typewrite(self.checkin_text, interval=0.05)
            time.sleep(0.5)

            # 点击提交按钮（弹窗底部）
            submit_x = x + self.template_w // 2
            submit_y = y + self.template_h - 40
            pyautogui.click(submit_x, submit_y)
            time.sleep(1)

            logger.info(f"签到文本已输入: {self.checkin_text}")
            return True

        except pyautogui.FailSafeException:
            logger.error("签到操作被安全中断（鼠标移至屏幕角落）")
            return False
        except Exception as e:
            logger.error(f"签到操作失败: {e}")
            return False

    def watch_and_checkin(self, meeting_start: datetime, leave_callback=None) -> bool:
        """
        在签到窗口内持续监控并执行签到

        Args:
            meeting_start: 会议开始时间
            leave_callback: 签到成功后的回调（如离开会议）

        Returns:
            是否签到成功
        """
        if not self.is_template_ready():
            logger.error("模板图片未准备好，请替换占位图！")
            return False

        # 计算检测窗口
        window_start = meeting_start - timedelta(minutes=self.window_before_minutes)
        window_end = meeting_start + timedelta(minutes=self.window_after_minutes)
        now = datetime.now()

        if now < window_start:
            wait_seconds = (window_start - now).total_seconds()
            logger.info(f"签到窗口未到，等待 {wait_seconds/60:.0f} 分钟后开始检测")
            time.sleep(min(wait_seconds, 60))  # 最多等60秒再检查

        logger.info(
            f"开始检测签到弹窗 "
            f"(窗口: {window_start.strftime('%H:%M')} ~ {window_end.strftime('%H:%M')})"
        )

        while datetime.now() <= window_end:
            popup_pos = self.detect_popup()
            if popup_pos:
                success = self.do_checkin(popup_pos)
                if success:
                    logger.info("签到成功!")
                    if self.auto_leave and leave_callback:
                        time.sleep(2)
                        leave_callback()
                    return True
                else:
                    logger.warning("签到操作失败，继续尝试...")

            time.sleep(self.check_interval)

        logger.warning("签到窗口已过，未检测到签到弹窗")
        return False
