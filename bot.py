import telebot
from telebot import types
import uuid
import requests
import json
import schedule
import qrcode
import io
import time as t
import calendar
from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta
from threading import Thread
from flask import Flask, request, jsonify
from sqlalchemy import Column, ForeignKey, Integer, ARRAY, String, Boolean, Text, Date, DateTime, Table, MetaData, create_engine, delete, select, insert, update, and_, or_, not_, func

bot = telebot.TeleBot('', threaded=True, num_threads=20) #live

app = Flask(__name__)
API_SECRET = ''

commands = [types.BotCommand("start", "Запустить бота"),
            types.BotCommand("offer", "Оферта")]
bot.set_my_commands(commands, scope = types.BotCommandScopeAllPrivateChats())

admins = ['457250506', '751215557']
adminsCommands = [types.BotCommand("start", "Запустить бота"),
                  types.BotCommand("stats", "Посмотреть статистику"),
                  types.BotCommand("new_codes", "Ввести коды"),
                  types.BotCommand("actual_codes", "Имеющиеся коды"),
                  types.BotCommand("count", "Уникальные посетители"),
                  types.BotCommand("purchases", "Посмотреть покупки"),
                  types.BotCommand("price", "Установить цену"),
                  types.BotCommand("test", "тестовая оплата"),
                  types.BotCommand("stop", "Остановить бота"),
                  types.BotCommand("offer", "Оферта")
                 ]
for admin in admins:
    bot.set_my_commands(adminsCommands, types.BotCommandScopeChat(admin))

def catch_all_errors(func): # обработчик ошибок
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            bot.send_message(457250506, f"[!] Сбой в {func.__name__}\nArgs: {args}\nkwargs: {kwargs}\n{e}")
            print(f"[!] Сбой в {func.__name__}\nArgs: {args}\nkwargs: {kwargs}\n{e}")
            return None
    return wrapper

@app.route('/webhook', methods=['GET', 'POST'])
@catch_all_errors
def itpay_webhook():
    with engine.begin() as connection:
        data = request.json
        event_type = data["type"]        
        
        if event_type == 'payment.completed':
            self_id = data['data']['client_payment_id']
            value = data['data']['description'][-3:-1]
            
            if data['data']['description'][-4:] == 'test':
                result = connection.execute(select(payments)
                    .where(
                        payments.c.payload == self_id
                    )
                ).fetchone()
                code = result._mapping['code']
                connection.execute(update(payments)
                    .where(payments.c.payload == self_id
                    )
                    .values(
                        status = 'finished',
                        sellTime = datetime.today().replace(microsecond=0),
                        code = code
                    )
                )
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton(text = "🆘 Поддержка", url = f'https://t.me/'))
                bot.send_message(result._mapping['telegramId'], f'Спасибо за покупку 💚\n\nВаш код: **`{code}`**\n\nБудем ждать вас снова 😊', reply_markup = keyboard, parse_mode='Markdown')
                return jsonify({"status": 0}), 200
                
            result = connection.execute(select(codes)
                .where(codes.c.payload == self_id)
            ).fetchone()
            if result:
                code = result._mapping['code']
                connection.execute(update(codes)
                    .where(codes.c.payload == self_id)
                    .values(selled = True)
                )
    
                connection.execute(update(payments)
                    .where(payments.c.payload == self_id)
                    .values(
                        status = 'finished',
                        sellTime = datetime.today().replace(microsecond=0),
                        code = code
                    )
                )

                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton(text = "🆘 Поддержка", url = f'https://t.me/'))
                result = connection.execute(select(payments)
                    .where(payments.c.payload == self_id)
                ).fetchone()
                bot.send_message(result._mapping['telegramId'], f'Спасибо за покупку 💚\n\nВаш код: **`{code}`**\n\nБудем ждать вас снова 😊', reply_markup = keyboard, parse_mode='Markdown')
                return jsonify({"status": 0}), 200
                
            result = connection.execute(select(codes)
                .where(
                    and_(
                        codes.c.value == value,
                        codes.c.reserved == False,
                        codes.c.selled == False
                    )
                ).limit(1)
            ).fetchone()
                
            if result:
                code = result._mapping['code']
                connection.execute(update(codes)
                    .where(codes.c.code == code)
                    .values(
                        payload = self_id,
                        selled = True
                    )
                )
                
                connection.execute(update(payments)
                    .where(payments.c.payload == self_id)
                    .values(
                        status = 'finished',
                        sellTime = datetime.today().replace(microsecond=0),
                        code = code
                    )
                )
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton(text = "🆘 Поддержка", url = f'https://t.me/'))
                result = connection.execute(select(payments)
                    .where(payments.c.payload == self_id)
                ).fetchone()
                bot.send_message(result._mapping['telegramId'], f'Спасибо за покупку 💚\n\nВаш код: **`{code}`**\n\nБудем ждать вас снова 😊', reply_markup = keyboard, parse_mode='Markdown')
                return jsonify({"status": 0}), 200
                
            else:
                result = connection.execute(select(payments)
                    .where(payments.c.payload == self_id)
                ).fetchone()
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton(text = "Пользователь", url = f'https://t.me/{result._mapping["username"]}'))
                bot.send_message('457250506', f'Пользователь не получил свой код на {result._mapping["value"]}$\nId для бота {result._mapping["id"]}', reply_markup = keyboard, parse_mode='Markdown')
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton(text = "🆘 Поддержка", url = f'https://t.me/'))
                result = connection.execute(select(payments)
                    .where(payments.c.payload == self_id)
                ).fetchone()
                bot.send_message(result._mapping['telegramId'], f'🤔 Что-то пошло не по плану\nОбратитесь в поддержку 👇\nВаш уникальный номер заказа **`{self_id}`**', reply_markup = keyboard, parse_mode='Markdown')
                
        if event_type == 'payment.rejected':
            result = connection.execute(select(payments)
                .where(payments.c.payload == self_id)
            ).fetchone()
            bot.send_message(result._mapping['telegramId'], f'Кажется с оплатой что-то пошло не так\nПопробуйте обратиться в ваш банк 🏦', parse_mode='HTML')
            
        if event_type == 'payment.errored':
            result = connection.execute(select(payments)
                .where(payments.c.payload == self_id)
            ).fetchone()
            bot.send_message(result._mapping['telegramId'], f'Кажется с оплатой что-то пошло не так\nПопробуйте обратиться в ваш банк 🏦', parse_mode='HTML')
    
    return jsonify({"status": 0}), 200

@bot.message_handler(content_types=['photo'])
def command(message):

    if str(message.from_user.id) == '457250506':
        bot.send_message(message.from_user.id, message.photo.file_id)

@bot.message_handler(commands=['start', 'Start', 'hello', 'Hello', 'привет', 'Привет', 'старт', 'Старт'])
@catch_all_errors
def send_welcome(message):
    print(str(message))
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
        types.InlineKeyboardButton(text = "10$", callback_data = 'giftCards.10'),
        types.InlineKeyboardButton(text = "20$", callback_data = 'giftCards.20'),
        types.InlineKeyboardButton(text = "30$", callback_data = 'giftCards.30'))
    keyboard.row(types.InlineKeyboardButton(text = "Оферта 📑", url = "https://telegra.ph/"))

    try:
        bot.edit_message_caption(caption = f'<b>Привет, {message.from_user.first_name} 🙌🏻</b>\n\nВ нашем магазине можно приобрести подарочные коды для вашего айфона 📲\nЭто полностью легальный и самый доступный способ пополнения на данный момент 🔓', chat_id = message.from_user.id, message_id = message.message.id, reply_markup = keyboard, parse_mode='HTML')
    except:
        bot.send_photo(message.from_user.id, photo = 'AgACAgIAAxkBAAIBC2oQruE3c7y8L0x1FU8R8wnCboDKAAJNImsbdAOASC3G46qkQrTbAQADAgADeQADOwQ', caption = f'<b>Привет, {message.from_user.first_name} 🙌🏻</b>\n\nВ нашем магазине можно приобрести подарочные коды для вашего айфона 📲\nЭто полностью легальный и самый доступный способ пополнения на данный момент 🔓', reply_markup = keyboard, parse_mode='HTML')

@bot.message_handler(commands=['new_codes'])
@catch_all_errors
def new_codes(message):
    if str(message.from_user.id) in admins:
        bot.send_message(message.from_user.id, "Вы в режиме ввода новых кодов.\nВведите их в виде код пробел номинал в долларах и следующий с новой строки, но не более 50.\nВот пример.\nGKHVRR962JTKGHQW 10\nDUMLR7462RKCDAPV 20")
        bot.register_next_step_handler(message, next_new_codes)

@catch_all_errors
def next_new_codes(message):
    newCodesText = str(message.text)
    if newCodesText.count("\n") > 49:
        bot.send_message(message.from_user.id, 'Ошибка. Более 50 строк')
        return
    parseLineCodes = newCodesText.split("\n")
    parts = []
    for line in parseLineCodes:
        parts.append(line + '\n')
    recollectParseLineCodes = "".join(parts)
    
    bot.send_message(message.from_user.id, f"Проверьте, всё правильно? Если всё верно напишите 'да'.\n{recollectParseLineCodes}")
    bot.register_next_step_handler(message, new_codes_final_step, parseLineCodes)

@catch_all_errors   
def new_codes_final_step(message, parseLineCodes):
    if str(message.text).lower() == "да":
        with engine.begin() as connection:
            codesInsert = []
            for codesPart in parseLineCodes:
                codesInsert.append({
                    'value': codesPart[-2:],
                    'code': codesPart[:-3],
                    'insertTime': datetime.today().replace(microsecond=0),
                    'reserved': False                                    
                })
            connection.execute(insert(codes)
                .values(codesInsert)
            )
        bot.send_message(message.from_user.id, f"Коды успешно добавлены")
    else:
        bot.send_message(message.from_user.id, f"Коды не добавлены")
        
@bot.message_handler(commands=['actual_codes'])
@catch_all_errors
def actual_codes(message):
    if str(message.from_user.id) in admins:
        with engine.begin() as connection:
            r = connection.execute(select(codes.c.value, func.count())
                .where(codes.c.selled == False)
                .group_by(codes.c.value)
            )
            count_dict = {row.value: row.count for row in r}
        bot.send_message(message.from_user.id, f"Действующие коды:\n{count_dict}")
    
@bot.message_handler(commands=['stats'])
@catch_all_errors
def stats(message, startDate = datetime.today().date(), chosenDay = 0, activeUsers = 0, newUsers = 0, back = False):
    if str(message.from_user.id) in admins:
        keyboard = types.InlineKeyboardMarkup()
        listFull = []
        listButton = []
        print(startDate)
        todayDate = datetime.today().date()
        if startDate == todayDate or startDate == date(todayDate.year, todayDate.month, 1):
            buttonTextPlus = " "
            buttonCallbackPlus = "1"
        else:
            buttonTextPlus = "➡️"
            buttonCallbackPlus = "Stats.+." + str(startDate)
        startDate = date(startDate.year, startDate.month, 1)
        keyboard.add(types.InlineKeyboardButton(text = str(startDate.strftime("%B")) + " " + str(startDate.year), callback_data = '1'))
        for i in range(1, calendar.monthrange(startDate.year, startDate.month)[1] + 1):
            if i == 1:
                for x in range(startDate.weekday()):
                    listButton.append(types.InlineKeyboardButton(text = " ", callback_data = "1"))
            listButton.append(types.InlineKeyboardButton(text = str(startDate.day + i - 1), callback_data = "Stats." + str(date(startDate.year, startDate.month, startDate.day + i - 1))))
            # print(str(date(startDate.year, startDate.month, startDate.day + i - 1))) #debug
            if date(startDate.year, startDate.month, startDate.day + i - 1).weekday() == 6:
                keyboard.row(listButton[0], listButton[1], listButton[2], listButton[3], listButton[4], listButton[5], listButton[6])
                listButton = []
        for i in range(6 - date(startDate.year, startDate.month, calendar.monthrange(startDate.year, startDate.month)[1]).weekday()):
            listButton.append(types.InlineKeyboardButton(text = " ", callback_data = "1"))
            if date(startDate.year, startDate.month, calendar.monthrange(startDate.year, startDate.month)[1]).weekday() + 1 + i == 6:
                keyboard.row(listButton[0], listButton[1], listButton[2], listButton[3], listButton[4], listButton[5], listButton[6])
        keyboard.row(types.InlineKeyboardButton(text = "⬅️", callback_data = "Stats.-." + str(startDate)), types.InlineKeyboardButton(text = buttonTextPlus, callback_data = buttonCallbackPlus))
            #⬅️➡️
        if chosenDay != 0:
            bot.edit_message_text(str(chosenDay) + " " + str(startDate.strftime("%B")) + "\nАктивных пользователей: " + str(activeUsers) + "\nНовых пользователей: " + str(newUsers), str(message.from_user.id), str(message.message.id), reply_markup = keyboard)
            # "A request to the Telegram API was unsuccessful. Error code: 400. Description: Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message":
            # bot.send_message(message.from_user.id, "Активных пользователей: " + str(activeUsers), reply_markup = keyboard)
        elif back == True:
            bot.edit_message_text("Выберите день", str(message.from_user.id), str(message.message.id), reply_markup = keyboard)
        else:
            bot.send_message(message.from_user.id, "Выберите день", reply_markup = keyboard)
            
@bot.message_handler(commands=['test'])
@catch_all_errors
def test(message):
    if str(message.from_user.id) in admins:
        price = check_price('Test')
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🛒Купить", callback_data = 'Test'))
        bot.send_photo(message.from_user.id, photo = 'AgACAgIAAxkBAAIBC2oQruE3c7y8L0x1FU8R8wnCboDKAAJNImsbdAOASC3G46qkQrTbAQADAgADeQADOwQ', caption =  f"Тестовая `подарочная` карта за 1р", reply_markup = keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['stop'])
@catch_all_errors
def stop_polling_manual(message):
    if str(message.from_user.id) in admins:
        bot.send_message(457250506, "stop polling manual")
        bot.stop_polling()

@bot.message_handler(commands=['count'])
@catch_all_errors
def command(message):
    with engine.begin() as connection:
        r = connection.execute(func.count().select().select_from(users)).fetchall()
        for row in r:
            bot.send_message(message.from_user.id, "Количество уникальных посетителей " + str(row[0]))
    
@bot.message_handler(commands=['purchases'])
@catch_all_errors
def purchases(message):
    if str(message.from_user.id) in admins:
        bot.send_message(message.from_user.id, "Вы в режиме просмотра покупок, введите email покупателя.")
        bot.register_next_step_handler(message, next_purchases)

@catch_all_errors   
def next_purchases(message):
    email = str(message.text)
    with engine.begin() as connection:
        r = connection.execute(select(codes)
            .where(codes.c.email == email)
        ).fetchall()
        if len(r) == 0:
            bot.send_message(message.from_user.id, 'Такого покупателя нет')
        else:
            for i in r:
                bot.send_message(message.from_user.id, 'email ' + str(i[0]) + '\n' + 
                                                       'payload ' + str(i[1])  + '\n' + 
                                                       'telegramId ' + str(i[2])  + '\n' + 
                                                       'providerId ' + str(i[3])  + '\n' + 
                                                       'type ' + str(i[4])  + '\n' + 
                                                       'time ' + str(i[6])
                )
                t.sleep(1)

@bot.message_handler(commands=['price'])
@catch_all_errors
def set_price(message):
    if str(message.from_user.id) in admins:
        bot.send_message(message.from_user.id, "Вы в режиме изменения цены, будьте внимательны!\nЦена указывается для 10$ как множитель для всех остальных кодов.\nВведите стоимость кода 10$ как число в рублях.")
        bot.register_next_step_handler(message, main_price)

@catch_all_errors
def main_price(message):
    try:
        mainPrice = int(message.text)
    except:
        bot.send_message(message.from_user.id, 'Неправильное значение')
        return
    with engine.begin() as connection:
        r = connection.execute(select(price)).fetchall()
        if len(r) == 0:
            connection.execute(insert(price)
                .values(priceMultiplier = mainPrice)
            )
        else:
            connection.execute(update(price)
                .values(priceMultiplier = mainPrice)
            )
    bot.send_message(message.from_user.id, f'Множитель цены установлен в размере {mainPrice}')

@bot.callback_query_handler(func = lambda callback: True)
@catch_all_errors
def callback_message(callback):
    with engine.begin() as connection:
        r = connection.execute(func.count()
            .select()
            .select_from(statsForButtons)
            .where(
                and_(
                    statsForButtons.c.userId == str(callback.from_user.id),
                    statsForButtons.c.time.between(
                        datetime.today().date(),
                        datetime.today().date() + timedelta(days=1)
                    )
                )
            )
        ).fetchall()
        for row in r:
            if row[0] == 0:
                connection.execute(insert(statsForButtons)
                    .values(
                        userId = str(callback.from_user.id),
                        time = datetime.today().replace(microsecond=0)
                    )
                )

    # print(str(callback)) #debug
    if callback.data == 'Start':
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
        types.InlineKeyboardButton(text = "10$", callback_data = 'giftCards.10'),
        types.InlineKeyboardButton(text = "20$", callback_data = 'giftCards.20'),
        types.InlineKeyboardButton(text = "30$", callback_data = 'giftCards.30'))
        keyboard.row(types.InlineKeyboardButton(text = "Оферта 📑", url = "https://telegra.ph/"))

        try:
            bot.edit_message_caption(caption = f'<b>Привет, {callback.from_user.first_name} 🙌🏻</b>\n\nВ нашем магазине можно приобрести подарочные коды для вашего айфона 📲\nЭто полностью легальный и самый доступный способ пополнения на данный момент 🔓', chat_id = callback.from_user.id, message_id = callback.message.id, reply_markup = keyboard, parse_mode='HTML')
        except:
            bot.send_photo(callback.from_user.id, photo = 'AgACAgIAAxkBAAIBC2oQruE3c7y8L0x1FU8R8wnCboDKAAJNImsbdAOASC3G46qkQrTbAQADAgADeQADOwQ', caption = f'<b>Привет, {callback.from_user.first_name} 🙌🏻</b>\n\nВ нашем магазине можно приобрести подарочные коды для вашего айфона 📲\nЭто полностью легальный и самый доступный способ пополнения на данный момент 🔓', reply_markup = keyboard, parse_mode='HTML')
           
    if callback.data[:9] == 'giftCards': # giftCards.10
        prices = check_price(callback.data[10:12])
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🛒Купить", callback_data = f'QR.{callback.data[10:12]}.{prices}'))
        keyboard.add(types.InlineKeyboardButton(text = "⬅️Назад", callback_data = 'Start'))
        try:
            bot.edit_message_caption(caption =  f"Подарочная карта на {callback.data[10:12]}$, стоимость карты {str(prices)}р\nМы зарезервируем для вас код на 10 минут 🔐\nОсталось только оплатить, и мы пришлём ваш код 🎁", chat_id = callback.from_user.id, message_id = callback.message.id, reply_markup = keyboard, parse_mode='HTML')
        except:
            bot.send_photo(callback.from_user.id, photo = 'AgACAgIAAxkBAAIBC2oQruE3c7y8L0x1FU8R8wnCboDKAAJNImsbdAOASC3G46qkQrTbAQADAgADeQADOwQ', caption =  f"Подарочная карта на {callback.data[10:12]}$, стоимость карты {str(prices)}р'\nМы зарезервируем для ваш код номиналом на 5 минут 🔐\nОсталось только оплатить, и мы пришлём ваш код 🎁", reply_markup = keyboard, parse_mode='HTML')

    if callback.data[:2] == 'QR': # QR.10.150000
        keyboard = types.InlineKeyboardMarkup()

        if not code_available(callback.data[3:5]):
            keyboard.add(types.InlineKeyboardButton(text = "⬅️Назад", callback_data = 'Start'))
            try:
                bot.edit_message_caption(caption =  f"К сожалению коды на {callback.data[3:5]}$ у нас закончились 😓 попробуйте другие\nМы уведомим вас когда пополним их 💬", chat_id = callback.from_user.id, message_id = callback.message.id, reply_markup = keyboard, parse_mode='HTML')
            except:
                bot.send_photo(callback.from_user.id, photo = 'AgACAgIAAxkBAAIBC2oQruE3c7y8L0x1FU8R8wnCboDKAAJNImsbdAOASC3G46qkQrTbAQADAgADeQADOwQ', caption =  f"К сожалению коды на {callback.data[3:5]}$ у нас закончились 😓 попробуйте другие\nМы уведомим вас когда пополним их 💬", reply_markup = keyboard, parse_mode='HTML')
        else:
            with engine.begin() as connection:
                result = connection.execute(
                    select(codes.c.code).where(
                        and_(codes.c.selled == False,
                             codes.c.reserved == False,
                             codes.c.value == callback.data[3:5]
                        )
                    )
                ).fetchone()
                code = result._mapping['code']

                self_id = str(uuid.uuid4())
                connection.execute(update(codes)
                    .where(codes.c.code == code)
                    .values(
                        telegramId = str(callback.from_user.id),
                        payload = self_id,
                        reserved = True,
                        reservedTime = datetime.today().replace(microsecond=0)
                    )
                )

                price = check_price(callback.data[3:5])
                payload = {
                    "amount": f"{str(price)}.00",
                    "client_payment_id": self_id,
                    "method": "sbp",
                    "description": f"Gift {callback.data[3:5]}$",
                    "success_url": None
                }
                response = requests.post(
                    'https://api.gw.itpay.ru/v1/payments',
                    auth=('pk_58191_7b2635b5', API_SECRET),  # HTTP Basic Auth
                    json = payload,
                    timeout=10
                )
                try:
                    response.raise_for_status()
                except Exception:
                    bot.send_message(callback.from_user.id, "⚠️ У нас технические шоколадки\nПопробуйте попозже 😥", parse_mode='HTML')
                    raise
                    
                payment = response.json()
                providerId = payment["data"]["id"]
                qrc_id = payment["data"]["qrc_id"]
                url = payment["data"]["payment_qr_images"]["desktop"]
                qr_url = url.split('?data=')[1].split('?type=')[0]
                
                img = qrcode.make(qr_url)
                bio = io.BytesIO()
                img.save(bio, 'PNG')
                bio.seek(0)

    
                bot.send_photo(callback.from_user.id, photo = bio, caption = "Последний шаг, отсканируйте для оплаты 💳\nЕсли у вас возникнут сложности, мы обязательно поможем 🤝\n\n⚠️ Пожалуйста, оплатите заказ в течении 10 минут, если не успеваете, то запросите платёж ещё раз 🙏", parse_mode='HTML')

                
                connection.execute(insert(payments)
                    .values(
                        telegramId = str(callback.from_user.id),
                        username = str(callback.from_user.username),
                        qrc_id = qrc_id,
                        payload = self_id,
                        providerId = providerId,
                        status = 'new',
                        code = code,
                        value = callback.data[3:5]
                    )
                )
                

    if callback.data == 'Test': # QR.10.150000
        with engine.begin() as connection:

            self_id = str(uuid.uuid4())
            payload = {
                "amount": "1.00",
                "client_payment_id": self_id,
                "method": "sbp",
                "description": f"Gift test",
                "success_url": None
            }
            response = requests.post(
                'https://api.gw.itpay.ru/v1/payments',
                auth=('pk_58191_7b2635b5', API_SECRET),  # HTTP Basic Auth
                json = payload,
                timeout=10
            )
            try:
                response.raise_for_status()
            except Exception:
                bot.send_message(callback.from_user.id, "⚠️ У нас технические шоколадки\nПопробуйте попозже 😥", parse_mode='HTML')
                raise
                
            payment = response.json()
            providerId = payment["data"]["id"]
            qrc_id = payment["data"]["qrc_id"]
            url = payment["data"]["payment_qr_images"]["desktop"]
            qr_url = url.split('?data=')[1].split('?type=')[0]
            
            img = qrcode.make(qr_url)
            bio = io.BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)

            bot.send_photo(
                chat_id = callback.from_user.id,
                photo = bio,
                caption = "Последний шаг, отсканируйте для оплаты 💳\nЕсли у вас возникнут сложности, мы обязательно поможем 🤝\n\n⚠️ Пожалуйста, оплатите заказ в течении 10 минут или запросите платёж ещё раз 🙏",
                parse_mode='HTML'
            )
            
            connection.execute(insert(payments)
                .values(
                    telegramId = str(callback.from_user.id),
                    username = str(callback.from_user.username),
                    qrc_id = qrc_id,
                    payload = self_id,
                    providerId = providerId,
                    status = 'new',
                    code = str(uuid.uuid4().time_low),
                    value = 'тест'
                )
            )
                        
    if callback.data == '1':
        bot.send_message(callback.from_user.id, 'Пустая кнопка')

    if callback.data[:5] == 'Stats':
        # print(str(callback.data)) #debug
        # print(callback.data.split('.', 3)[2].split('-', 3)[0])
        todayDate = datetime.today().date()
        if callback.data[6] != "+" and callback.data[6] != "-":
            startDate = datetime.strptime(callback.data.split('.', 2)[1], '%Y-%m-%d').date()
            chosenDay = startDate.day
            startDate = date(startDate.year, startDate.month, 1)
            with engine.begin() as connection:
                r = connection.execute(func.count().select().select_from(statsForButtons)
                    .where(
                        statsForButtons.c.time.between(
                            datetime.strptime(callback.data.split('.', 2)[1], '%Y-%m-%d').date(),
                            datetime.strptime(callback.data.split('.', 2)[1], '%Y-%m-%d').date() + timedelta(days=1)
                        )
                    )
                )
                for row in r:
                    activeUsers = row[0]
                    
                r = connection.execute(func.count().select().select_from(users)
                    .where(users.c.time
                        .between(
                            datetime.strptime(callback.data.split('.', 2)[1], '%Y-%m-%d').date(),
                            datetime.strptime(callback.data.split('.', 2)[1], '%Y-%m-%d').date() + timedelta(days=1)
                        )
                    )
                )
                for row in r:
                    newUsers = row[0]
                    
            stats(callback, startDate, chosenDay, activeUsers, newUsers)
            
        elif callback.data[6] == "-":
            startDate = datetime.strptime(callback.data.split('.', 3)[2], '%Y-%m-%d').date() - relativedelta(months=1)
            chosenDay = 0
            stats(callback, startDate, chosenDay, back = True)
        else:
            startDate = datetime.strptime(callback.data.split('.', 3)[2], '%Y-%m-%d').date() + relativedelta(months=1)
            chosenDay = 0
            stats(callback, startDate, chosenDay, back = True)

@catch_all_errors
def code_available(value):
    with engine.begin() as connection:
        r = connection.execute(select(codes.c.code)
            .where(
                codes.c.selled == False,
                codes.c.reserved == False,
                codes.c.value == value
            )
        ).first()
        return(r != None)

@catch_all_errors
def check_price(giftValue):
    with engine.begin() as connection:
        r = connection.execute(select(price)).fetchall()
        priceMultiplier = r[0][0]
    prices = {}
    prices['10'] = priceMultiplier * 1
    prices['20'] = priceMultiplier * 2
    prices['30'] = priceMultiplier * 3
    prices['Test'] = 1
    return prices[giftValue]        
    
@catch_all_errors       
def listener(messages):
    for m in messages:
        # print(m) # debug
        with engine.begin() as connection:
            r = connection.execute(select(users)
                .where(users.c.userId == str(m.from_user.id))
            ).fetchall()
            if len(r) == 0:
                s = insert(users).values(
                    userId = str(m.from_user.id),
                    time = datetime.today().replace(microsecond=0)
                )
                connection.execute(insert(users)
                    .values(
                        userId = str(m.from_user.id),
                        time = datetime.today().replace(microsecond=0)
                    )
                )

@catch_all_errors
def reserved_remover():
    expired_time = datetime.today().replace(microsecond=0) - timedelta(minutes=10)
    with engine.begin() as connection:
        connection.execute(
            update(codes)
            .where(
                and_(
                    codes.c.reserved == True,
                    # codes.c.reservedTime.isnot(None),  # на случай NULL
                    codes.c.reservedTime < expired_time
                )
            )
            .values(reserved = False)
        )
    
@catch_all_errors
def stop_polling():
    bot.stop_polling()
    
@catch_all_errors
def runFlask():
    app.run(host='0.0.0.0', port=2345)
    
def schedule_checker():
    while True:
        schedule.run_pending()
        t.sleep(1)

if __name__ == '__main__':
    metadata = MetaData()

    codes = Table('codes', metadata,
        Column('email', String(100), nullable=True, comment='Email'),
        Column('payload', String(100), nullable=True, comment='SelfPayload'),
        Column('telegramId', String(100), nullable=True, comment='TelegramId'),    Column('providerId', String(100), nullable=True, comment='ProviderId'),
        Column('value', String(20), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Номинал кода'),
        Column('code', String(30), nullable=False, unique=True, primary_key=False, autoincrement=False, comment='Подарочный код'),
        Column('insertTime', DateTime(), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Время добавления кода'),
        Column('reserved', Boolean(), nullable=False, unique=False, primary_key=False, autoincrement=False, default=False, comment='Статус'),
        Column('reservedTime', DateTime(), nullable=True, unique=False, primary_key=False, autoincrement=False, comment='Время резервирования'),
        Column('selled', Boolean(), nullable=False, unique=False, primary_key=False, autoincrement=False, default=False, comment='Статус покупки'),
    )

    payments = Table('payments', metadata,
        Column('qrc_id', String(100), nullable=True, comment='Alfa qrc_id'),
        Column('payload', String(100), nullable=True, comment='SelfPayload'),
        Column('telegramId', String(100), nullable=True, comment='TelegramId'),
        Column('username', String(100), nullable=True, comment='@username'),    Column('providerId', String(100), nullable=True, comment='ProviderId'),
        Column('sellTime', DateTime(), nullable=True, unique=False, primary_key=False, autoincrement=False, comment='Время покупки'),
        Column('status', String(20), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Статус покупки'),
        Column('code', String(30), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Подарочный код'),
        Column('value', String(20), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Номинал кода')
    )
    
    price = Table('price', metadata,
        Column('priceMultiplier', Integer(), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Множитель цены')
    )
    
    users = Table('users', metadata,
        Column('userId', String(20), nullable=False, unique=True, primary_key=False, autoincrement=False, comment='Id пользователя'),
        Column('time', DateTime(), nullable=True, unique=False, primary_key=False, autoincrement=False, comment='Time')
    )

    statsForButtons = Table('statsForButtons', metadata,
        Column('userId', String(20), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Id пользователя'),
        Column('time', DateTime(), nullable=False, unique=False, primary_key=False, autoincrement=False, comment='Time')
    )
    

    engine = create_engine('postgresql://postgres:32313@db:5432/postgres', pool_pre_ping=True)
    metadata.create_all(engine)
    schedule.every(1).minutes.do(reserved_remover)
    Thread(target = schedule_checker, daemon=True).start()
    Thread(target = runFlask, daemon=True).start()
    bot.set_update_listener(listener)
    bot.infinity_polling()
