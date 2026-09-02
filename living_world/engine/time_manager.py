from datetime import datetime, timedelta

class TimeManager:
    # Base starting date for the world
    START_DATE = datetime(2000, 1, 1, 8, 0, 0)

    def __init__(self):
        self.current_datetime = self.START_DATE
        self.speed = 1  # 1x, 10x, 100x, 1000x
        self.paused = True

    def set_time(self, current_datetime: datetime):
        self.current_datetime = current_datetime

    def set_time_from_dict(self, time_dict: dict):
        if 'year' in time_dict and 'month' in time_dict:
            # New format
            self.current_datetime = datetime(
                time_dict.get('year', 2000),
                time_dict.get('month', 1),
                time_dict.get('day', 1),
                time_dict.get('hour', 8),
                time_dict.get('minute', 0)
            )
        else:
            # Old format (relative day, hour, minute)
            day = time_dict.get('day', 1)
            hour = time_dict.get('hour', 8)
            minute = time_dict.get('minute', 0)

            # Convert day offset back to a datetime relative to START_DATE
            delta = timedelta(days=day - 1, hours=hour - 8, minutes=minute)
            self.current_datetime = self.START_DATE + delta

    def get_time_dict(self):
        return {
            "year": self.current_datetime.year,
            "month": self.current_datetime.month,
            "day": self.current_datetime.day,
            "hour": self.current_datetime.hour,
            "minute": self.current_datetime.minute
        }

    def format_time(self):
        return self.current_datetime.strftime("%d.%m.%Y · %H:%M")

    def format_date(self):
        return self.current_datetime.strftime("%d.%m.%Y")

    def tick(self, minutes=1):
        if self.paused:
            return False

        self.current_datetime += timedelta(minutes=minutes)
        return True

    def get_total_minutes(self):
        # Time elapsed since START_DATE in minutes
        delta = self.current_datetime - self.START_DATE
        return int(delta.total_seconds() // 60)

    @property
    def day(self):
        """Property for backwards compatibility and ease of access. Represents absolute days since start."""
        return (self.current_datetime - self.START_DATE).days + 1

    @property
    def hour(self):
        """Property for backwards compatibility and ease of access"""
        return self.current_datetime.hour

    @property
    def minute(self):
        """Property for backwards compatibility and ease of access"""
        return self.current_datetime.minute
