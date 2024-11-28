import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import telebot
import requests
import re
import psycopg2
from io import BytesIO
import api_requests as api
from db_config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from auth import TELEBOT_TOKEN

matplotlib.use('Agg')
regex_pattern = re.compile(
    r"^(?:http|ftp)s?://"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?$)"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$", re.IGNORECASE)

bot = telebot.TeleBot(TELEBOT_TOKEN)
api_url = 'https://api.websitecarbon.com/site?url='
about_text = '''Привет! Вы используете бота для оценки экологичности сайта. Он основан на исследованиях компании Wholegrain Digital. Мы не будем углубляться в подробности, подробнее вы можете узнать на сайте: https://api.websitecarbon.com/. 

Как пользоваться калькулятором? Не переживайте, всё просто!
/start - команда, которая поможет вернуться в самое начало. Вы можете ввести её в любой момент и начать заново.

Дальше есть всего три кнопки:
📌 Проверить - позволяет получить данные о сайте, от вас требуется только ввести ссылку.
📌 Рейтинг - выводит 10 самых грязных сайтов из тех, которые вы проверяли. По желанию, вы можете удалить все данные о запросах - здесь будет соответствующая кнопка.
📌 Как работает бот? - выведет это сообщение

Ну что, узнаем, как сильно мы загрязняем окружающую среду?'''

users_url = {}

try:
    connection = psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    cursor = connection.cursor()
    if connection.closed == 0:
        print("Соединение c базой данных установлено!")
        print(connection.dsn)
    else:
        print("Соединение с базой данных закрыто.")
except Exception as db_connection_error:
    print(db_connection_error)


@bot.message_handler(commands=['start'])
def start(message):
    try:
        chat_id = message.chat.id
        username = message.from_user.username
        if not api.is_user_exists(cursor, chat_id):
            api.insert_user(cursor, connection, chat_id, username)

        keyboard = telebot.types.InlineKeyboardMarkup()
        button_check = telebot.types.InlineKeyboardButton(text="Проверить",
                                                          callback_data='check')
        button_rating = telebot.types.InlineKeyboardButton(text="Рейтинг",
                                                           callback_data='rating')
        button_about = telebot.types.InlineKeyboardButton(text="Как работает бот?",
                                                          callback_data='about')
        keyboard.add(button_check)
        keyboard.add(button_rating)
        keyboard.add(button_about)

        bot.send_message(message.chat.id,
                         'Я бот для оценки экологичности сайта. Что будем делать?',
                         reply_markup=keyboard)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id,
                         'Произошла неизвестная ошибка. Пожалуйста, попробуйте еще раз')


@bot.callback_query_handler(func=lambda call: call.data == 'check')
def save_btn(call):
    message = call.message
    chat_id = message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=message.id,
                          text='Введите URL сайта, который вы хотите проверить')
    users_url[chat_id] = {}

    bot.register_next_step_handler(message, save_url)


def is_valid_url(url, pattern=regex_pattern):
    return re.match(pattern, url) is not None


def incorrect_url(message):
    chat_id = message.chat.id
    bot.send_message(chat_id,
                     text='Ой, а что это у нас? Не похоже на сайт🤔 Попробуйте ввести адрес сайта в формате: https://example.com')
    users_url[chat_id] = {}

    bot.register_next_step_handler(message, save_url)


def try_again(message):
    chat_id = message.chat.id
    bot.send_message(chat_id,
                     text='Хмм, для этого сайта ничего не найдено. Разумеется, во всём виноваты глобальные изменения климата. Попробуйте ещё раз')
    users_url[chat_id] = {}

    bot.register_next_step_handler(message, save_url)


def save_url(message):
    chat_id = message.chat.id
    input_text = message.text
    if input_text == '/start':
        start(message)
    else:
        url = input_text
        users_url[chat_id]['url'] = url
        bot.send_message(chat_id, f'Вы хотите проверить этот сайт: {url}')
        bot.send_message(chat_id,
                         f'Встать на путь экологии непросто - любые изменения требуют времени. Подождите несколько минут, ваш запрос уже передан на обработку')

        if not is_valid_url(url):
            incorrect_url(message)

        else:
            input_url = url
            url = url.replace('/', '%2F')
            url = url.replace(':', '%3A')

            url_for_check = api_url + url
            response = requests.get(url_for_check)

            if response.status_code != 200:
                try_again(message)

            else:
                info = response.json()
                cleaner_than = info["cleanerThan"] * 100
                cleaner_than = round(cleaner_than)
                rating = info["rating"]
                co2 = info["statistics"]["co2"]["grid"]["grams"]
                co2 = round(co2, 2)

                try:
                    api.insert_carbon_emission(cursor, connection, chat_id, input_url, rating, co2)
                    bot.send_message(chat_id,
                                     f'О ужас! При каждом посещении этот сайт вырабатывает {co2} грамм углекислого газа!')
                    bot.send_message(chat_id,
                                     f'Углеродный рейтинг этого сайта {rating}. Это значит, что этот сайт чище, чем {cleaner_than}% всех сайтов по всему миру')
                    bot.send_message(chat_id,
                                     f'Подробнее об углеродном рейтинге вы можете почитать здесь: https://www.websitecarbon.com/introducing-the-website-carbon-rating-system/')
                    start(message)
                except Exception as e:
                    print(e)
                    bot.send_message(message.chat.id,
                                     'Произошла неизвестная ошибка. Пожалуйста, попробуйте еще раз')


@bot.callback_query_handler(func=lambda call: call.data == 'rating')
def rating_btn(call):
    message = call.message
    chat_id = message.chat.id
    try:
        response = api.select_top_websites(cursor, chat_id)
        if response:
            bot.edit_message_text(chat_id=chat_id, message_id=message.id,
                                  text='Так держать! Проверьте как можно больше сайтов, чтобы получить ТОП 10 самых "грязных" проверенных сайтов')
            show_rating_picture(chat_id, response)
            keyboard = telebot.types.InlineKeyboardMarkup()
            button_clean = telebot.types.InlineKeyboardButton(text="Очистить",
                                                              callback_data='clean')
            button_back = telebot.types.InlineKeyboardButton(text="Вернуться",
                                                             callback_data='back')
            keyboard.add(button_clean)
            keyboard.add(button_back)
            bot.send_message(message.chat.id,
                             'Очистить данные всех запросов?',
                             reply_markup=keyboard)
        else:
            bot.edit_message_text(chat_id=chat_id, message_id=message.id,
                                  text='Начните проверять сайты, чтобы составить персональный рейтинг!')
            bot.send_message(chat_id, text='Введите адрес сайта, который вы хотите проверить')
            users_url[chat_id] = {}

            bot.register_next_step_handler(message, save_url)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id,
                         'Произошла неизвестная ошибка. Пожалуйста, попробуйте еще раз')


def show_rating_picture(chat_id, request):
    data = {
        'url': [],
        'carbon_grams': []
    }
    for url, grams in request:
        data['url'].append(url)
        data['carbon_grams'].append(float(grams))

    df = pd.DataFrame(data)
    df_sorted = df.sort_values(by='carbon_grams', ascending=False)
    colors = plt.cm.viridis(np.linspace(0, 1, len(df_sorted)))
    plt.figure(figsize=(12, 6))
    plt.bar(df_sorted['url'], df_sorted['carbon_grams'], color=colors)
    plt.title('ТОП 10 самых неэкологичных запрошенных сайтов', fontsize=14)
    plt.xlabel('URL', fontsize=16)
    plt.ylabel('Количество углерода (грамм)', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = BytesIO()  # Сохраняем гистограмму в объект BytesIO
    plt.savefig(buf, format='png')
    buf.seek(0)  # Возвращаемся в начало буфера
    plt.close()
    bot.send_photo(chat_id=chat_id, photo=buf)


@bot.callback_query_handler(func=lambda call: call.data == 'clean')
def clean_btn(call):
    message = call.message
    chat_id = message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=message.id,
                          text='Чистим историю запросов...')
    try:
        api.delete_user_history(cursor, connection, chat_id)
        bot.send_message(chat_id=chat_id,
                         text='Успешно!')
        start(message)
    except Exception as e:
        print(e)
        bot.send_message(message.chat.id,
                         'Произошла неизвестная ошибка. Пожалуйста, попробуйте еще раз')


@bot.callback_query_handler(func=lambda call: call.data == 'about')
def about_btn(call):
    message = call.message
    chat_id = message.chat.id
    bot.edit_message_text(chat_id=chat_id, message_id=message.id,
                          text={about_text})
    start(message)


@bot.callback_query_handler(func=lambda call: call.data == 'back')
def back_to_menu(call):
    message = call.message
    bot.delete_message(message.chat.id, message_id=message.id)
    bot.answer_callback_query(call.id)
    start(message)


bot.polling(none_stop=True)
