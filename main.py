import os
from dotenv import load_dotenv
import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types.message import ContentTypes
from aiogram.contrib.middlewares.logging import LoggingMiddleware

# Загрузка переменных окружения из .env файла
load_dotenv()

# Инициализация логгирования
logging.basicConfig(level=logging.INFO)

# Создание объекта бота, диспетчера и стореджа для сохранения состояний (выбора)
bot = Bot(token=os.getenv('TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Константы для текстов сообщений
START_TEXT = (
    f'Я - бот-помощник канала \U0001F517 <u><b><a href="https://t.me/iwantnewflat">Нам нужна квартира</a></b></u>.\n'
    f'Подбор новостроек для подписчиков канала бесплатен.\nЯ задам Вам несколько вопросов, а затем попрошу '
    f'одного из агентов прислать Вам подборку подходящих квартир.\nДоговорились?'
)
NEXT_TEXT = (
    f'Отлично, Мы уже готовы подобрать идеальную недвижимость для Вас!\nОстался всего один момент \U0001F609 \n'
    f'Пожалуйста введите Ваше номер телефона в формате <i><b>+79051234567</b></i> или <i><b>89051234567</b></i>'
)

SELECT_TEXT = (
    f'Расскажите, какая квартира Вас интересует?\nВы можете сделать это в произвольной форме\n'
    f'<i><b>Например:</b>\nХочу купить однушку не меньше 30 кв.м. в бюджете до 12 млн. Нужна московская прописка. </i>'
    f'<i>Хочу зелёный район и хорошую транспортную доступность. Отделка не важна. Перехать хочу до конца следующего года. </i>'
    f'<i>Маткапитала и субсидий нет.</i>\n\nили я могу задать ряд уточняющих вопросов. \n\nКак Вам будет удобнее?'
)

LAST_MESSAGE = (f'Не забудьте указать дополнительные пожелания к новой квартире Вашему Агенту \U0001F609')

ERROR_MSG = (f'Попробуйте начать заново, отправив мне команду <b>/start</b>')

AGENTS = [os.getenv('agent1'), os.getenv('agent2'), os.getenv('agent3'), os.getenv('agent4')]

# Обработка команды /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    user_name = message.from_user.first_name
    async with state.proxy() as data:
            data['user_name'] = user_name
    user = message.from_user
    if user.username:
        async with state.proxy() as data:
            data['user_nickname'] = user.username
    else:
        async with state.proxy() as data:
            data['user_nickname'] = None
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton('Далее', callback_data='get_phone')
    markup.add(button)
    await message.answer(text=f'Привет {user_name}!\n' + START_TEXT, reply_markup=markup, parse_mode=types.ParseMode.HTML)

# Обработка команды /dev
@dp.message_handler(commands=['dev'])
async def send_dev(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    info_button = types.InlineKeyboardButton("\U0001F98A Source", callback_data="github",
                                             url='https://github.com/nikohakerinc/apartment_search')
    markup.add(info_button)
    await message.answer(text='Created by @Niko_from_Niko', reply_markup=markup)

# Обработка нажатия кнопки 'Далее'
@dp.callback_query_handler(lambda c: c.data == 'get_phone')
async def process_callback_button(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, NEXT_TEXT, parse_mode=types.ParseMode.HTML)

# Обработка введенных пользователем данных
# ВНИМАНИЕ! Здесь немного костылей на условия пользовательского ввода.
# Для ограничения кол-ва символов в сообщении править цифру в первом if (сейчас 15 символов)
@dp.message_handler(content_types=ContentTypes.TEXT)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with state.proxy() as data:
                data['user_id'] = user_id
    async with state.proxy() as data:
        user_name = data.get('user_name')
    if len(message.text) <=15:
        phone_number = re.sub(r'\D', '', message.text)  # Удаление всех символов, кроме цифр
        # Номер телефона абонентов РФ - 11 цифр с учётом '7' или '8' в начале номера
        if len(phone_number) != 11:
            await message.reply(ERROR_MSG, parse_mode=types.ParseMode.HTML)
        elif len(phone_number) == 11 and not (phone_number.startswith('79') or phone_number.startswith('89')):
            await message.reply('Это не похоже на номер телефона')
        # Проверка что номер телефона 11 символов и содержит '79' или '89' в начале
        elif len(phone_number) == 11 and (phone_number.startswith('79') or phone_number.startswith('89')):
            async with state.proxy() as data:
                data['phone_number'] = phone_number
            markup = types.InlineKeyboardMarkup()
            button1 = types.InlineKeyboardButton('\U00002709 Опишу сам(а)', callback_data='send_text')
            button2 = types.InlineKeyboardButton('\U00002753 Задай вопросы', callback_data='use_buttons')
            markup.add(button1)
            markup.add(button2)
            await bot.send_message(message.chat.id, SELECT_TEXT, reply_markup=markup, parse_mode=types.ParseMode.HTML)
    else:
        user_input = message.text
        async with state.proxy() as data:
            data['user_input'] = user_input
        # Отправка уведомления пользователю (вызов фунции send_message)
        await send_message_to_user(state)
        # Сброс хранилища состояний для пользователя
        await state.finish()


# Выбор города
@dp.callback_query_handler(lambda c: c.data in ['send_text', 'use_buttons'])
async def process_callback_continue(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == 'send_text':
        await bot.send_message(callback_query.from_user.id, 'Напишите нам о квартире своей мечты')
    else:
        markup = types.InlineKeyboardMarkup()
        city1 = types.InlineKeyboardButton('Москва/Московская область', callback_data='city1')
        city2 = types.InlineKeyboardButton('Санкт-Петербург/Лен. область', callback_data='city2')
        city3 = types.InlineKeyboardButton('Другие регионы', callback_data='any_regions')
        city4 = types.InlineKeyboardButton('Другие страны', callback_data='any_countries')
        markup.add(city1)
        markup.add(city2)
        markup.add(city3)
        markup.add(city4)
        await bot.send_message(callback_query.from_user.id, text='В каком регионе Вы планируете покупку?', reply_markup=markup)

# Обработка выбранного горда, вопрос про ипотеку
@dp.callback_query_handler(lambda c: c.data in ['city1', 'city2', 'any_regions', 'any_countries'])
async def second_q(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == 'city1':
        city = 'Москва/Московская область'
    elif callback_query.data == 'city2':
        city = 'Санкт-Петербург/Лен. область'
    elif callback_query.data == 'any_regions':
        city = 'Другие регионы'
    elif callback_query.data == 'any_countries':
        city = 'Другие страны'
    async with state.proxy() as data:
            data['city'] = city
    markup = types.InlineKeyboardMarkup()
    yes_button = types.InlineKeyboardButton('Да', callback_data='choise_yes')
    no_button = types.InlineKeyboardButton('Нет', callback_data='choise_no')
    markup.add(yes_button)
    markup.add(no_button)
    await bot.send_message(callback_query.from_user.id, text='Покупку планируете в ипотеку?', reply_markup=markup)

# Обработка ответа про Ипотеку, вопрос про Первоначальный взнос
@dp.callback_query_handler(lambda c: c.data in ['choise_yes', 'choise_no'])
async def third_q(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == 'choise_yes':
        ipoteka = 'Да'
    elif callback_query.data == 'choise_no':
        ipoteka = 'Нет'
    async with state.proxy() as data:
            data['ipoteka'] = ipoteka
    markup = types.InlineKeyboardMarkup()
    percent_but1 = types.InlineKeyboardButton('Без первоначального взноса', callback_data='no_pv')
    percent_but2 = types.InlineKeyboardButton('До 1 млн рублей', callback_data='1mln')
    percent_but3 = types.InlineKeyboardButton('До 3 млн рублей', callback_data='3mln')
    percent_but4 = types.InlineKeyboardButton('До 5 млн рублей', callback_data='5mln')
    percent_but5 = types.InlineKeyboardButton('Свыше 5 млн рублей', callback_data='6mln')
    markup.add(percent_but1)
    markup.add(percent_but2)
    markup.add(percent_but3)
    markup.add(percent_but4)
    markup.add(percent_but5)
    await bot.send_message(callback_query.from_user.id,
                           text='Какой первоначальный взнос (ПВ) планируете внести?',
                           reply_markup=markup)

# Обработка выбора ПВ, вопрос по маткапитал или субсидии
@dp.callback_query_handler(lambda c: c.data in ['no_pv', '1mln', '3mln', '5mln', '6mln'])
async def fourth_q(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == 'no_pv':
        vznos = 'Без первоначального взноса'
    elif callback_query.data == '1mln':
        vznos = 'До 1 миллиона рублей'
    elif callback_query.data == '3mln':
        vznos = 'До 3 миллиона рублей'
    elif callback_query.data == '5mln':
        vznos = 'До 5 миллиона рублей'
    elif callback_query.data == '6mln':
        vznos = 'Свыше 5 миллиона рублей'
    async with state.proxy() as data:
            data['vznos'] = vznos
    markup = types.InlineKeyboardMarkup()
    kapital_but1 = types.InlineKeyboardButton('Да \U0001F642', callback_data='kapital_yes')
    kapital_but2 = types.InlineKeyboardButton('Нет \U0001F641', callback_data='kapital_no')
    markup.add(kapital_but1)
    markup.add(kapital_but2)
    await bot.send_message(callback_query.from_user.id,
                           text='Планируете ли использовать в качестве первоначального взноса маткапитал или иную субсидию?',
                           reply_markup=markup)

# Обработка ответа маткапитала, вопрос про дату сдачи объекта
@dp.callback_query_handler(lambda c: c.data in ['kapital_yes', 'kapital_no'])
async def fifth_q(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == 'kapital_yes':
        kapital = 'Да'
    elif callback_query.data == 'kapital_no':
        kapital = 'Нет'
    async with state.proxy() as data:
            data['kapital'] = kapital
    markup = types.InlineKeyboardMarkup()
    home_but1 = types.InlineKeyboardButton('Дом сдан', callback_data='00_year')
    home_but2 = types.InlineKeyboardButton('2024 год сдачи', callback_data='24_year')
    home_but3 = types.InlineKeyboardButton('2025 год сдачи', callback_data='25_year')
    home_but4 = types.InlineKeyboardButton('2026 год и далее', callback_data='26_year')
    home_but5 = types.InlineKeyboardButton('Не имеет значения', callback_data='never_mind_year')
    markup.add(home_but1)
    markup.add(home_but2)
    markup.add(home_but3)
    markup.add(home_but4)
    markup.add(home_but5)
    await bot.send_message(callback_query.from_user.id,
                           text='Планируемый срок сдачи объекта?',
                           reply_markup=markup)

# Обработка вопроса про дату сдачи, вопрос про отделку
@dp.callback_query_handler(lambda c: c.data in ['00_year', '24_year', '25_year', '26_year','never_mind_year'])
async def sixth_q(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == '00_year':
        year = 'Дом уже сдан'
    elif callback_query.data == '24_year':
        year = '2024'
    elif callback_query.data == '25_year':
        year = '2025'
    elif callback_query.data == '26_year':
        year = '2026 и далее'
    elif callback_query.data == 'never_mind_year':
        year = 'Не имеет значения'
    async with state.proxy() as data:
            data['year'] = year
    markup = types.InlineKeyboardMarkup()
    otdelka_but1 = types.InlineKeyboardButton('Чистовая отделка', callback_data='clean')
    otdelka_but2 = types.InlineKeyboardButton('Черновая с коммуникациями', callback_data='draft+')
    otdelka_but3 = types.InlineKeyboardButton('Черновая без коммуникаций', callback_data='draft-')
    otdelka_but4 = types.InlineKeyboardButton('Без отделки', callback_data='not_clean')
    markup.add(otdelka_but1)
    markup.add(otdelka_but2)
    markup.add(otdelka_but3)
    markup.add(otdelka_but4)
    await bot.send_message(callback_query.from_user.id, text='Отделка квартиры?', reply_markup=markup)

# Обработчик ответа про отделку
@dp.callback_query_handler(lambda c: c.data in ['clean', 'draft+', 'draft-', 'no_clean'])
async def last_message(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data == 'clean':
        otdelka = 'Чистовая'
    elif callback_query.data == 'draft+':
        otdelka = 'Черновая отделка с коммуникациями'
    elif callback_query.data == 'draft-':
        otdelka = 'Черновая отделка без коммуникаций'
    elif callback_query.data == 'no_clean':
        otdelka = 'Без отделки'
    async with state.proxy() as data:
            data['otdelka'] = otdelka
    await send_message_to_user(state)

# Функция отправки сообщения пользователю и владельцу канала
async def send_message_to_user(state: FSMContext):
    async with state.proxy() as data:
        user_nickname = data.get('user_nickname')
        user_name = data.get('user_name')
        user_id = data.get('user_id')
        phone_number = data.get('phone_number')
        user_input = data.get('user_input')
        city = data.get('city')
        ipoteka = data.get('ipoteka')
        vznos = data.get('vznos')
        kapital = data.get('kapital')
        year = data.get('year')
        otdelka = data.get('otdelka')

    message_text = ''

    agent_index = user_id % len(AGENTS)  # Вычисляем индекс агента из списка
    agent_to_send = AGENTS[agent_index]  # Получаем агента для отправки пользователю

    if user_input:
        message_text += (
            f'Клиент: {user_name}\n'
            f'Telegram: @{user_nickname}\n'
            f'Номер телефона: {phone_number}\n'
            f'Описание: {user_input}\n\n'
            f'Агент: {agent_to_send}'
        )
    else:
        message_text = (
            f'Клиент: {user_name}\n'
            f'Telegram: @{user_nickname}\n'
            f'Номер телефона: {phone_number}\n'
            f'Регион: {city}\n'
            f'Ипотека: {ipoteka}\n'
            f'Первоначальный взнос: {vznos}\n'
            f'Маткапитал или другая субсидия: {kapital}\n'
            f'Год сдачи объекта: {year}\n'
            f'Отделка: {otdelka}\n\n'
            f'Агент: {agent_to_send}'
        )

    await bot.send_message(os.getenv('GROUP_ID'), message_text)
    # Отправка сообщения пользователю
    await bot.send_message(user_id, LAST_MESSAGE)
    user_message = f'Спасибо!\nВаше обращение успешно создано. Ваш агент: {agent_to_send}'
    await bot.send_message(user_id, user_message)
    await state.finish()


if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
