"""
定时调度模块 - 管理会议入会定时任务

使用 APScheduler 管理定时入会任务。
同一会议码不重复创建任务。
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class MeetingScheduler:
    """会议定时调度器"""

    def __init__(self, join_advance_minutes: int = 8):
        self.join_advance_minutes = join_advance_minutes
        self._scheduled_meetings = {}  # meeting_code -> MeetingInfo
        self._scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": ThreadPoolExecutor(max_workers=5)},
            timezone="Asia/Shanghai",
        )
        self._scheduler.start()
        logger.info(f"调度器已启动，提前 {join_advance_minutes} 分钟入会")

    def add_meeting(self, meeting_info, join_callback):
        """
        添加会议到定时调度

        Args:
            meeting_info: parser.MeetingInfo 对象
            join_callback: 入会回调函数，接收 meeting_info 作为参数
        """
        code = meeting_info.meeting_code

        if code in self._scheduled_meetings:
            logger.info(f"会议 {code} 已在调度中，跳过（去重）")
            return False

        # 计算入会时间 = 会议开始时间 - 提前量
        join_time = meeting_info.datetime_obj - timedelta(minutes=self.join_advance_minutes)

        # 如果入会时间已过（比如老师发消息晚了），立即入会
        now = datetime.now()
        if join_time <= now:
            if meeting_info.datetime_obj > now + timedelta(minutes=5):
                # 会议还没结束，立即入会
                logger.warning(f"会议 {code} 入会时间已过，立即入会")
                self._scheduled_meetings[code] = meeting_info
                join_callback(meeting_info)
                return True
            else:
                logger.warning(f"会议 {code} 已结束，跳过")
                return False

        # 添加定时任务
        job_id = f"meeting_{code}"
        try:
            self._scheduler.add_job(
                join_callback,
                "date",
                run_date=join_time,
                args=[meeting_info],
                id=job_id,
                replace_existing=True,
            )
            self._scheduled_meetings[code] = meeting_info
            logger.info(
                f"已调度会议 [{meeting_info.course_name}] "
                f"会议号:{code} "
                f"将于 {join_time.strftime('%m-%d %H:%M')} 自动入会"
            )
            return True
        except Exception as e:
            logger.error(f"添加调度任务失败: {e}")
            return False

    def remove_meeting(self, meeting_code: str):
        """移除已完成的会议"""
        job_id = f"meeting_{meeting_code}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass
        self._scheduled_meetings.pop(meeting_code, None)
        logger.info(f"已移除会议 {meeting_code}")

    def get_scheduled_meetings(self) -> dict:
        """获取所有已调度的会议"""
        return dict(self._scheduled_meetings)

    def shutdown(self):
        """关闭调度器"""
        self._scheduler.shutdown(wait=False)
        logger.info("调度器已关闭")


# --- 测试 ---
if __name__ == "__main__":
    from parser import MeetingInfo

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    scheduler = MeetingScheduler(join_advance_minutes=8)

    # 模拟一个明天 14:00 的会议
    tomorrow = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)

    meeting = MeetingInfo(
        course_name="测试课程",
        meeting_code="123-456-789",
        date_str="明天",
        start_time="14:00",
        end_time="15:40",
        datetime_obj=tomorrow,
        raw_message="测试",
    )

    def on_join(info):
        print(f"触发入会: {info}")

    scheduler.add_meeting(meeting, on_join)

    print("已调度的会议:")
    for code, info in scheduler.get_scheduled_meetings().items():
        print(f"  {code}: {info.course_name} @ {info.datetime_obj}")

    scheduler.shutdown()
