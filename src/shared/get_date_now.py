from datetime import datetime

def get_date_now():
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    day_week = now.strftime("%A")
    return current_date, current_time, day_week
