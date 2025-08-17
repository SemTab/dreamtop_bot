import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from db import (
    init_db, add_user, get_user, get_user_by_id, get_user_by_username,
    update_coins, update_last_reward, get_all_users,
    transfer_coins, update_ban, check_ban, unban_user
)

TOKEN = "СЮДА ВАШ ТОКЕН"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----------------- ADMIN -----------------
def load_admins():
    with open("admins.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def is_admin(username: str):
    admins = load_admins()
    return username in admins

# ----------------- /start -----------------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без ника"

    if add_user(user_id, username):
        await message.answer(f"✅ Привет, {username}! Ты добавлен в базу данных.")
    else:
        await message.answer(f"👋 Привет снова, {username}! Ты уже зарегестрирован в базе данных✅")

# ----------------- /reward -----------------
@dp.message(Command("reward"))
async def cmd_reward(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return
    banned, until, reason = check_ban(user[0])
    if banned:
        await message.answer(f"❌ Вы в бане до {until}\nПричина: {reason}")
        return
    last_reward = datetime.strptime(user[3], "%Y-%m-%d %H:%M:%S")
    if datetime.now() - last_reward < timedelta(hours=1):
        remaining = timedelta(hours=1) - (datetime.now() - last_reward)
        await message.answer(f"⏳ Подожди {remaining.seconds // 60} минут перед следующим /reward.")
        return
    balance = user[2]
    reward = max(700, balance // 10)
    update_coins(user[0], balance + reward)
    update_last_reward(user[0])
    await message.answer(f"💰 Ты получил {reward} монет! Новый баланс: {balance + reward}")
# ----------------- /casino -----------------
@dp.message(Command("casino"))
async def cmd_casino(message: Message):
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Используй: /casino <ставка>")
        return

    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return

    banned, until, reason = check_ban(user[0])
    if banned:
        await message.answer(f"❌ Вы в бане до {until}\nПричина: {reason}")
        return

    bet = int(parts[1])
    balance = user[2]
    if bet <= 0 or bet > balance:
        await message.answer("❌ Неверная ставка.")
        return

    if random.random() < 0.5:
        balance -= bet
        await message.answer(f"💀 Ты проиграл {bet} монет. Баланс: {balance}")
    else:
        win = bet * 2
        balance += bet
        await message.answer(f"🎉 Ты выиграл {win} монет! Баланс: {balance}")

    update_coins(user[0], balance)

# ----------------- /pay -----------------
@dp.message(Command("pay"))
async def cmd_pay(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /pay <user_id или username> <кол-во монет>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Количество монет должно быть числом.")
        return

    if amount <= 0:
        await message.answer("Сумма должна быть больше 0.")
        return

    sender_id = message.from_user.id
    sender = get_user(sender_id)
    banned, until, reason = check_ban(sender_id)
    if banned:
        await message.answer(f"❌ Вы в бане до {until}\nПричина: {reason}")
        return

    
    if target.isdigit():
        recipient = get_user_by_id(int(target))
    else:
        if target.startswith("@"):
            target = target[1:]
        recipient = get_user_by_username(target)

    if recipient is None:
        await message.answer("Пользователь не найден.")
        return

    recipient_id = recipient[0]
    if sender_id == recipient_id:
        await message.answer("Нельзя отправлять монеты самому себе.")
        return

    if transfer_coins(sender_id, recipient_id, amount):
        await message.answer(f"✅ Вы успешно отправили {amount} монет пользователю {recipient[1]}")
    else:
        await message.answer("❌ Недостаточно монет для перевода.")

# ----------------- Топ 10 -----------------
@dp.message(Command("top"))
async def cmd_top(message: Message):
    users = get_all_users()
    text = "🏆 Топ 10 игроков по балансу:\n"
    for uid, uname, coins in users:
        text += f"• <a href='tg://user?id={uid}'>{uname}</a> — {coins} монет\n"
    await message.answer(text, parse_mode="HTML")

# ----------------- /balance -----------------
@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала используй /start")
        return

    banned, until, reason = check_ban(user[0])
    if banned:
        await message.answer(f"❌ Вы в бане до {until}\nПричина: {reason}")
        return

    await message.answer(f"💰 Твой текущий баланс: {user[2]} монет")

# ----------------- /addcoins (админ) -----------------
@dp.message(Command("addcoins"))
async def cmd_addcoins(message: Message):
    if not is_admin(message.from_user.username):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /addcoins <user_id или @username> <кол-во>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Количество должно быть числом.")
        return

    if target.isdigit():
        user = get_user_by_id(int(target))
    else:
        if target.startswith("@"):
            target = target[1:]
        user = get_user_by_username(target)

    if not user:
        await message.answer("Пользователь не найден.")
        return

    update_coins(user[0], user[2] + amount)
    await message.answer(f"✅ Добавлено {amount} монет пользователю {user[1]}")

# ----------------- /removecoins (админ) -----------------
@dp.message(Command("removecoins"))
async def cmd_removecoins(message: Message):
    if not is_admin(message.from_user.username):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /removecoins <user_id или @username> <кол-во>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Количество должно быть числом.")
        return

    if target.isdigit():
        user = get_user_by_id(int(target))
    else:
        if target.startswith("@"):
            target = target[1:]
        user = get_user_by_username(target)

    if not user:
        await message.answer("Пользователь не найден.")
        return

    new_balance = max(0, user[2] - amount)
    update_coins(user[0], new_balance)
    await message.answer(f"✅ Снято {amount} монет у пользователя {user[1]}. Новый баланс: {new_balance}")

# ----------------- /ban (админ) -----------------
@dp.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.username):
        await message.answer("❌ Только администраторы могут использовать эту команду.")
        return

    parts = message.text.split(maxsplit=3)
    if len(parts) < 3:
        await message.answer("Использование: /ban <user_id или username> <время в минутах или forever> [причина]")
        return

    target = parts[1]
    duration = parts[2]
    reason = parts[3] if len(parts) > 3 else "Без причины"

    if target.isdigit():
        user = get_user_by_id(int(target))
    else:
        if target.startswith("@"):
            target = target[1:]
        user = get_user_by_username(target)

    if not user:
        await message.answer("Пользователь не найден.")
        return

    if duration == "forever":
        until = "forever"
    else:
        try:
            minutes = int(duration)
            until = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            await message.answer("Неверное время бана.")
            return

    update_ban(user[0], until, reason)
    await message.answer(f"✅ Пользователь {user[1]} забанен до {duration}. Причина: {reason}")

# ----------------- /unban (админ) -----------------
@dp.message(Command("unban"))
async def cmd_unban(message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /unban <user_id или @username> <причина>")
        return

    target = parts[1]
    reason = " ".join(parts[2:])

    if target.isdigit():
        user = get_user_by_id(int(target))
    else:
        if target.startswith("@"):
            target = target[1:]
        user = get_user_by_username(target)

    if not user:
        await message.answer("Пользователь не найден.")
        return

    unban_user(user[0])
    await message.answer(f"✅ Пользователь {user[1]} разбанен. Причина: {reason}")

#---------------------HELP----------------------------
@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📜 <b>Список команд</b>\n\n"
        "👤 <b>Пользовательские:</b>\n"
        "/start — Регистрация в боте\n"
        "/reward — Получить награду (раз в час)\n"
        "/balance — Проверить баланс\n"
        "/casino — Сыграть в казино\n"
        "/top — Топ игроков по балансу\n"
        "/help — Список команд\n\n"
        
    )
    if is_admin(message.from_user.username):
            text += (
            "🛠 <b>Админские:</b>\n"
            "/addcoins [id/username] (сумма) — Добавить монеты\n"
            "/removecoins [id/username] (сумма) — Снять монеты\n"

            "🛠Это весь список команд, желаю хорошего общения😎"
              )
    await message.answer(text, parse_mode="HTML")
    
# ----------------- Установка команд -----------------
async def set_commands(bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь по командам"),
        BotCommand(command="reward", description="Получить подарок"),
        BotCommand(command="casino", description="Сыграть в казино"),
        BotCommand(command="pay", description="Перевести монеты другому пользователю"),
        BotCommand(command="top", description="Топ игроков"),
        BotCommand(command="ban", description="Забанить пользователя (админ)"),
        BotCommand(command="unban", description="Разбанить пользователя (админ)"),
        BotCommand(command="addcoins", description="Выдать монеты пользователю (админ)"),
        BotCommand(command="removecoins", description="Снять монеты с пользователя (админ)")
     ]
    await bot.set_my_commands(commands)

# ----------------- Запуск  -----------------
async def main():
    init_db()
    await set_commands(bot)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
