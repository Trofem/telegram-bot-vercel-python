
import asyncio,os, json
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from api.school_time import schedule, calendar, rtu, create_and_return_for_bot


inline_keyboard_buttons = {
    "КПС12-24":         InlineKeyboardButton("КПС12-24", callback_data="kps12-24-schedule"),
    "Автор":            InlineKeyboardButton("Автор", callback_data='author'),
    "Изменить группу":  InlineKeyboardButton("Изменить группу", callback_data='change_group'),
    "Помощь":           InlineKeyboardButton("Помощь", callback_data='help'),
    "Доп. опции":       InlineKeyboardButton("Доп. опции", callback_data='other_options'),
    "Назад":            InlineKeyboardButton("Назад", callback_data='back_to_start'),
    "1 группа":         InlineKeyboardButton("1 группа", callback_data='1-st-group'),
    "2 группа":         InlineKeyboardButton("2 группа", callback_data='2-nd-group'),
    "- Сегодня -":      InlineKeyboardButton("- Сегодня -", callback_data=f'kps12-24-schedule'),
}


# Применение nest_asyncio
nest_asyncio.apply()

# Токен вашего бота
TOKEN = os.environ.get('TOKEN')
bot_username = "@schedule_rtu_bot"
directory_path = os.path.dirname(os.path.abspath(__file__))
database:dict

async def main():
    # Загрузка базы данных
    global database
    database = read_from_database()

    print("Запуск бота...")
    app = Application.builder().token(TOKEN).build()

    # Добавляем команды
    command_dict = {
    "start": start_command,
    "help": help_command,
    "group_choice": group_choice_command,
    "author": author_command
    }

    [app.add_handler(
        CommandHandler(list(command_dict.keys())[i], list(command_dict.values())[i])
    ) for i in range(len(command_dict))]

    # Обработка нажатий на кнопки
    app.add_handler(CallbackQueryHandler(button_click))

    #обработка ошибок (Важно)
    #app.add_error_handler(error)
    
    # Обработка сообщений
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    

    # Запуск бота
    print("Бот запущен, ожидаем сообщения...")
    await app.run_polling(poll_interval=2)

## функция для того, что-бы понять откуда получена комманда/функция 
async def update_message_or_callback_query(update: Update):
    if update.message:
        return update
    else:
        return update.callback_query

# функция что-бы получить от какого пользователя мы получаем информацию
async def get_from_user(update: Update):
    if update.message:
        return update.message.from_user
    elif update.callback_query:
        return update.callback_query.from_user

## асинхронное отправление любого сообщения
async def send_message(update: Update, text:str,reply_markup=None):
    await (
        update if update.message else update.callback_query
        ).message.reply_text(text,reply_markup=reply_markup)

## Функция для получения имени пользователя
async def get_user_name(update: Update) -> str:
    try:
        return str((await get_from_user(update)).first_name)

    except:
        return None

## Функция для получения ID пользователя
async def get_id(update: Update) -> str:
    try:
        return str((await get_from_user(update)).id)
    except:
        return None

## Есть ли пользователь в датабазе
async def user_in_system(update: Update):
    id = await get_id(update)
    print("check for", id)
    if id in database:
        print(f"user exist")

    else:
        print("user is not exist ")
    return await get_id(update) in database  # Проверка, есть ли пользователь в базе данных

## Команда /start с отображением кнопок
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Старт пользователем", await get_user_name(update))
    # Определяем кнопки
    starting_keyboard = [
        [
            inline_keyboard_buttons["КПС12-24"],
            inline_keyboard_buttons["Помощь"],
            inline_keyboard_buttons["Доп. опции"]
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(starting_keyboard)
    text = f"Привет, {await get_user_name(update)}! \nВыбери действие:\n{await get_id(update)}"
    await send_message(update,text,reply_markup=reply_markup)

## Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = f"""Привет, {await get_user_name(update)}!
Для начала работы, выбери одну из кнопок при вызове /start.

Пока что в боте такой набор функциональных кнопок:
- >  КПС12-24 (расписание, выбор группы),
- >  Помощь,
- >  Доп. опции (открывает остальные кнопки):
    - >  Автор,
    - >  Изменить группу (появляется если вы уже выбирали)."""

    reply_markup = InlineKeyboardMarkup([
        [inline_keyboard_buttons["Назад"]
    ]])
    #отправляем ответ
    await send_message(update,help_text,reply_markup=reply_markup)

async def other_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Выбраны дополнительные функции")
    # Определяем кнопки
    addition_keyboard = [[
            inline_keyboard_buttons["Автор"]
    ]]
    if await user_in_system(update):
        addition_keyboard[0].append([
            inline_keyboard_buttons["Изменить группу"]
        ])
    #ставим кнопку назад под конец
    addition_keyboard[0].append([
        inline_keyboard_buttons["Назад"]
    ])


    reply_markup = InlineKeyboardMarkup(addition_keyboard)
    message_back = f"Дополнительные опции:"
    
    await send_message(update,message_back,reply_markup=reply_markup)


## Функция для кнопки Автор
async def author_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ("Создатель бота:\nАлёшин Трофим (@TrofimAl).")

## Функция для кнопки КПС12-24
async def kps_12_schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE, offset_in_days: int = -1):
    user_id = await get_id(update)  # Получаем ID пользователя
    user_group = database.get(user_id, {}).get('group', 0)  # Достаём группу пользователя из базы данных
    offset_in_days = await get_offset(update) if offset_in_days == -1 else offset_in_days
    if not user_group:  # Если группа не выбрана
        await update.callback_query.message.reply_text("Группа не выбрана! Пожалуйста, выберите группу.")
        return

    schedule_array = await create_and_return_for_bot(offset_in_days)
    if schedule_array != "N":
        subject_order_list = f";|n- ".join(
        [
            ", ".join(
                schedule_array[i] if schedule_array[i] != () else "^") for i in range(
                    1, len(schedule_array)+1 
                )
            ]
        )
    else:
        subject_order_list = "Нету пар в этот день"

    # Формируем ответное сообщение для расписания
    message_back = f"""{f"Будующее на {offset_in_days} шаг(а)" if offset_in_days > 0 else "Сегодня" if offset_in_days == 0 else f"Прошлое на {offset_in_days} шаг(а)"}: {await calendar.date()}, {"нечётная (жёлтая)" if calendar.is_odd_week_state else "чётная (белая)"} неделя.
|nРасписание для {user_group}-ой группы:|n- { subject_order_list };""".replace("\n","").replace("|n", "\n").replace("^", "Нету пары")


    # Клавиатура для управления днями
    schedule_keyboard = [
        [
            InlineKeyboardButton("- Вчера", callback_data=f"kps12-24-scheduleN-{offset_in_days - 1}"),
            inline_keyboard_buttons["- Сегодня -"],
            InlineKeyboardButton("Завтра -", callback_data=f'kps12-24-scheduleN-{offset_in_days + 1}')
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(schedule_keyboard)

    # Отправляем ответное сообщение с расписанием
    await send_message(update,message_back, reply_markup=reply_markup)

async def get_offset(update: Update) -> int:
    return database.get(await get_id(update), {}).get('offset', 0)

async def set_offset(update: Update, offset: int):
    print("оффсет равен", offset)
    await dump_in_database(update, offset=offset)


async def group_choice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Определяем кнопки
    group_choose_keyboard = [[
            InlineKeyboardButton("1 группа", callback_data='1-st-group'),
            InlineKeyboardButton("2 группа", callback_data='2-nd-group'),
            InlineKeyboardButton("Назад", callback_data='back_to_start')
    ]]
    reply_markup = InlineKeyboardMarkup(group_choose_keyboard)
    message_back = f"Выбери группу, в которой состоишь:\n(Уроки, где в расписании кабинетов несколько, будет выбрана та, которая актуальна в тот день недели и для твоей группы!)"
    
    if update.message:
        await update.message.reply_text(message_back, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(message_back, reply_markup=reply_markup)
        

# Функция для смены группы (смена группы в school_time)

async def change_group(update:Update, context: ContextTypes.DEFAULT_TYPE, group_num:int):
    await dump_in_database(update, group_num)  # Изменение группы пользователя в базе данных
    await schedule.generate_raw_schedule()  # Пересчёт расписания
    await update.callback_query.message.reply_text(f"Вы выбрали {group_num}-ю группу:")
    await kps_12_schedule_command(update, context, 0)  # Вызываем обновлённое расписание


### Обработка нажатий на все кнопки
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global database
    query = update.callback_query
    await query.answer()
    
    # Проверяем, что database инициализирована
    if not isinstance(database, dict):
        database = read_from_database()  # Загружаем базу данных, если она не была загружена

    print(f"Пользователь: {await get_user_name(update)}")

    button_name = query.data
    if 'kps12-24-schedule' in button_name:
        #print(database)
        print(f"Выбор группы" if not await user_in_system(update) else f"Выдача расписания" )
        offset_in_days = 0
        if "N" in button_name:
            sep_index = button_name.find("N")
            try:
                offset_in_days = int(button_name[sep_index+2:])
                print("фактор посчитался:" , offset_in_days)
            except:
                print("ну вроде фактор есть но ошибочка")
                print(button_name[sep_index+1:])

        if await user_in_system(update):
            # Устанавливаем новый offset_in_days
            await set_offset(update, offset_in_days)
            await kps_12_schedule_command(update, context)
        else:
            await group_choice_command(update, context)

    elif button_name == "change_group":
        print("изменяет группу!")
        await group_choice_command(update, context)
    elif button_name == "help":
        await help_command(update, context)
    elif button_name == "1-st-group":
        await change_group(update, context, 1)
    elif button_name == "2-nd-group":
        await change_group(update, context, 2)
    elif button_name == "other_options":
        await other_options(update,context)
    elif button_name == 'back_to_start':
        await start_command(update, context)
    elif button_name == 'author':
        await author_command(update, context)



async def dump_in_database(update:Update,value=None, offset=None):
    key = await get_id(update)
    global database
    if key is not None:
        if key not in database:
            
            database[key] = {'group': None, 'offset': 0}
        if value is not None:
            database[key]['group'] = value
        if offset is not None:
            database[key]['offset'] = offset
        print("внесли значение с ключом", key,":", value, offset )
        
        with open(directory_path + "/database.json", "w", encoding="utf-8") as file:
            json.dump(database, file, ensure_ascii=False, indent=4)
    
    #print(str(database))

def read_from_database():
    global database
    try:
        with open(directory_path + "/database.json", "r", encoding="utf-8") as file:
            print("база данных была загружена")
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        print("Пустая или некорректная база данных, создаём с нуля...")
        return {}  # Инициализация пустого словаря
        
async def check_database(key):
    global database
    if not database == {}:
        return key in read_from_database()
    else:
        return False


# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        response = handle_response(update.message.text)
    elif update.callback_query:
        response = handle_response(update.callback_query.message.text)
    else:
        return
    if response:
        print("Бот:", response)
        await update.message.reply_text(response)

def handle_response(text: str) -> str:
    processed: str = text.lower()
    if "hello" in processed:
        return "привет"
    return None

# Обработка ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error_value = f"\nUpdate {update} вызвал ошибку {context.error}\nЕсли это видите, напишите @TrofimAl, чтобы пофиксил баг."
    await send_message(update, error_value)
    print(error_value)



asyncio.run(main())
