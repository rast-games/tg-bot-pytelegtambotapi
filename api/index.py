import os
import time
from flask import Flask, Response, request
from dotenv import load_dotenv
import telebot
import requests
from googletrans import Translator

load_dotenv()

# Получаем токен из переменных окружения
TOKEN = os.getenv('token')

if not TOKEN:
    raise ValueError("Bot token is not set in environment variables!")

# Инициализация бота и API
Api = os.getenv("ApiDeepSeekDifferentServer")
translator = Translator()

if not Api:
    raise ValueError("API не установлен в переменных окружения!")


# Создаем Flask приложение
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)


@app.route("/")
def index():
    return "Hello World!"

@app.route("/setWebhook")
def set_webhook():
    try:
        bot.remove_webhook()

        # 1. Проверяем наличие обязательных переменных
        vercel_url = os.getenv("VERCEL_URL")
        if not vercel_url:
            return "<h1>Error: VERCEL_URL not set</h1>", 500

        # 2. Устанавливаем вебхук с таймаутом
        try:
            bot.remove_webhook()
            time.sleep(1)
            webhook_url = f"{vercel_url}/webhook"

            # Важно: set_webhook может вызывать 500 при таймаутах
            bot.set_webhook(
                url=webhook_url,
                timeout=10  # Явно указываем таймаут
            )

            return f"<h1>Bot is running. Webhook: {webhook_url}</h1>"

        except Exception as webhook_error:
            # Возвращаем 200 даже при ошибке, чтобы не ломать health-check
            return f"<h1>Bot running (webhook error: {str(webhook_error)})</h1>", 200

    except Exception as e:
        return f"<h1>Critical error: {str(e)}</h1>", 500

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        json_data = request.stream.read().decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
    return 'ok', 200




# Глобальные переменные
flag = True
back = telebot.types.KeyboardButton("❌Назад")


# Обработчики команд
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "🤣Рандом шутка про Чака Нориса",
        "❓Задать вопрос(Q&A)",
        #"🖼Описание фото"
    ]
    markup.add(*[telebot.types.KeyboardButton(btn) for btn in buttons])
    bot.send_message(message.chat.id, "Здравствуйте, Сэр", reply_markup=markup)


# Остальные обработчики (без изменений)
@bot.message_handler(func=lambda x: x.text == "🤣Рандом шутка про Чака Нориса")
def get_joke(message):
    response = requests.get('https://api.chucknorris.io/jokes/random').json()
    translated = translator.translate(response['value'], src='en', dest="ru").text
    bot.send_message(message.chat.id, translated)

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(back)
    bot.send_message(message.chat.id, "Смешно?...Сосал?", reply_markup=markup)


def split_send(text: str, chat_id: int, parse_mode=None):
    """Улучшенная функция отправки частями"""
    for i in range(0, len(text), 4096):
        bot.send_message(chat_id, text[i:i + 4096], parse_mode=parse_mode)


@bot.message_handler(func=lambda x: x.text == "❓Задать вопрос(Q&A)")
def give_question(message):
    global flag
    flag = True
    bot.send_message(message.chat.id, "Пишите вопрос")


@bot.message_handler(func=lambda message: flag, content_types=['text'])
def get_answer(message):

    # Конфигурация API
    headers = {
        'Authorization': f'Bearer {Api}',
        'content-type': 'application/json'
    }

    data = {
        "model": "deepseek-ai/DeepSeek-R1",
        "messages": [
            {"role": "system", "content": "Отвечай на русском.Мысли на русском."},
            {"role": "user", "content": ''}
        ],
        "temperature": 0.7
    }

    try:
        data['messages'][1]['content'] = message.text
        try:
            response = requests.post(
                'https://api.intelligence.io.solutions/api/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=10  # Всегда устанавливайте таймаут
            )
            response.raise_for_status()  # Проверка на 4XX/5XX ошибки
        except requests.exceptions.RequestException as e:
            print(f"API Request Failed: {str(e)}")
            bot.send_message(message.chat.id, "⚠️ Ошибка API. Попробуйте позже.")

        if response.ok:
            answer = response.json()["choices"][0]["message"]["content"]
            parts = answer.split("<think>")[1].split("</think>")
            thinking, answer_text = parts[0], parts[1]
            split_send(f"_{thinking}_ {answer_text}", message.chat.id, "Markdown")
        else:
            bot.send_message(message.chat.id, f"Ошибка API: {response.status_code}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")
    finally:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(back)
        bot.send_message(message.chat.id, "Спасибо за вопрос", reply_markup=markup)


@bot.message_handler(func=lambda x: x.text == "❌Назад")
def back_handler(message):
    global flag
    flag = False
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        "🤣Рандом шутка про Чака Нориса",
        "❓Задать вопрос(Q&A)"
    ]
    markup.add(*[telebot.types.KeyboardButton(btn) for btn in buttons])
    bot.send_message(message.chat.id, "Вы в главном меню", reply_markup=markup)



