from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.common.exceptions import WebDriverException

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

browser = webdriver.Chrome(options=chrome_options)


YANDEX_URL = "https://yandex.ru/pogoda/{}"


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


async def get_time(city):
    try:
        await open_new_tab(YANDEX_URL.format(city))

        WebDriverWait(browser, 20).until(
            ec.presence_of_element_located((By.CLASS_NAME, "fact__time"))
        )

        soup = BeautifulSoup(browser.page_source, 'html.parser')

        fact_time = soup.find('time', class_="fact__time")
        if fact_time is None:
            raise ValueError("Не удалось найти элемент <time> с классом 'fact__time'")

        time_text = fact_time.text.strip()
        time_only = time_text.split()[-1].strip('.')

        hour = int(time_only.split(':')[0])
        return hour

    except:
        print(f"Элемент с классом 'fact__time' не найден для города {city}")
        with open(f"{city}_error.html", "w", encoding="utf-8") as f:
            f.write(browser.page_source)
        return -1
    finally:
        await close_current_tab()
