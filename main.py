from telebot.async_telebot import AsyncTeleBot
from telebot import types
import asyncio, aiohttp, datetime, sqlite3
import numpy as np
from matplotlib import pyplot as plt
import time
import random
import requests
import base64

bot = AsyncTeleBot("6574774136:AAGRCli5ka_LDhrGI1wBOi-ave8ELaAKK2M")
connection = sqlite3.connect("Dap.service")
cursor = connection.cursor()
r = 0.00
sigma = 0.2
dt = 0.00001
np.random.seed(int(time.time() % 5344))


async def check_user(user_id):
    cursor.execute(f'SELECT dap FROM Users WHERE user_id="{user_id}"')
    user = cursor.fetchone()
    if user:
        return
    else:
        cursor.execute(f'INSERT INTO Users(user_id) VALUES ("{user_id}")')
        print(f"Added {user} to Database")
        connection.commit()


def continue_paths(r, sigma, M, dt, path):
    if M > 14400:
        M = 14400
    for t in range(len(path), len(path) + M):
        rand = np.random.standard_normal(1)
        num = np.round(path[t - 1] * np.exp((r - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * rand), 6)
        path = np.append(path, num)
    print(path, M)
    return path[M:]


@bot.message_handler(commands=['start'])
async def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton("Перевод")
    item2 = types.KeyboardButton("Бонус")
    markup.add(item1, item2)
    await bot.reply_to(message, f"Your ligma id: {message.from_user.username}", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Бонус")
async def bonus(message):
    user = message.from_user.username

    cursor.execute(f"SELECT dap FROM Users WHERE user_id='treasury'")
    treasury = cursor.fetchone()[0]
    if treasury < 100:
        await bot.send_message(message.chat.id, f"В казне нет денег! Обойдетесь...")
        return

    await check_user(user)
    cursor.execute(f"SELECT bonus FROM Users WHERE user_id='{user}'")
    bonus_day = cursor.fetchone()[0]

    if bonus_day != datetime.date.today().day:
        cursor.execute(f'SELECT dap FROM Users WHERE user_id="{user}"')
        user_dap = cursor.fetchone()[0]

        cursor.execute(f'UPDATE Users SET dap ={treasury - 100} WHERE user_id="treasury"')
        cursor.execute(f'UPDATE Users SET dap = {user_dap + 100} WHERE user_id="{user}"')
        cursor.execute(f'UPDATE Users SET bonus = {datetime.date.today().day} WHERE user_id="{user}"')
        connection.commit()
        await bot.send_message(message.chat.id, f"Вы получили ежедневный бонус: 100 DP!")
    else:
        await bot.send_message(message.chat.id, f"Вы уже получали ежедневный бонус :|")


@bot.message_handler(func=lambda message: message.text == "Перевод")
async def transfer(message):
    dap = 300
    markup = types.ForceReply(selective=False)
    await bot.send_message(message.chat.id, f"Ваш текущий баланс: {dap} DP!\nКому перевести DP?")


@bot.inline_handler(lambda query: len(query.query) >= 0)
async def query_text(inline_query):
    user = inline_query.from_user.username
    await check_user(user)
    cursor.execute(f'SELECT dap FROM Users WHERE user_id="{user}"')
    user = cursor.fetchone()[0]
    cursor.execute(f'SELECT dap FROM Users WHERE user_id="treasury"')
    treasure = cursor.fetchone()[0]
    cursor.execute(f"SELECT time FROM Time")
    tt = int(cursor.fetchone()[0])
    vt = int(time.time()) - tt
    np.random.seed(int(time.time() % 5344) * random.randint(1, 100))
    cursor.execute(f"UPDATE Time SET time = {int(time.time())}")
    cursor.execute("SELECT num FROM Data")
    results = cursor.fetchall()
    path = [row[0] for row in results]
    path = continue_paths(r, sigma, vt, dt, path)
    for i in range(len(path)):
        cursor.execute(f'UPDATE Data SET num = {path[i]} WHERE id="{i + 1}"')
    connection.commit()
    plt.ylim(min(path) - 0.1, max(path) + 0.1)
    plt.ylabel('Цена акции (BP)')
    plt.xlabel('Время (сек)')
    plt.title(f'Текущая цена акции: {round(path[-1], 2)} DP')
    plt.plot(path)
    plt.savefig("image.png")
    plt.close()

    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": "Client-ID dff0bd4292298b0"}
    with open("image.png", "rb") as file:
        data = file.read()
        base64_data = base64.b64encode(data)
    response = requests.post(url, headers=headers, data={"image": base64_data})
    url = response.json()["data"]["link"]
    print(url)
    balance = types.InlineQueryResultArticle("1", 'Баланс',
                                             types.InputTextMessageContent(f"Ваш баланс: {user} DP"),
                                             thumbnail_url="https://cdn.icon-icons.com/icons2/516/PNG/512/cash_icon"
                                                           "-icons.com_51090.png")
    treasury = types.InlineQueryResultArticle("2", 'Казна',
                                              types.InputTextMessageContent(f"Текущая казна: {treasure} DP"),
                                              thumbnail_url="https://pngfre.com/wp-content/uploads/Piggy-Bank-4.png")
    stock_market = types.InlineQueryResultPhoto('3',
                                                photo_url=url,
                                                title='Фондовая биржа',
                                                thumbnail_url='https://static.vecteezy.com/system/resources/previews/031/014/787/non_2x/stock-market-icon-vector.jpg')

    await bot.answer_inline_query(inline_query.id, [balance, treasury, stock_market], cache_time=1, next_offset="")


if __name__ == '__main__':
    try:
        asyncio.run(bot.infinity_polling())
    except KeyboardInterrupt:
        connection.close()
        print('\nExiting by user request.\n')
