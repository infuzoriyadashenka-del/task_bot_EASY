import re
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database import (
add_task,
get_task,
get_active_tasks,
get_last_tasks,
update_task_status,
update_deadline,
add_participant,
get_stats,
get_rating,
get_streak
)

router = Router()

UTC_OFFSET = 3

# =========================

# TIME

# =========================

def now():
return datetime.utcnow() + timedelta(hours=UTC_OFFSET)

# =========================

# SAVE USER

# =========================

async def save_user(message: Message):
if message.from_user and message.from_user.username:
await add_participant(
message.chat.id,
f"@{message.from_user.username}"
)

# =========================

# DATE PARSER

# =========================

def parse_human_date(text: str):
base = now()
text = text.lower()

```
if "завтра" in text:
    return (base + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")

if "послезавтра" in text:
    return (base + timedelta(days=2)).strftime("%d.%m.%Y %H:%M")

match = re.search(r"через (\d+) (день|дня|дней)", text)
if match:
    return (base + timedelta(days=int(match.group(1)))).strftime("%d.%m.%Y %H:%M")

return None
```

# =========================

# PARSE TASK

# =========================

def parse_task(text: str):
executor = re.search(r"@\w+", text)
date = re.search(r"\d{2}.\d{2}.\d{4} \d{2}:\d{2}", text)

```
executor = executor.group() if executor else "@unknown"
deadline = date.group() if date else parse_human_date(text)

clean = re.sub(r"@\w+", "", text)
clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

return clean.strip(), executor, deadline
```

# =========================

# CREATE TASK

# =========================

@router.message(F.text.startswith("задача:"))
async def create_task(message: Message):

```
await save_user(message)

text = message.text.replace("задача:", "").strip()

task_text, executor, deadline = parse_task(text)

if not deadline:
    await message.answer("❌ Не понял дедлайн")
    return

await add_task(message.chat.id, task_text, executor, deadline)

last = await get_last_tasks(message.chat.id, 1)
task_id = last[0][0] if last else "?"

await message.answer(
    f"✅ Задача #{task_id}\n\n"
    f"👤 {executor}\n"
    f"📌 {task_text}\n"
    f"⏰ {deadline}"
)
```

# =========================

# TASK LIST

# =========================

@router.message(Command("tasks"))
async def list_tasks(message: Message):

```
tasks = await get_active_tasks(message.chat.id)

if not tasks:
    await message.answer("📭 Нет задач")
    return

msg = "📌 Задачи:\n\n"

for t in tasks:
    msg += f"#{t[0]} {t[2]} — {t[3]} — {t[4]}\n"

await message.answer(msg)
```

# =========================

# TASK INFO

# =========================

@router.message(F.text.regexp(r"задача\s+\d+"))
async def task_info(message: Message):

```
nums = re.findall(r"\d+", message.text)
if not nums:
    return

task_id = int(nums[0])

task = await get_task(task_id, message.chat.id)

if not task:
    await message.answer("❌ Не найдено")
    return

try:
    deadline = datetime.strptime(task[4], "%d.%m.%Y %H:%M")
    diff = deadline - now()
    hours = int(diff.total_seconds() // 3600)
except:
    hours = None

msg = (
    f"📌 Задача #{task[0]}\n\n"
    f"📄 {task[2]}\n"
    f"👤 {task[3]}\n"
    f"⏰ {task[4]}\n"
    f"📊 {task[5]}\n"
)

if hours is not None:
    msg += f"\n⏳ Осталось {hours} часов"

await message.answer(msg)
```

# =========================

# COMMANDS

# =========================

@router.message(Command("done"))
async def done_task(message: Message):

```
try:
    task_id = int(message.text.split()[1])
except:
    await message.answer("❌ Формат: /done 1")
    return

await update_task_status(task_id, "done")
await message.answer("✅ Выполнено")
```

@router.message(Command("cancel"))
async def cancel_task(message: Message):

```
try:
    task_id = int(message.text.split()[1])
except:
    await message.answer("❌ Формат: /cancel 1")
    return

await update_task_status(task_id, "cancelled")
await message.answer("❌ Отменено")
```

@router.message(Command("stats"))
async def stats(message: Message):

```
rows = await get_stats(message.chat.id)

msg = "📊 Статистика:\n\n"

for user, status, count in rows:
    msg += f"{user} — {status}: {count}\n"

await message.answer(msg)
```

@router.message(Command("rating"))
async def rating(message: Message):

```
rows = await get_rating(message.chat.id)

if not rows:
    await message.answer("📭 Нет данных")
    return

msg = "🏆 Рейтинг:\n\n"

for i, (user, score) in enumerate(rows, 1):
    msg += f"{i}. {user} — {score}\n"

await message.answer(msg)
```

@router.message(Command("analytics"))
async def analytics(message: Message):

```
stats = await get_stats(message.chat.id)

msg = "📊 Аналитика:\n\n"

for user, status, count in stats:
    streak = await get_streak(message.chat.id, user)
    s = streak[0] if streak else 0

    msg += (
        f"{user}\n"
        f"✔ {status}: {count}\n"
        f"🔥 streak: {s}\n\n"
    )

await message.answer(msg)
```
