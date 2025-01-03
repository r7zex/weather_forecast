import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import executor
from get_weather_forecast import get_weather
from get_time import get_time

# Токен вашего бота
Token = open('.gitignore').read()

TOKEN = Token
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


user_states = {}
start_messages = {}

POPULAR_CITIES = {
    "Москва": "moscow",
    "Санкт Петербург": "saint-petersburg",
    "Новосибирск": "novosibirsk",
    "Екатеринбург": "yekaterinburg",
    "Казань": "kazan"
}

global cur_time
global mes_id


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    start_messages[message.from_user.id] = message.message_id
    builder = InlineKeyboardMarkup()
    builder.add(*[InlineKeyboardButton(text=city, callback_data=city) for city in POPULAR_CITIES.keys()])

    await message.answer("Привет! Я помогу узнать погоду. Выберите город:", reply_markup=builder)


@dp.callback_query_handler(lambda c: c.data in POPULAR_CITIES.keys())
async def handle_popular_city(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = callback_query.data

    if user_states.get(user_id) == city:
        await bot.answer_callback_query(callback_query.id, text="Этот город уже выбран.")
        return

    user_states[user_id] = city
    global cur_time
    cur_time = await get_time(POPULAR_CITIES[city])

    if user_id in start_messages:
        await bot.delete_message(user_id, start_messages[user_id])
    await bot.delete_message(user_id, callback_query.message.message_id)
    start_messages.pop(user_id, None)

    await asyncio.sleep(1)

    markup = await get_keyboard_for_time()
    markup.add(InlineKeyboardButton("Вернуться к выбору города", callback_data="change_city"))

    await bot.send_message(user_id, f"Город выбран: {city}. Выберите временной промежуток.", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "change_city")
async def change_city(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_states.pop(user_id, None)

    builder = InlineKeyboardMarkup()
    builder.add(*[InlineKeyboardButton(text=city, callback_data=city) for city in POPULAR_CITIES.keys()])
    builder.add(InlineKeyboardButton(text="Ввести свой город", callback_data="custom_city"))

    await bot.delete_message(user_id, callback_query.message.message_id)
    await bot.send_message(user_id, "Выберите новый город:", reply_markup=builder)


@dp.callback_query_handler(lambda c: c.data.startswith("Погода на"))
async def handle_forecast(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    city = user_states.get(user_id)
    if not city:
        await bot.send_message(user_id, "Сначала выберите город!")

    time_type = callback_query.data[10:].lower()
    forecast_map = {"утро": "morning", "день": "day", "вечер": "evening", "ночь": "night"}

    if time_type in forecast_map:
        weather = await get_weather(POPULAR_CITIES[city], forecast_map[time_type], detailed=True)
    elif time_type == "весь день":
        weather = await get_weather(POPULAR_CITIES[city], "all_day", detailed=False)
    elif time_type == "сейчас":
        weather = await get_weather(POPULAR_CITIES[city], "current", detailed=False)
    else:
        weather = "Неверный выбор времени суток."

    await bot.send_message(user_id, weather)


@dp.message_handler()
async def handle_any_message(message: types.Message):
    user_id = message.from_user.id
    city = user_states.get(user_id)
    global mes_id
    mes_id = message.message_id
    if not city:
        await message.reply("Сначала выберите город с помощью команды /start.")
    else:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Узнать погоду", callback_data="select_time"))
        markup.add(InlineKeyboardButton("Изменить город", callback_data="change_city"))
        await message.reply(f"Вы выбрали город: {city}. Что хотите сделать?", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data == "select_time")
async def handle_select_time(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    await bot.delete_message(user_id, mes_id)
    await bot.delete_message(user_id, callback_query.message.message_id)

    markup = await get_keyboard_for_time()
    markup.add(InlineKeyboardButton("Вернуться к выбору города", callback_data="change_city"))
    await bot.send_message(user_id, f"Город выбран: {user_states[user_id]}. Выберите временной промежуток.",
                           reply_markup=markup)


async def get_keyboard_for_time():
    markup = InlineKeyboardMarkup()
    markup.add()
    local_time = cur_time
    buttons = [
        InlineKeyboardButton("На весь день", callback_data="Погода на весь день"),
        InlineKeyboardButton("На сейчас", callback_data="Погода на сейчас"),
        InlineKeyboardButton("На утро", callback_data="Погода на утро"),
        InlineKeyboardButton("На день", callback_data="Погода на день"),
        InlineKeyboardButton("На вечер", callback_data="Погода на вечер"),
        InlineKeyboardButton("На ночь", callback_data="Погода на ночь")
    ]
    if 4 <= local_time < 12:
        markup.add(*buttons[:2], *buttons[3:])
    elif 12 <= local_time < 16:
        markup.add(*buttons[:2], buttons[4], buttons[5])
    elif 16 <= local_time <= 23:
        markup.add(*buttons[:2], buttons[5])
    else:
        markup.add(*buttons[:])
    return markup


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
