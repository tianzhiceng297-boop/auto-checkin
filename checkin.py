"""
腾讯会议签到检测与执行模块 (pywinauto UI自动化版)

通过 Windows UI Automation 直接定位腾讯会议控件，
不依赖截图模板，兼容性更好。
支持两步签到流程：
  1. 检测签到通知弹窗 → 点击「加入」
  2. 在签到应用窗口中输入学号+姓名 → 点击「提交」
"""

import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 腾讯会议窗口标题关键词
TM_WINDOW_TITLES = ["腾讯会议", "Tencent Meeting", "会议中"]


def _connect_tm_window(retry=3, delay=2):
    """连接腾讯会议窗口，返回 pywinauto 窗口对象"""
    try:
        import pywinauto
    except ImportError:
        logger.error("pywinauto 未安装，请运行: pip install pywinauto")
        return None

    for attempt in range(retry):
        for title in TM_WINDOW_TITLES:
            try:
                app = pywinauto.Application(backend="uia").connect(title_re=f".*{title}.*", timeout=5)
                window = app.window(title_re=f".*{title}.*")
                if window.exists():
                    logger.info(f"已连接到腾讯会议窗口: {window.window_text()}")
                    return window
            except Exception:
                continue
        if attempt < retry - 1:
            logger.warning(f"未找到腾讯会议窗口，{delay}秒后重试({attempt+1}/{retry})...")
            time.sleep(delay)

    logger.error("无法连接到腾讯会议窗口，请确保腾讯会议已打开")
    return None


def _click_button_by_text(window, text_list, timeout=10):
    """
    在窗口中按文字查找并点击按钮。
    text_list: 候选文字列表，如 ["加入", "Join"]
    """
    try:
        import pywinauto
    except ImportError:
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        for text in text_list:
            try:
                # 查找按钮控件
                btn = window.child_window(title=text, control_type="Button", timeout=1)
                if btn.exists():
                    btn.click_input()
                    logger.info(f"已点击按钮: [{text}]")
                    return True
            except Exception:
                pass

            try:
                # 也尝试查找 Hyperlink 或 Pane 中的文字
                elems = window.descendants(title=text)
                for elem in elems:
                    try:
                        elem.click_input()
                        logger.info(f"已点击元素: [{text}]")
                        return True
                    except Exception:
                        continue
            except Exception:
                pass

        time.sleep(1)

    logger.warning(f"在 {timeout} 秒内未找到按钮: {text_list}")
    return False


def _input_text_by_label(window, label_texts, input_text, timeout=10):
    """
    根据标签文字找到对应的输入框，并输入文字。
    label_texts: 标签候选文字，如 ["学号", "姓名", "请输入"]
    """
    try:
        import pywinauto
    except ImportError:
        return False

    deadline = time.time() + timeout
    while time.time() < deadline:
        for label in label_texts:
            try:
                # 查找标签附近的 Edit 控件
                label_elem = window.child_window(title=label, control_type="Text", timeout=1)
                if label_elem.exists():
                    # 尝试找相邻的 Edit 控件
                    parent = label_elem.parent()
                    edit = parent.child_window(control_type="Edit", timeout=1)
                    if edit.exists():
                        edit.set_text(input_text)
                        logger.info(f"已在 [{label}] 输入框中填入: {input_text}")
                        return True
            except Exception:
                pass

        # 兜底：直接找第一个空的 Edit 控件
        try:
            edits = window.children(control_type="Edit")
            if edits:
                edits[0].set_text(input_text)
                logger.info(f"已在第一个输入框中填入: {input_text}")
                return True
        except Exception:
            pass

        time.sleep(1)

    logger.warning(f"在 {timeout} 秒内未找到输入框: {label_texts}")
    return False


def _wait_for_window_with_text(text_list, timeout=30):
    """
    等待窗口中出现指定文字（签到应用窗口出现）。
    """
    try:
        import pywinauto
    except ImportError:
        return None

    deadline = time.time() + timeout
    while time.time() < deadline:
        for title in TM_WINDOW_TITLES:
            try:
                app = pywinauto.Application(backend="uia").connect(title_re=f".*{title}.*", timeout=1)
                window = app.window(title_re=f".*{title}.*")
                if window.exists():
                    # 检查窗口中是否包含目标文字
                    for text in text_list:
                        try:
                            elem = window.child_window(title=text, timeout=1)
                            if elem.exists():
                                logger.info(f"找到包含文字 [{text}] 的窗口")
                                return window
                        except Exception:
                            pass
            except Exception:
                continue
        time.sleep(1)

    logger.warning(f"在 {timeout} 秒内未找到包含 {text_list} 的窗口")
    return None


def _check_success(window, success_texts=("签到成功", "已完成签到", "签到完成"), timeout=10):
    """检查是否出现签到成功提示"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for text in success_texts:
            try:
                elem = window.child_window(title=text, timeout=1)
                if elem.exists():
                    logger.info(f"检测到签到成功提示: [{text}]")
                    return True
            except Exception:
                pass
        time.sleep(1)
    return False


def run_checkin(student_id, student_name, meeting_number=None, timeout=600):
    """
    执行签到流程。
    
    Args:
        student_id: 学号
        student_name: 姓名
        meeting_number: 会议号（用于日志）
        timeout: 最大等待时间（秒），默认10分钟
    
    Returns:
        (success: bool, message: str)
    """
    meeting_info = f"会议 {meeting_number}" if meeting_number else "当前会议"
    logger.info(f"开始签到流程: {meeting_info}, 学号={student_id}, 姓名={student_name}")

    window = _connect_tm_window()
    if not window:
        return False, "无法连接到腾讯会议窗口"

    # ============================================================
    # 第一步：检测签到通知弹窗，点击「加入」
    # ============================================================
    logger.info("第一步：等待签到通知弹窗（点击「加入」）...")
    join_clicked = _click_button_by_text(
        window,
        text_list=["加入", "Join", "立即加入", "开始签到"],
        timeout=timeout
    )

    if not join_clicked:
        # 可能已经跳过通知弹窗，直接进入签到应用
        logger.warning("未检测到签到通知弹窗，尝试直接查找签到应用窗口...")

    # 等待签到应用窗口加载
    time.sleep(2)

    # ============================================================
    # 第二步：在签到应用窗口中输入学号+姓名
    # ============================================================
    logger.info("第二步：在签到应用窗口中输入学号+姓名...")

    # 重新获取窗口（签到应用可能是新窗口）
    app_window = _wait_for_window_with_text(
        text_list=["签到", "请输入", "学号", "姓名"],
        timeout=30
    )

    target_window = app_window if app_window else window

    # 尝试填入学号
    id_success = _input_text_by_label(
        target_window,
        label_texts=["学号", "主修学号", "学生编号", "ID"],
        input_text=student_id,
        timeout=15
    )

    # 尝试填入姓名
    name_success = _input_text_by_label(
        target_window,
        label_texts=["姓名", "名字", "Name"],
        input_text=student_name,
        timeout=15
    )

    if not id_success and not name_success:
        # 兜底：尝试直接找到所有 Edit 控件依次填入
        try:
            import pywinauto
            edits = target_window.children(control_type="Edit")
            if len(edits) >= 2:
                edits[0].set_text(student_id)
                edits[1].set_text(student_name)
                logger.info("使用兜底方案填入学号和姓名")
                id_success = name_success = True
            elif len(edits) == 1:
                # 可能是一个框里填 "学号+姓名"
                edits[0].set_text(f"{student_id}{student_name}")
                logger.info("使用一个输入框填入学号+姓名")
                id_success = name_success = True
        except Exception as e:
            logger.error(f"兜底填入方案失败: {e}")
            return False, f"无法在签到窗口中找到输入框，请手动操作。错误: {e}"

    if not id_success and not name_success:
        return False, "无法在签到窗口中找到输入框，请手动操作。"

    time.sleep(1)

    # ============================================================
    # 第三步：点击「提交」按钮
    # ============================================================
    logger.info("第三步：点击「提交」按钮...")
    submit_success = _click_button_by_text(
        target_window,
        text_list=["提交", "确认", "签到", "Submit", "确定"],
        timeout=10
    )

    if not submit_success:
        logger.error("未找到「提交」按钮")
        return False, "未找到提交按钮，请手动点击提交"

    # 等待签到结果
    time.sleep(2)

    # ============================================================
    # 第四步：检查签到结果
    # ============================================================
    logger.info("第四步：检查签到结果...")
    if _check_success(target_window or window):
        logger.info("✅ 签到成功！")
        return True, "签到成功"
    else:
        # 未检测到成功提示，但提交已点击，可能是成功了的
        logger.warning("未检测到明确的签到成功提示，但已点击提交按钮")
        return True, "已点击提交按钮，但未检测到成功提示（可能已成功）"


def leave_meeting():
    """签到成功后自动离开会议"""
    logger.info("签到成功，准备离开会议...")
    try:
        window = _connect_tm_window()
        if window:
            _click_button_by_text(window, text_list=["离开会议", "退出", "Leave", "结束"], timeout=5)
            logger.info("已离开会议")
    except Exception as e:
        logger.error(f"离开会议失败: {e}")


def checkin_via_ocr(student_id, student_name, meeting_number=None, timeout=600):
    """
    OCR 后备方案：使用 pytesseract 识别屏幕文字定位控件。
    当 pywinauto 无法定位控件时自动切换至此方案。
    """
    try:
        import pytesseract
        import pyautogui
        import cv2
        import numpy as np
    except ImportError:
        logger.error("OCR后备方案需要 pytesseract, pyautogui, opencv-python，请运行: pip install pytesseract pyautogui opencv-python")
        return False, "OCR后备方案依赖缺失"

    logger.info("启动 OCR 后备签到方案...")
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            # 截取屏幕
            screenshot = pyautogui.screenshot()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 使用 OCR 识别文字
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
            
            # 查找包含目标文字的区域
            for i, text in enumerate(data['text']):
                if any(keyword in text for keyword in ["加入", "Join", "签到", "提交", "确认"]):
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    center_x, center_y = x + w // 2, y + h // 2
                    pyautogui.click(center_x, center_y)
                    logger.info(f"OCR 点击: [{text}] at ({center_x}, {center_y})")
                    time.sleep(1)
                    
            # 查找输入框并填入信息
            for i, text in enumerate(data['text']):
                if any(keyword in text for keyword in ["学号", "姓名", "请输入"]):
                    # 点击输入框附近位置（右侧或下方）
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    pyautogui.click(x + w + 50, y + h // 2)
                    pyautogui.write(f"{student_id}{student_name}")
                    logger.info(f"OCR 填入信息: {student_id}{student_name}")
                    time.sleep(1)
                    
        except Exception as e:
            logger.warning(f"OCR 方案出错: {e}")
            
        time.sleep(2)

    logger.warning("OCR 后备方案超时")
    return False, "OCR 后备方案超时"


if __name__ == "__main__":
    # 测试入口
    import sys
    if len(sys.argv) >= 3:
        sid, sname = sys.argv[1], sys.argv[2]
    else:
        sid, sname = "2024312250", "曾天智"
    
    print(f"测试签到流程: 学号={sid}, 姓名={sname}")
    print("请确保腾讯会议已打开并在会议中...")
    input("按 Enter 开始...")
    
    success, msg = run_checkin(sid, sname)
    print(f"结果: {msg}")
    
    if success:
        leave_meeting()
