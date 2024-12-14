from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta
import logging

# Настройки логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Ваш токен от BotFather
TOKEN = "7647642013:AAE2qHBWTKPKx7EhUOlK28YmtEbcuvtyJ48"
OWNER_CHAT_ID = "289636084"  # Ваш ID

# Словарь для хранения сообщений от пользователей
user_messages = {}

# Функция для команды /start
async def start(update: Update, context: CallbackContext) -> None:
    # Создаём inline клавиатуру с кнопкой "Услуги"
    keyboard = [
        [InlineKeyboardButton("Записаться на студию", callback_data='book_studio')],
        [InlineKeyboardButton("Услуги", callback_data='services')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем обновлённое приветственное сообщение
    await update.message.reply_text(
        "Привет! Я помогу вам записаться на студию. Нажмите кнопку ниже, чтобы начать.",
        reply_markup=reply_markup
    )

# Функция для обработки нажатия на кнопку
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'services':
        # Отправляем сообщение с услугами
        services_message = (
            "Запись: 2000₽ первый час, 2500₽ каждый последующий.\n"
            "Сведение: от 5000₽\n"
            "Мастеринг: от 5000₽\n"
            "Трек под ключ: от 5000₽\n"
            "В нашей студии есть возможность свести и отмастерить все ваши треки на аналоговом оборудовании."
        )
        # Кнопка "Назад"
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text=services_message, reply_markup=reply_markup)
    
    elif query.data == 'book_studio':
        # Проверяем, есть ли уже активная сессия, чтобы избежать повторного сообщения
        if user_messages.get(update.effective_user.id, {}).get("status") != "getting_name":
            # Начинаем процесс записи
            await query.edit_message_text(
                "Чтобы записаться на студию, напишите мне ваше имя."
            )
            user_messages[update.effective_user.id] = {"status": "getting_name"}
        # Кнопка "Назад"
        keyboard = [
            [InlineKeyboardButton("Назад", callback_data='back_to_main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(text="Чтобы записаться на студию, напишите мне ваше имя.", reply_markup=reply_markup)

    elif query.data == 'back_to_main_menu':
        # Возврат в главное меню
        keyboard = [
            [InlineKeyboardButton("Записаться на студию", callback_data='book_studio')],
            [InlineKeyboardButton("Услуги", callback_data='services')],
            [InlineKeyboardButton("ВКонтакте", url="https://vk.com/westnight")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выберите, что вы хотите сделать.",
            reply_markup=reply_markup
        )

# Функция для обработки данных записи
async def handle_booking(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    user_message = update.message.text

    if user_id in user_messages:
        status = user_messages[user_id].get("status")

        if status == "getting_name":
            # Сохраняем имя пользователя
            user_messages[user_id]["name"] = user_message
            user_messages[user_id]["status"] = "getting_date_time"
            await update.message.reply_text("Теперь, укажите желаемую дату и время записи в формате: ДД.ММ.ГГГГ ЧЧ:ММ.")

        elif status == "getting_date_time":
            # Сохраняем дату и время записи
            user_messages[user_id]["date_time"] = user_message
            user_messages[user_id]["status"] = "getting_service"
            await update.message.reply_text("Теперь, укажите тип услуги (Запись, Сведение, Мастеринг и т.д.).")

        elif status == "getting_service":
            # Сохраняем тип услуги
            user_messages[user_id]["service"] = user_message
            name = user_messages[user_id]["name"]
            date_time_str = user_messages[user_id]["date_time"]
            service_type = user_messages[user_id]["service"]

            # Преобразуем дату и время в объект datetime
            try:
                appointment_time = datetime.strptime(date_time_str, "%d.%m.%Y %H:%M")
            except ValueError:
                await update.message.reply_text("Ошибка в формате даты и времени. Пожалуйста, укажите дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ.")
                return

            # Отправляем информацию владельцу
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"Запрос на запись от {update.message.from_user.full_name} (ID: {user_id}):\n"
                     f"Имя: {name}\nДата и время: {appointment_time.strftime('%d.%m.%Y %H:%M')}\nТип услуги: {service_type}"
            )
            await update.message.reply_text("Спасибо за вашу запись! Мы свяжемся с вами для подтверждения.")

            # Запланировать напоминание о записи
            reminder_time = appointment_time - timedelta(days=1)
            context.job_queue.run_once(send_reminder, reminder_time, context=user_id)

            # Сохраняем статус записи
            user_messages[user_id] = {"status": "confirmed", "appointment": appointment_time}

        else:
            await update.message.reply_text("Произошла ошибка. Попробуйте снова.")

# Функция для отправки напоминания
async def send_reminder(context: CallbackContext) -> None:
    user_id = context.job.context
    await context.bot.send_message(user_id, "Напоминаем, что ваша запись на студию состоится завтра.")

# Функция для получения цен на услуги
async def price(update: Update, context: CallbackContext) -> None:
    price_message = (
        "Наши услуги:\n"
        "Запись: 2000₽ первый час, 2500₽ каждый последующий.\n"
        "Сведение: от 5000₽\n"
        "Мастеринг: от 5000₽\n"
        "Трек под ключ: от 5000₽\n"
        "В нашей студии есть возможность свести и отмастерить все ваши треки на аналоговом оборудовании."
    )
    await update.message.reply_text(price_message)

# Функция для оставления отзыва
async def review(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    if user_id in user_messages and user_messages[user_id]["status"] == "confirmed":
        # Запрос отзыва
        await update.message.reply_text("Как вам была оказана услуга? Напишите ваш отзыв.")
        user_messages[user_id] = {"status": "reviewing"}
    else:
        await update.message.reply_text("Отзыв можно оставить только после подтверждения записи.")

# Функция для обработки отзыва
async def handle_review(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    user_message = update.message.text

    if user_id in user_messages and user_messages[user_id]["status"] == "reviewing":
        # Отправляем отзыв владельцу
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=f"Отзыв от {update.message.from_user.full_name}:\n{user_message}"
        )
        await update.message.reply_text("Спасибо за ваш отзыв!")
        user_messages[user_id] = {}  # Сброс статуса после отзыва

# Функция для приветственного сообщения новым пользователям
async def new_user(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    # Отправляем пользователю сообщение с предложением использовать команду /start
    await context.bot.send_message(
        chat_id=user_id,
        text="Привет! Чтобы начать, отправь команду /start."
    )

def main():
    # Создаём приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_booking))
    application.add_handler(CommandHandler("reply", review))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("price", price))
    application.add_handler(CommandHandler("review", review))

    # Добавляем обработчик для новых пользователей
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_user))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
