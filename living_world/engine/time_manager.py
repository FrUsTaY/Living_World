class TimeManager:
    def __init__(self):
        self.day = 1
        self.hour = 8
        self.minute = 0
        self.speed = 1  # 1x, 10x, 100x, 1000x
        self.paused = True

    def set_time(self, day, hour, minute):
        self.day = day
        self.hour = hour
        self.minute = minute

    def get_time_dict(self):
        return {"day": self.day, "hour": self.hour, "minute": self.minute}

    def format_time(self):
        return f"День {self.day} · {self.hour:02d}:{self.minute:02d}"

    def tick(self, minutes=1):
        if self.paused:
            return False

        self.minute += minutes
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1

        while self.hour >= 24:
            self.hour -= 24
            self.day += 1

        return True

    def get_total_minutes(self):
        return (self.day - 1) * 24 * 60 + self.hour * 60 + self.minute
