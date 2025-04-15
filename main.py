import os
from dotenv import load_dotenv
import telebot
import requests
from googletrans import Translator
from googletrans import LANGCODES
import base64

load_dotenv()
#работа с апи
Api = os.getenv("ApiDeepSeekDifferentServer")
token = os.getenv("token")

headers = {
'Authorization': 'Bearer ' + Api,
'content-type': 'application/json'
}


data = {
        "model": "deepseek-ai/DeepSeek-R1",
        "messages": [{"role": "system", "content": "Отвечай на русском.Мысли на русском."}, {"role": "user", "content": ''}],
        "temperature": 0.7
        }
bot = telebot.TeleBot(token)
translator = Translator()


#начальное сообщение
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    JokeButton = telebot.types.KeyboardButton("🤣Рандом шутка про Чака Нориса")
    QuestionAndAnswerButton = telebot.types.KeyboardButton("❓Задать вопрос(Q&A)")
    #AIvision = telebot.types.KeyboardButton("🖼Описание фото")
    markup.add(JokeButton, QuestionAndAnswerButton, AIvision)
    bot.send_message(message.chat.id, "Здравствуйте, Сэр", reply_markup=markup)


back = telebot.types.KeyboardButton("❌Назад")


#обработчик для рандомной шутки про Чака Норриса
@bot.message_handler(func=lambda x: x.text == "🤣Рандом шутка про Чака Нориса")
def get_joke(message):
    response = requests.get('https://api.chucknorris.io/jokes/random').json()
    translate_response = translator.translate(response['value'], src='en', dest="ru").text
    bot.send_message(message.chat.id, translate_response)
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(back)
    bot.send_message(message.chat.id, "Смешно?...Сосал?", reply_markup=markup)


#функия для разбиение ответа если он больше максимума тг
def split_send(ans: str, user_input, parse_mode: str = None) -> None:
    """
    Отправляет сообщение `ans` частями по 4096 символов.

    :param ans: Текст для отправки
    :param user_input: Объект с данными чата (должен иметь `user_input.chat.id`)
    :param parse_mode: Режим форматирования (например, 'Markdown')
    """
    chunk_size = 4096
    for i in range(0, len(ans), chunk_size):
        chunk = ans[i:i + chunk_size]
        bot.send_message(
            chat_id=user_input.chat.id,
            text=chunk,
            parse_mode=parse_mode
        )


flag = True


#обработчик для вода в меню (Q&A)
@bot.message_handler(func=lambda x: x.text == "❓Задать вопрос(Q&A)")
def give_question(message):
    global flag
    flag = True
    bot.send_message(message.chat.id, "Пишите вопрос")
    #вложенный обработчик для парсинга вопроса пользователя и последуещего ответа
    @bot.message_handler(func=lambda message: flag is True, content_types=['text'])
    def get_answer(user_input):
        try:
            data['messages'][1]['content'] = user_input.text
            response = requests.post('https://api.intelligence.io.solutions/api/v1/chat/completions', headers=headers, json=data)
            if response:
                j_answer = response.json()
                answer = j_answer["choices"][0]["message"]["content"]
                thinking = answer.split("<think>")[1].split(r"</think>")[0]
                answer_for_user = answer.split(r"</think>")[1]
                limit = len(answer) + len(thinking) + 3
                count = 1
                print(answer)
                if 4096 < limit:
                    count = limit // 4096 + (1 if limit % 4096 != 0 else 0)
                full_answer = f"_{thinking}_ {answer_for_user}"
                try:
                    #bot.send_message(user_input.chat.id, f"_{thinking}_ {answer_for_user}", parse_mode='Markdown')
                    split_send(full_answer, user_input, "Markdown")
                except:
                    split_send(full_answer, user_input)
                    #bot.send_message(user_input.chat.id, f"{thinking} {answer_for_user}")

            else:
                print(f"Ошибка работы с сетью, {response.status_code}")
                bot.send_message(message.chat.id, f"Ошибка работы с сетью, {response.status_code}")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при работе с API {str(e)}")
        finally:
            markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(back)
            bot.send_message(message.chat.id, "Спасибо за вопрос", reply_markup=markup)

#обработчик для выхода в главное меню
@bot.message_handler(func=lambda x: x.text == "❌Назад")
def Back(message):
    global flag
    flag = False
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    JokeButton = telebot.types.KeyboardButton("🤣Рандом шутка про Чака Нориса")
    QuestionAndAnswerButton = telebot.types.KeyboardButton("❓Задать вопрос(Q&A)")
    markup.add(JokeButton, QuestionAndAnswerButton)
    bot.send_message(message.chat.id, "Вы в главном меню", reply_markup=markup)


#@bot.message_handler(func=lambda x: x.text == "🖼Описание фото")
#def Vision(message):
#    global flag
#    @bot.message_handler(func=lambda m: flag is True)
#    def description(photo):


bot.polling(none_stop=True)