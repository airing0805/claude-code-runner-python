"""计算下次执行时间并更新 scheduled.json"""
import json
from datetime import datetime, timedelta
from pathlib import Path

# 读取 scheduled.json
scheduled_file = Path("data/scheduled.json")
data = json.loads(scheduled_file.read_text(encoding="utf-8"))

# Cron 表达式 "1 * * * *" - 每小时第 1 分钟执行
now = datetime.now()

# 计算下次执行时间
if now.minute < 1:
    # 当前分钟小于 1，下次就是当前小时的第 1 分钟
    next_run = now.replace(minute=1, second=0, microsecond=0)
elif now.minute == 1 and now.second == 0:
    # 正好是 1 分 0 秒，下次就是下一小时的第 1 分钟
    next_run = now + timedelta(hours=1)
    next_run = next_run.replace(minute=1, second=0, microsecond=0)
else:
    # 当前分钟已过，下次就是下一小时的第 1 分钟
    next_run = now + timedelta(hours=1)
    next_run = next_run.replace(minute=1, second=0, microsecond=0)

# 更新任务的 next_run
for task in data.get("tasks", []):
    if task.get("id") == "a050556f-241c-4a72-9eac-8233793903fa":
        task["next_run"] = next_run.isoformat()
        print(f"Updated next_run for task 'qqqq': {next_run.isoformat()}")
        break

# 写回文件
scheduled_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Done!")
