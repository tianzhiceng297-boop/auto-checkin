"""
消息解析模块 - 从微信群消息中提取腾讯会议信息

老师消息格式示例：
    各位同学好!
    5月30日(星期六)
    公司金融(线上)
    时间:8:00-9:40
    腾讯会议号:415-968-791
    签到方式为腾讯会议签到...
"""

import re
from datetime import datetime
from dataclasses import dataclass


@dataclass
class MeetingInfo:
    """解析出的会议信息"""
    course_name: str      # 课程名称，如 "公司金融(线上)"
    meeting_code: str     # 会议码，如 "415-968-791"
    date_str: str         # 日期原文，如 "5月30日(星期六)"
    start_time: str       # 开始时间，如 "08:00"
    end_time: str         # 结束时间，如 "09:40"
    datetime_obj: datetime  # 解析后的会议开始时间
    raw_message: str       # 原始消息文本

    def __str__(self):
        return f"[{self.course_name}] {self.date_str} {self.start_time}-{self.end_time} 会议号:{self.meeting_code}"


# 正则表达式模式
PATTERNS = {
    "meeting_code": re.compile(r"腾讯会议号[:：]?\s*(\d{3}-\d{3}-\d{3})"),
    "meeting_code_alt": re.compile(r"会议号[:：]?\s*(\d{3}-\d{3}-\d{3})"),
    "date": re.compile(r"(\d{1,2})月(\d{1,2})日[（(](星期[一二三四五六日])[）)]"),
    "time": re.compile(r"时间[:：]\s*(\d{1,2}:\d{2})-(\d{1,2}:\d{2})"),
    "course": re.compile(r"^([^\n]+(?:线上|线下|线上\))?)(?:\n|$)", re.MULTILINE),
}


def parse_message(message: str) -> list[MeetingInfo]:
    """
    解析单条或合并的多条消息，提取会议信息。
    返回 MeetingInfo 列表（一条消息可能包含多个会议）。
    """
    results = []

    # 尝试提取会议码
    code_match = PATTERNS["meeting_code"].search(message) or PATTERNS["meeting_code_alt"].search(message)
    if not code_match:
        return results

    meeting_code = code_match.group(1)

    # 提取日期
    date_match = PATTERNS["date"].search(message)
    if not date_match:
        return results

    month = int(date_match.group(1))
    day = int(date_match.group(2))
    weekday_str = date_match.group(3)

    # 提取时间
    time_match = PATTERNS["time"].search(message)
    if not time_match:
        return results

    start_time = time_match.group(1)
    end_time = time_match.group(2)

    # 构建完整的 datetime
    now = datetime.now()
    year = now.year
    # 如果解析出的月份小于当前月份，说明是明年（跨年情况）
    if month < now.month and month < 6:
        year += 1

    start_hour, start_min = map(int, start_time.split(":"))
    try:
        dt = datetime(year, month, day, start_hour, start_min)
    except ValueError:
        return results

    # 提取课程名称（取消息开头到"各位同学好"或"腾讯会议号"之间的内容）
    course_name = _extract_course_name(message)

    info = MeetingInfo(
        course_name=course_name,
        meeting_code=meeting_code,
        date_str=f"{month}月{day}日({weekday_str})",
        start_time=start_time,
        end_time=end_time,
        datetime_obj=dt,
        raw_message=message,
    )
    results.append(info)

    return results


def _extract_course_name(message: str) -> str:
    """从消息中提取课程名称"""
    # 常见模式：紧跟在问候语后面的行
    lines = message.strip().split("\n")
    course = "未知课程"

    skip_phrases = {"各位同学好", "@All", "谢谢", "签到", "腾讯会议号"}

    for line in lines:
        line = line.strip()
        if not line or line.startswith("@") or line in skip_phrases:
            continue
        if "会议号" in line or "时间" in line or "签到" in line:
            continue
        # 如果这行包含课程关键词特征
        if "金融" in line or "管理" in line or "经济" in line or "会计" in line or \
           "线上" in line or "线下" in line:
            course = line
            break
        # 如果这行看起来像课程名（中文字符为主）
        if len(line) <= 20 and re.search(r"[\u4e00-\u9fff]", line):
            course = line
            break

    return course


def is_meeting_notification(message: str) -> bool:
    """快速判断消息是否可能包含腾讯会议信息"""
    keywords = ["腾讯会议", "会议号", "会议码", "meeting.tencent.com"]
    return any(kw in message for kw in keywords)


# --- 测试 ---
if __name__ == "__main__":
    test_messages = [
        """各位同学好!

5月30日(星期六)
公司金融(线上)
时间:8:00-9:40
腾讯会议号:415-968-791
签到方式为腾讯会议签到，请同学们一定提前进入会议，按时完成签到!@All""",

        """腾讯会议号:424-122-502

注:本学期课程签到方式改为腾讯会议签到,请同学们一定提前进入会议,按时完成签到!""",
    ]

    for msg in test_messages:
        print(f"{'='*50}")
        print(f"消息: {msg[:50]}...")
        print(f"是否会议通知: {is_meeting_notification(msg)}")
        results = parse_message(msg)
        for r in results:
            print(f"解析结果: {r}")
        if not results:
            print("未解析到会议信息")
