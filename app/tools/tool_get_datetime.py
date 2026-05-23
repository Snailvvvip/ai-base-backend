import datetime

from langchain_core.tools import tool


@tool(name_or_callable="tool_get_datetime", description="一个获取当前时间信息的一个工具")
def tool_get_datetime():
  now = datetime.datetime.now()
  current_time = now.strftime("%Y-%m-%d %H:%M:%S")

  yesterday = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
  tomorrow = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
  day_after_tomorrow = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
  two_days_after_tomorrow = (now + datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

  weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
  current_weekday = weekdays[now.weekday()]
  yesterday_weekday = weekdays[(now.weekday() - 1) % 7]
  tomorrow_weekday = weekdays[(now.weekday() + 1) % 7]
  day_after_tomorrow_weekday = weekdays[(now.weekday() + 2) % 7]
  two_days_after_tomorrow_weekday = weekdays[(now.weekday() + 3) % 7]

  result = {
    "当前时间": f"{current_time} {current_weekday}",
    "昨天": f"{yesterday} {yesterday_weekday}",
    "明天": f"{tomorrow} {tomorrow_weekday}",
    "后天": f"{day_after_tomorrow} {day_after_tomorrow_weekday}",
    "大后天": f"{two_days_after_tomorrow} {two_days_after_tomorrow_weekday}"
  }

  return result
