from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import WebDriverException


user_drivers = {}

# Настройки Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

browser = webdriver.Chrome(options=chrome_options)
browser.get('about:blank')  # Загружаем пустую страницу, чтобы браузер был готов

# Популярные города и соответствующие им коды
POPULAR_CITIES = {
    "Москва": "moscow",
    "Санкт-Петербург": "saint-petersburg",
    "Новосибирск": "novosibirsk",
    "Екатеринбург": "yekaterinburg",
    "Казань": "kazan"
}

YANDEX_URL = "https://yandex.ru/pogoda/ru-RU/{}/details"
YANDEX_URL_DAY = "https://yandex.ru/pogoda/{}"

# Временные зоны городов
CITY_TIMEZONES = {
    "Москва": "Europe/Moscow",
    "Санкт-Петербург": "Europe/Moscow",
    "Новосибирск": "Asia/Novosibirsk",
    "Екатеринбург": "Asia/Yekaterinburg",
    "Казань": "Europe/Moscow"
}


def get_temperature_emoji(temperature):
    match = re.search(r'([+-]?\d+\.?\d*)', temperature.replace('−', '-'.strip()))
    temperature = int(match.group(1))
    if temperature < 0:
        return "🥶"
    elif 0 <= temperature <= 15:
        return "😎"
    else:
        return "🥵"


def get_wind_direction(full_direction):
    full_direction = full_direction.split()[-1]
    directions = {
        'С': 'Северный',
        'Ю': 'Южный',
        'З': 'Западный',
        'В': 'Восточный',
        'СЗ': 'Северо-Западный',
        'СВ': 'Северо-Восточный',
        'ЮЗ': 'Юго-Западный',
        'ЮВ': 'Юго-Восточный',
    }
    return directions.get(full_direction, "Неизвестно")


def get_weather_condition(condition):
    condition = condition.lower()
    weather_emojis = {
        'ясно': "☀️",
        'туман': "🌫️",
        'смог': "🌫️",
        'облачно с прояснениями': "🌥️",
        'пасмурно': "☁️☁️☁️",
        'малооблачно': "☁️",
        'небольшой дождь': "💧",
        'дождь': "🌧️",
        'гроза': "⛈️",
        'дождь с грозой': "⛈️🌧️",
        'ливень': "🌧️🌧️🌧️",
        'град': "🌧️🧊️",
        'дождь со снегом': "🌧️❄️",
        'небольшой снег': "❄️",
        'снег': "🌨️",
    }
    return weather_emojis.get(condition, "")


async def open_new_tab(url):
    """Открывает новую вкладку с указанным URL."""
    try:
        browser.execute_script("window.open('');")
        browser.switch_to.window(browser.window_handles[-1])
        browser.get(url)
    except WebDriverException as e:
        print(f"Ошибка при работе с браузером: {e}")


async def close_current_tab():
    """Закрывает текущую вкладку."""
    browser.close()
    browser.switch_to.window(browser.window_handles[-1])


async def get_weather(city_code, forecast_type, detailed):
    """Получает прогноз погоды через Selenium и BeautifulSoup."""
    url = YANDEX_URL.format(city_code) if detailed else YANDEX_URL_DAY.format(city_code)
    await open_new_tab(url)
    if detailed:
        WebDriverWait(browser, 10).until(
            ec.presence_of_element_located(
                (By.XPATH, "//div[contains(@style, 'grid-area: temperature-morning; padding: 10px 0px;')]"))
        )
    soup = BeautifulSoup(browser.page_source, 'html.parser')

    if forecast_type == "current":
        try:
            fact_time = soup.find('time', class_="fact__time").text.strip().split()[-1].strip('.')

            temp_element = soup.find('div', class_='fact__temp').find('span', class_='temp__value')
            condition_element = soup.find('div', class_='link__condition')
            feels_element = soup.find('div', class_='link__feelings').find('span', class_='temp__value')
            props = soup.find('div', class_="fact__props")
            wind_element = props.find_next('div', class_="fact__wind-speed").find_next('span',
                                                                                       class_="a11y-hidden").text.split()
            humidity_element = props.find_next('div', class_="fact__humidity").find_next('span',
                                                                                         class_="a11y-hidden").text
            pressure_element = props.find_next('div', class_="fact__pressure").find_next('span',
                                                                                         class_="a11y-hidden").text.split()

            temperature = temp_element.text.strip() if temp_element else "Неизвестно"
            condition = condition_element.text.strip() if condition_element else "Неизвестно"
            feels_like = feels_element.text.strip() if feels_element else "Неизвестно"
            wind_speed = wind_element[1]
            wind_direction = wind_element[-1]
            humidity = humidity_element
            pressure = pressure_element[1]

            condition_emoji = get_weather_condition(condition)
            temperature_emoji = get_temperature_emoji(temperature)
            feels_like_emoji = get_temperature_emoji(feels_like)
            await close_current_tab()

            return (
                f"Погода на {fact_time}🕛:\n"
                f"Температура: {temperature}C {temperature_emoji}\n"
                f"Состояние:  {condition} {condition_emoji}\n"
                f"Давление: {pressure} мм. рт. ст. ⏲️\n"
                f"Влажность: {humidity} 💧\n"
                f"Ветер: {wind_speed} м/с  {wind_direction.capitalize()} 🌪️\n"
                f"Ощущается как: {feels_like}C {feels_like_emoji}"

            )
        except Exception as e:
            await close_current_tab()
            return f"Не удалось получить данные о текущей погоде: {e}"

    if forecast_type == "all_day":
        try:
            forecast_days = soup.find_all('li', class_='forecast-briefly__day')
            aria_labels = [day.find('a').get('aria-label') for day in forecast_days if day.find('a')]
            aria_labels = [x.split(', ') for x in aria_labels]
            aria_label = aria_labels[1]
            condition_emoji = get_weather_condition(aria_label[-3])
            await close_current_tab()
            return (
                f"Погода на весь день:\n"
                f"Температура днем:  {aria_label[-2].capitalize()}C ☀️\n"
                f"Температура ночью:  {aria_label[-1].capitalize()}C 🌙\n"
                f"Состояние: {aria_label[-3]} {condition_emoji}"
            )
        except Exception as e:
            await close_current_tab()
            return f"Не удалось получить данные о погоде на весь день: {e}"
    period_map = {
        "morning": "утро",
        "day": "день",
        "evening": "вечер",
        "night": "ночь"
    }
    forecast_period = period_map.get(forecast_type)

    if not forecast_period:
        await close_current_tab()
        return "Некорректный выбор времени суток."

    try:
        all_periods = soup.find_all('article')
        cur_day = all_periods[1]
        if cur_day:
            def get_forecast_info(cur_day_func, forecast_type_func):
                style_suffix = f"{forecast_type_func}"
                temperature_cur = cur_day_func.find_next('div',
                                                         style=f"grid-area: temperature-{style_suffix}; padding: 10px 0px;")
                condition_cur = cur_day_func.find_next('div', style=f"grid-area: condition-{style_suffix};").find_next(
                    'div').find_next('div')
                pressure = cur_day_func.find_next('div', style=f"grid-area: pressure-{style_suffix};")
                humidity = cur_day_func.find_next('div', style=f"grid-area: humidity-{style_suffix};")
                wind = cur_day_func.find_next('div', style=f"grid-area: wind-{style_suffix};")
                feels_like_cur = cur_day_func.find_next('div', style=f"grid-area: feelsLike-{style_suffix};")
                return {
                    "temperature_cur": str(temperature_cur).split('</div>')[-2],
                    "condition_cur": condition_cur.get_text(),
                    "pressure": pressure.get_text(),
                    "humidity": humidity.get_text(),
                    "wind": ' '.join(wind.stripped_strings),
                    "feels_like_cur": feels_like_cur.get_text(),
                }

            forecast_info = get_forecast_info(cur_day, forecast_type)
            temperature_emoji = get_temperature_emoji(forecast_info['temperature_cur'])
            wind_direction_emoji = get_wind_direction(forecast_info['wind'])
            condition_emoji = get_weather_condition(forecast_info['condition_cur'])
            feels_like_emoji = get_temperature_emoji(forecast_info['feels_like_cur'])
            await close_current_tab()
            return (
                f"Прогноз погоды на {forecast_period}:\n"
                f"Температура: {forecast_info['temperature_cur']}C {temperature_emoji}\n"
                f"Состояние:  {forecast_info['condition_cur'].capitalize()} {condition_emoji}\n"
                f"Давление: {forecast_info['pressure']} мм. рт. ст. ⏲️\n"
                f"Влажность: {forecast_info['humidity']} 💧\n"
                f"Ветер: {forecast_info['wind'].split()[0]} м/с {wind_direction_emoji} 🌪️\n"
                f"Ощущается как: {forecast_info['feels_like_cur']}C {feels_like_emoji}"
            )
        else:
            await close_current_tab()
            return f"Не удалось найти прогноз для {forecast_period}."
    except Exception as e:
        await close_current_tab()
        return f"Не удалось получить данные о погоде на {forecast_period}: {e}"