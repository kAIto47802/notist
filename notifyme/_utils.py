from datetime import timedelta


def format_timedelta(td: timedelta) -> str:
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = [
        days and f"{days}d",
        hours and f"{hours}h",
        minutes and f"{minutes}m",
        seconds and f"{seconds}s",
    ]
    return " ".join(filter(None, parts)) or "0s"
