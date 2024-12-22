from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import aiohttp
import asyncio
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')


WEATHER_SERVICE_URL = "http://localhost:5000"
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class WeatherStates(StatesGroup):
    waiting_for_start_city = State()
    waiting_for_days = State()
    waiting_for_details = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
👋 Добро пожаловать в Weather Route Bot!

Я помогу вам узнать прогноз погоды по маршруту вашего путешествия.

Что я умею:
• Показывать прогноз погоды для точек маршрута
• Предоставляь прогноз на несколько дней
• Отображать температуру, ветер и вероятность осадков

Используйте:...
/weather - Получить прогноз погоды
/help - Показать справку
"""
    await message.answer(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = """
📍 Доступные команды:

/start - Начать работу с ботом
/weather - Запросить прогноз погоды
/help - Показать это сообщение

🌤 Как получить прогноз погоды:
1. Введите команду /weather
2. Укажите начальный город
3. Укажите конечный город
4. Выберите количество дней для прогноза
"""
    await message.answer(help_text)

@dp.message(Command("weather"))
async def cmd_weather(message: types.Message, state: FSMContext):
    await message.answer("Введите города маршрута через запятую (например: Москва, Санкт-Петербург):")
    await state.set_state(WeatherStates.waiting_for_start_city)

@dp.message(WeatherStates.waiting_for_start_city)
async def process_start_city(message: types.Message, state: FSMContext):

    cities = [city.strip() for city in message.text.split(',')]
    
    if len(cities) < 2:
        await message.answer("Пожалуйста, введите как минимум 2 города через запятую:")
        return
    

    await state.update_data(cities=cities)
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="1 день", callback_data="days_1"),
                types.InlineKeyboardButton(text="2 дня", callback_data="days_2"),
            ],
            [
                types.InlineKeyboardButton(text="3 дня", callback_data="days_3"),
                types.InlineKeyboardButton(text="4 дня", callback_data="days_4"),
            ]
        ]
    )
    
    await message.answer("Выберите количество дней для прогноза:", reply_markup=keyboard)
    await state.set_state(WeatherStates.waiting_for_days)

@dp.callback_query(lambda c: c.data.startswith('days_'))
async def process_days_selection(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    processing_msg = await callback.message.answer("⏳ Получаю данные о погоде...")
    
    user_data = await state.get_data()
    if 'cities' not in user_data:
        await callback.message.answer(
            "Произошла ошибка: данные о городах не найдены.\n"
            "Пожалуйста, начните заново с команды /weather"
        )
        await processing_msg.delete()
        await state.clear()
        return

    days = int(callback.data.split('_')[1])
    cities = user_data['cities']

    try:
        weather_data = {}
        async with aiohttp.ClientSession() as session:
            for city in cities:  # Перебираем все города
                api_key = WEATHER_API_KEY
                params = {
                    "q": city,
                    "appid": api_key,
                    "units": "metric",
                    "cnt": days * 8
                }
                
                async with session.get("http://api.openweathermap.org/data/2.5/forecast", params=params) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise Exception(f"API Error for {city}: {error_data.get('message', 'Unknown error')}")
                    
                    data = await response.json()
                    weather_data[city] = {
                        'forecast': [
                            {
                                'date': item['dt_txt'],
                                'temp': item['main']['temp'],
                                'wind_speed': item['wind']['speed'],
                                'precipitation': item.get('pop', 0) * 100
                            }
                            for item in data['list']
                        ]
                    }

        plt.figure(figsize=(12, 6))
        for city, data in weather_data.items():
            dates = [datetime.strptime(d['date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m %H:%M') for d in data['forecast']]
            temps = [d['temp'] for d in data['forecast']]
            plt.plot(dates, temps, marker='o', label=city, markersize=4)

        plt.title('Прогноз температуры')
        plt.xlabel('Дата и время')
        plt.ylabel('Температура (°C)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()

        await callback.message.answer_photo(
            types.BufferedInputFile(buf.getvalue(), filename="forecast.png"),
            caption="График температур по маршруту"
        )

        for city, data in weather_data.items():
            daily_data = {}
            for item in data['forecast']:
                date = datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
                if date not in daily_data:
                    daily_data[date] = {
                        'temps': [],
                        'winds': [],
                        'precips': []
                    }
                daily_data[date]['temps'].append(item['temp'])
                daily_data[date]['winds'].append(item['wind_speed'])
                daily_data[date]['precips'].append(item['precipitation'])

            summary_text = f"🌤 Прогноз погоды для {city}:\n\n"
            for date, values in daily_data.items():
                display_date = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')
                avg_temp = sum(values['temps']) / len(values['temps'])
                avg_wind = sum(values['winds']) / len(values['winds'])
                max_precip = max(values['precips'])
                
                summary_text += (
                    f"📅 {display_date}\n"
                    f"🌡 Температура: {avg_temp:.1f}°C\n"
                    f"💨 Ветер: {avg_wind:.1f} м/с\n"
                    f"☔️ Осадки: {max_precip:.0f}%\n\n"
                )

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="Показать погоду с интервалами в три часа",
                        callback_data=f"detailed_{city}"
                    )
                ]]
            )
            
            await callback.message.answer(summary_text, reply_markup=keyboard)

        await state.update_data(weather_data=weather_data)
        await processing_msg.delete()
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        await processing_msg.delete()
        await callback.message.answer(
            f"😔 Произошла ошибка при получении прогноза: {str(e)}\n"
            "Пожалуйста, проверьте названия городов и попробуйте снова."
        )
    
    await state.set_state(WeatherStates.waiting_for_details)

@dp.callback_query(lambda c: c.data.startswith('detailed_'))
async def process_detailed_forecast(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    city = callback.data.split('_')[1]
    
    user_data = await state.get_data()
    weather_data = user_data.get('weather_data', {})
    
    if city not in weather_data:
        await callback.message.answer("Данные не найдены. Пожалуйста, запросите прогноз заново.")
        return
    
    daily_forecast = {}
    for item in weather_data[city]['forecast']:
        date = datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S')
        day = date.strftime('%d.%m')
        if day not in daily_forecast:
            daily_forecast[day] = []
        daily_forecast[day].append(item)

    detailed_text = f"🌤 Подробный прогноз для {city}:\n\n"
    for day, items in daily_forecast.items():
        detailed_text += f"📅 {day}:\n"
        for item in items:
            time = datetime.strptime(item['date'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            detailed_text += (
                f"⏰ {time}\n"
                f"🌡 Температура: {item['temp']:.1f}°C\n"
                f"💨 Ветер: {item['wind_speed']:.1f} м/с\n"
                f"☔️ Осадки: {item['precipitation']:.0f}%\n\n"
            )
    
    max_length = 4096
    for i in range(0, len(detailed_text), max_length):
        await callback.message.answer(detailed_text[i:i+max_length])

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())