from telegram.ext import ContextTypes

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document

import logging
from handlers.states import *

from utils.utils import (
    build_menu,
    get_courses_by_teacher,
    save_message,
    delete_messages,
    generate_unique_id,
    split_many_buttons,
    recover_entered_students_data
)

from utils.csv_utils import (
    update_statement
)


async def courses_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning("🤖 Entered courses_management handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "add_new_course":
        buttons = [InlineKeyboardButton(text=f"Отмена", callback_data=f"cancel")]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE в случае, если введено сообщение
        message = await update.callback_query.edit_message_text(
            text=f"🔉 Введите название курса", reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return ADD_COURSE_CODE

    elif callback_data in context.bot_data["courses"].keys():
        course_id = callback_data
        logging.warning(
            f"🤖 Course {context.bot_data['courses'][course_id]['title']} choosen"
        )

        course_data = context.bot_data["courses"][course_id]
        context.chat_data["current_course_id"] = course_id

        buttons = [
            InlineKeyboardButton(text=f"✅ Тесты", callback_data=str(TESTS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🆔 Редактировать код", callback_data=str(EDIT_COURSE_CODE)
            ),
            InlineKeyboardButton(
                text=f"🔈 Редактировать название", callback_data=str(EDIT_COURSE_TITLE)
            ),
            InlineKeyboardButton(
                text=f"🔗 Редактировать ссылку", callback_data=str(EDIT_COURSE_LINK)
            ),
            InlineKeyboardButton(
                text=f"🗑️ Удалить курс", callback_data=str(REMOVE_COURSE_REQUEST)
            ),
            InlineKeyboardButton(text=f"🏠 Домашки", callback_data=str(HWS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🔄 Изменить статус курса", callback_data=str(SWITCH_COURSE_STATUS)
            ),
            InlineKeyboardButton(
                text=f"👥 Студенты", callback_data=str(COURSE_STUDENTS)
            ),
            InlineKeyboardButton(
                text=f"🧐 Ведомость", callback_data="statement"
            ),
            InlineKeyboardButton(
                text=f"🔙 Назад к курсам", callback_data=str(COURSES_MANAGEMENT)
            ),
            InlineKeyboardButton(
                text=f"👨‍🏫 Добавить преподавателя", callback_data=str(ADD_TEACHER_NAME) 
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        text = (
            f"🔈 Название: {course_data['title']}\n"
            f"🆔 Код: {course_data['code']}\n"
            f"🔗 Ссылка: {course_data['link']}\n"
            f"🚼 Студентов: {len(course_data['students'])}\n"
            f"🛎️ Статус: {course_data['status']}\n"
        )

        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MANAGEMENT

    elif callback_data == "all_courses":
        user = update.effective_user

        if "current_course" in context.chat_data.keys():
            context.chat_data.pop("current_course")

        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"
        courses = get_courses_by_teacher(
            bot_data=context.bot_data,
            teacher_id=context.user_data["current_user"]["id"],
        )

        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"+ Добавить новый курс", callback_data="add_new_course"
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSES_MANAGEMENT


async def course_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered course_management handler")
    await update.callback_query.answer()
    action = update.callback_query.data

    if action == str(TESTS_MANAGEMENT):
        current_course_id = context.chat_data["current_course_id"]
        tests = context.bot_data["courses"][current_course_id]["tests"]

        buttons = [
            InlineKeyboardButton(text=f"{test_data['title']}", callback_data=test_id)
            for test_id, test_data in tests.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"➕Добавить новый тест", callback_data="add_new_test"
            )
        )
        buttons.append(
            InlineKeyboardButton(
                text=f"🔙 К меню курса", callback_data=current_course_id
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(
            text=f"✅ Выберите тест.", reply_markup=keyboard
        )
        return TESTS_MANAGEMENT

    elif action == str(EDIT_COURSE_CODE):
        current_course_id = context.chat_data["current_course_id"]
        buttons = [
            InlineKeyboardButton(
                text=f"🔙 К меню курса", callback_data=current_course_id
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE если введено сообщение
        message = await update.callback_query.edit_message_text(
            text=f"🏷️ Введите новый код курса.", reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return EDIT_COURSE_CODE

    elif action == str(EDIT_COURSE_TITLE):
        current_course_id = context.chat_data["current_course_id"]
        buttons = [
            InlineKeyboardButton(
                text=f"🔙 К меню курса", callback_data=current_course_id
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE если введено сообщение
        message = await update.callback_query.edit_message_text(
            text=f"🔉 Введите новое название курса.", reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return EDIT_COURSE_TITLE

    elif action == str(EDIT_COURSE_LINK):
        current_course_id = context.chat_data["current_course_id"]
        buttons = [
            InlineKeyboardButton(
                text=f"🔙 К меню курса", callback_data=current_course_id
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE если введено сообщение
        message = await update.callback_query.edit_message_text(
            text=f"🔗 Введите новую ссылку.", reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return EDIT_COURSE_LINK

    elif action == str(REMOVE_COURSE_REQUEST):
        current_course_id = context.chat_data["current_course_id"]
        current_course_title = context.bot_data["courses"][current_course_id]["title"]
        buttons = [
            InlineKeyboardButton(text=f"👍 Да", callback_data="yes"),
            InlineKeyboardButton(text=f"👎 Нет", callback_data=current_course_id),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(
            text=f"⚠️ Вы действительно хотите удалить курс '{current_course_title}'?\n"
            f"Это действие будет невозможно отменить!\n",
            reply_markup=keyboard,
        )
        return REMOVE_COURSE_REQUEST

    elif action == str(COURSES_MANAGEMENT):
        user = update.callback_query.from_user
        if "current_course" in context.chat_data.keys():
            context.chat_data.pop("current_course")

        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"
        courses = get_courses_by_teacher(bot_data=context.bot_data, teacher_id=user.id)
        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"+ Добавить новый курс", callback_data="add_new_course"
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSES_MANAGEMENT

    elif action == str(HWS_MANAGEMENT):
        current_course_id = context.chat_data["current_course_id"]
        current_course_title = context.bot_data["courses"][current_course_id]["title"]
        hws = context.bot_data["courses"][current_course_id]["HWs"]
        buttons = [
            InlineKeyboardButton(
                text=f"📚 {hw_data['title']}", callback_data=f"hw_{hw_id}"
            )
            for hw_id, hw_data in hws.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"Добавить домашнее задание", callback_data=f"add_hw"
            )
        )
        buttons.append(
            InlineKeyboardButton(text=f"К меню курса", callback_data=f"back_to_course")
        )
        text = f"📖 Курс: {current_course_title}\n"
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return HWS_MANAGEMENT

    elif action == str(SWITCH_COURSE_STATUS):
        current_course_id = context.chat_data["current_course_id"]
        current_course_title = context.bot_data["courses"][current_course_id]["title"]
        current_course_status = context.bot_data["courses"][current_course_id]["status"]
        if current_course_status == "opened":
            context.bot_data["courses"][current_course_id]["status"] = "closed"
        else:
            context.bot_data["courses"][current_course_id]["status"] = "opened"

        current_course_status = context.bot_data["courses"][current_course_id]["status"]

        text = (
            f"Статус курса {current_course_title} изменён"
            f" на {current_course_status}."
        )
        buttons = [
            InlineKeyboardButton(text=f"🫡 Ладно.", callback_data=current_course_id)
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        return COURSES_MANAGEMENT

    elif action == str(COURSE_STUDENTS):
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        students = course_data["students"]
        buttons = [
            InlineKeyboardButton(
                text=f"{student['name']}",
                callback_data=f"student_{student['id']}"
            ) for student in students
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        )
        base_text = f"🔉 Курс: {course_data['title']}"
        splitted_buttons = split_many_buttons(
            buttons=buttons
        )
        
        for i in range(len(splitted_buttons)):
            text = base_text + f" {i+1}/{len(splitted_buttons)}\n"
            keyboard = InlineKeyboardMarkup(build_menu(splitted_buttons[i], n_cols=1))
            message = None
            if i == 0:
                message = await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
            else:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=keyboard
                )
            
            assert message is not None

            if "paginated_std_btns" not in context.chat_data.keys():
                context.chat_data["paginated_std_btns"] = \
                    [message.message_id]
            else:
                context.chat_data["paginated_std_btns"].append(message.message_id)
        return COURSE_STUDENTS

    elif action == "statement":
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        await update_statement(update, context)
    
    elif action == str(ADD_TEACHER_NAME):
        course_id = context.chat_data["current_course_id"]
        text = f"⌨️ Введите имя преподавателя:\n"
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data=course_id
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        
        message = await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_NAME


async def add_teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_teacher_name handler")
    
    if update.message.text:
        context.chat_data["teacher_name_to_add"] = update.message.text
        course_id = context.chat_data["current_course_id"]
        text = f"⌨️ Введите username преподавателя:\n"
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data=course_id
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )

        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )

        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_USERNAME

    elif update.message:
        text = f"❌ Имя преподавателя должно быть текстом."\
                f" Пожалуйста, отправьте текстовое сообщение с именем преподавателя:"
        course_id = context.chat_data["current_course_id"]
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data=course_id
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        
        message = await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_NAME


async def add_teacher_username_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Sent message with teacher's username """
    logging.warning(f"🤖 Entered add_teacher_username_msg handler")

    if update.message.text:
        context.chat_data["teacher_username_to_add"] = update.message.text
        text = f"⌨️ Введите ID преподавателя:\n"
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data="cancel"
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )

        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )

        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_ID
    elif update.message:
        text = f"❌ Username преподавателя должно быть текстом."\
                f" Пожалуйста, отправьте текстовое сообщение с username преподавателя:"
        course_id = context.chat_data["current_course_id"]
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data=course_id
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        
        message = await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_USERNAME


async def add_teacher_username_bttn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Cancel button pushed """
    logging.warning(f"🤖 Entered add_teacher_username_bttn handler")
    course_id = context.chat_data["current_course_id"]
    text = f"⌨️ Введите имя преподавателя:\n"
    buttons = [InlineKeyboardButton(
        text=f"↩️ Назад", callback_data=course_id
    )]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

    await delete_messages(
        context=context,
        chat_id=update.effective_chat.id
    )

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=keyboard
    )

    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id
    )
    return ADD_TEACHER_NAME


async def add_teacher_id_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_teacher_id_msg handler")
    if update.message.text:
        if not update.message.text.isdigit():
            text = f"❌ ID пользователя может содержать только цифры. "\
                    f"Пожалуйста, введите корректный ID преподавателя:\n"
            buttons = [InlineKeyboardButton(
                text=f"↩️ Назад", callback_data="cancel"
            )]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

            await delete_messages(
                context=context,
                chat_id=update.effective_chat.id
            )

            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=keyboard
            )

            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id
            )
            return ADD_TEACHER_ID
        
        context.chat_data["teacher_id_to_add"] = int(update.message.text)
        text = f"👨‍🏫 Новый преподаватель:\n"\
                f"📇 Имя: {context.chat_data['teacher_name_to_add']}\n"\
                f"🪪 Username: {context.chat_data['teacher_username_to_add']}\n"\
                f"🆔 ID: {context.chat_data['teacher_id_to_add']}\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✅ Добавить",
                callback_data="add"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад", 
                callback_data="cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )

        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )

        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER

    elif update.message:
        text = f"❌ Username преподавателя должно быть строкой, состоящей из цифр."\
                f" Пожалуйста, отправьте текстовое сообщение с username преподавателя:"
        course_id = context.chat_data["current_course_id"]
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data=course_id
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        
        message = await update.callback_query.edit_message_text(
            text=text,
            reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_USERNAME


async def add_teacher_id_bttn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_teacher_id_bttn handler")
    course_id = context.chat_data["current_course_id"]
    text = f"⌨️ Введите username преподавателя:\n"
    buttons = [InlineKeyboardButton(
        text=f"↩️ Назад", callback_data=course_id
    )]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

    await delete_messages(
        context=context,
        chat_id=update.effective_chat.id
    )

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=keyboard
    )

    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id
    )
    return ADD_TEACHER_USERNAME


async def add_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_teacher handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "add":
        name = context.chat_data.pop("teacher_name_to_add", None)
        username = context.chat_data.pop("teacher_username_to_add", None)
        teacher_id = context.chat_data.pop("teacher_id_to_add", None)

        course_id = context.chat_data["current_course_id"]
        context.bot_data["courses"][course_id]["teachers"].append({
            "name": name,
            "username": username,
            "id": teacher_id
        })
        course_data = context.bot_data["courses"][course_id]
        context.chat_data["current_course_id"] = course_id

        buttons = [
            InlineKeyboardButton(text=f"✅ Тесты", callback_data=str(TESTS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🆔 Редактировать код", callback_data=str(EDIT_COURSE_CODE)
            ),
            InlineKeyboardButton(
                text=f"🔈 Редактировать название", callback_data=str(EDIT_COURSE_TITLE)
            ),
            InlineKeyboardButton(
                text=f"🔗 Редактировать ссылку", callback_data=str(EDIT_COURSE_LINK)
            ),
            InlineKeyboardButton(
                text=f"🗑️ Удалить курс", callback_data=str(REMOVE_COURSE_REQUEST)
            ),
            InlineKeyboardButton(text=f"🏠 Домашки", callback_data=str(HWS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🔄 Изменить статус курса", callback_data=str(SWITCH_COURSE_STATUS)
            ),
            InlineKeyboardButton(
                text=f"👥 Студенты", callback_data=str(COURSE_STUDENTS)
            ),
            InlineKeyboardButton(
                text=f"🧐 Ведомость", callback_data="statement"
            ),
            InlineKeyboardButton(
                text=f"🔙 Назад к курсам", callback_data=str(COURSES_MANAGEMENT)
            ),
            InlineKeyboardButton(
                text=f"👨‍🏫 Добавить преподавателя", callback_data=str(ADD_TEACHER_NAME) 
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        text = (
            f"🔈 Название: {course_data['title']}\n"
            f"🆔 Код: {course_data['code']}\n"
            f"🔗 Ссылка: {course_data['link']}\n"
            f"🚼 Студентов: {len(course_data['students'])}\n"
            f"🛎️ Статус: {course_data['status']}\n"
        )

        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MANAGEMENT

    elif callback_data == "cancel":
        text = f"⌨️ Введите ID преподавателя:\n"
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад", callback_data="cancel"
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )

        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )

        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return ADD_TEACHER_ID


async def course_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered course_students handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if "paginated_std_btns" in context.chat_data.keys():
        deleted_ids = []
        for msg_id in context.chat_data["paginated_std_btns"]:
            deleted = False
            try:
                deleted = await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=msg_id
                )
            except:
                pass
            if deleted:
                deleted_ids.append(msg_id)
        for msg_id in deleted_ids:
            context.chat_data["paginated_std_btns"].remove(msg_id)


    await delete_messages(
        context=context,
        chat_id=update.effective_chat.id
    )

    if callback_data == "cancel":
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]

        buttons = [
            InlineKeyboardButton(text=f"✅ Тесты", callback_data=str(TESTS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🆔 Редактировать код", callback_data=str(EDIT_COURSE_CODE)
            ),
            InlineKeyboardButton(
                text=f"🔈 Редактировать название", callback_data=str(EDIT_COURSE_TITLE)
            ),
            InlineKeyboardButton(
                text=f"🔗 Редактировать ссылку", callback_data=str(EDIT_COURSE_LINK)
            ),
            InlineKeyboardButton(
                text=f"🗑️ Удалить курс", callback_data=str(REMOVE_COURSE_REQUEST)
            ),
            InlineKeyboardButton(text=f"🏠 Домашки", callback_data=str(HWS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🔄 Изменить статус курса", callback_data=str(SWITCH_COURSE_STATUS)
            ),
            InlineKeyboardButton(
                text=f"🔙 Назад к курсам", callback_data=str(COURSES_MANAGEMENT)
            ),
            InlineKeyboardButton(
                text=f"👥 Студенты", callback_data=str(COURSE_STUDENTS)
            ),
            InlineKeyboardButton(
                text=f"🧐 Ведомость", callback_data="statement"
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        text = (
            f"🔈 Название: {course_data['title']}\n"
            f"🆔 Код: {course_data['code']}\n"
            f"🔗 Ссылка: {course_data['link']}\n"
            f"🚼 Студентов: {len(course_data['students'])}\n"
            f"🛎️ Статус: {course_data['status']}\n"
        )
        #await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )
        return COURSE_MANAGEMENT

    elif callback_data.startswith("student_"):
        student_id = int(callback_data[len("student_"):])
        course_id = context.chat_data["current_course_id"]
        students = context.bot_data["courses"][course_id]["students"]
        student_data = {}
        for student in students:
            if student["id"] == student_id:
                student_data = student
                break
        
        text = f"🔉 Курс: {context.bot_data['courses'][course_id]['title']}\n"\
                f"🧑🏻‍🎓 Студент: {student_data['name']}\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✍🏻 Изменить имя",
                callback_data=f"edit_name_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"☠️ Забанить",
                callback_data=f"kill_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        #await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )
        return COURSE_STUDENT

async def course_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered course_student handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if "edit_name_msg_ids" in context.chat_data.keys():
        _ = context.chat_data.pop("edit_name_msg_ids")

    course_id = context.chat_data["current_course_id"]

    if callback_data.startswith("edit_name_"):
        student_id = int(callback_data[len("edit_name_"):])
        student_name = \
            next((student["name"] for student in context.bot_data["courses"][course_id]["students"]\
                  if student["id"] == student_id), None)
        assert student_name is not None

        text = f"🧑🏻‍🎓 Студент: {student_name}\n"\
                f"💬 Введите новое имя: \n"
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]

        context.chat_data["edit_name_student_id"] = student_id

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        if "edit_name_msg_ids" not in context.chat_data.keys():
            context.chat_data["edit_name_msg_ids"] = [message.message_id]
        else:
            context.chat_data["edit_name_msg_ids"].append(message.message_id)

        return EDIT_STUDENT_NAME

    elif callback_data.startswith("kill_"):
        student_id = int(callback_data[len("kill_"):])
        student_name = \
            next((student["name"] for student in context.bot_data["courses"][course_id]["students"]\
                  if student["id"] == student_id), None)
        text = f"🧑🏻‍🎓 Студент: {student_name}\n"\
                f"❓ Подтвердите удаление:\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✅ Подтверждаю",
                callback_data=f"yes_kill_him_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"❌ Нет",
                callback_data=f"no_{student_id}"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return KICK_STUDENT

    elif callback_data == "cancel":
        course_data = context.bot_data["courses"][course_id]
        students = course_data["students"]
        buttons = [
            InlineKeyboardButton(
                text=f"{student['name']}",
                callback_data=f"student_{student['id']}"
            ) for student in students
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        )
        base_text = f"🔉 Курс: {course_data['title']}"
        splitted_buttons = split_many_buttons(
            buttons=buttons
        )
        
        for i in range(len(splitted_buttons)):
            text = base_text + f" {i+1}/{len(splitted_buttons)}\n"
            keyboard = InlineKeyboardMarkup(build_menu(splitted_buttons[i], n_cols=1))
            message = None
            if i == 0:
                message = await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
            else:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=text,
                    reply_markup=keyboard
                )
            
            assert message is not None
            
            if "paginated_std_btns" not in context.chat_data.keys():
                context.chat_data["paginated_std_btns"] = \
                    [message.message_id]
            else:
                context.chat_data["paginated_std_btns"].append(message.message_id)
        
        return COURSE_STUDENTS


async def kick_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered kick_student handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("yes_kill_him_"):
        student_id = int(callback_data[len("yes_kill_him_"):])
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        students = course_data["students"]
        ind = -1
        for i in range(len(students)):
            if students[i]["id"] == student_id:
                ind = i
                break
        assert ind >= 0

        # del from students
        del context.bot_data["courses"][course_id]["students"][ind]

        # del from tests if exists
        for test_id in course_data["tests"].keys():
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if student_id in test_data["answers"].keys():
                del context.bot_data["courses"][course_id]["tests"][test_id]["answers"][student_id]
            
            if student_id in test_data["scores"].keys():
                del context.bot_data["courses"][course_id]["tests"][test_id]["scores"][student_id]

            if "entered_students" not in test_data.keys():
                context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"] = \
                    recover_entered_students_data(
                        test_data=test_data,
                        course_students=course_data["students"]
                    )
            entered_students = test_data["entered_students"]
            ind2 = -1
            for j in range(len(entered_students)):
                if entered_students[j]["id"] == student_id:
                    ind2 = j
                    break
            if ind2 >= 0:
                del context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"][ind2]

        # del from HWs
        for hw_id, hw_data in course_data["HWs"].items():

            if "students" in hw_data.keys() \
                and student_id in hw_data["students"].keys():
                del context.bot_data["courses"][course_id]["HWs"][hw_id]["students"][student_id]
            
            if "scores" in hw_data.keys() \
                and student_id in hw_data["scores"].keys():
                del context.bot_data["courses"][course_id]["HWs"][hw_id]["scores"][student_id]

        course_data = context.bot_data["courses"][course_id]
        students = course_data["students"]
        buttons = [
            InlineKeyboardButton(
                text=f"{student['name']}",
                callback_data=f"student_{student['id']}"
            ) for student in students
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        )
        text = f"🔉 Курс: {course_data['title']}"
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        return COURSE_STUDENTS

    elif callback_data.startswith("no_"):
        student_id = int(callback_data[len("no_"):])
        course_id = context.chat_data["current_course_id"]
        students = context.bot_data["courses"][course_id]["students"]
        student_data = {}
        for student in students:
            if student["id"] == student_id:
                student_data = student
                break
        
        text = f"🔉 Курс: {context.bot_data['courses'][course_id]['title']}\n"\
                f"🧑🏻‍🎓 Студент: {student_data['name']}\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✍🏻 Изменить имя",
                callback_data=f"edit_name_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"☠️ Забанить",
                callback_data=f"kill_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_STUDENT


async def edit_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_student_name handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        new_name = update.message.text

    if callback_data == "...":
        # entered new student's name
        student_id = context.chat_data["edit_name_student_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        student_data =\
            next((student for student in course_data["students"] \
                  if student["id"] == student_id), None)
        assert student_data is not None

        context.chat_data[f"new_name_{student_id}"] = new_name

        text = f"❌ Старое имя: {student_data['name']}\n"\
                f"⚠️ Новое имя: {new_name}\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✅ Сохранить",
                callback_data=f"save"
            ),
            InlineKeyboardButton(
                text=f"⛔️ Отмена",
                callback_data="cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # delete message
        if "edit_name_msg_ids" in context.chat_data.keys():
            for msg_id in context.chat_data["edit_name_msg_ids"]:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=msg_id
                    )
                except:
                    pass
            _ = context.chat_data.pop("edit_name_msg_ids")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )
        return SAVE_STUDENT_NAME
    else:
        # Отмена
        student_id = context.chat_data.pop("edit_name_student_id")
        course_id = context.chat_data["current_course_id"]
        students = context.bot_data["courses"][course_id]["students"]
        student_data = {}
        for student in students:
            if student["id"] == student_id:
                student_data = student
                break
        
        text = f"🔉 Курс: {context.bot_data['courses'][course_id]['title']}\n"\
                f"🧑🏻‍🎓 Студент: {student_data['name']}\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✍🏻 Изменить имя",
                callback_data=f"edit_name_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"☠️ Забанить",
                callback_data=f"kill_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_STUDENT
    

async def save_student_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered save_student_name handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "save":
        student_id = context.chat_data.pop("edit_name_student_id")
        new_name = context.chat_data.pop(f"new_name_{student_id}")
        course_id = context.chat_data["current_course_id"]
        students = context.bot_data["courses"][course_id]["students"]
        ind = -1
        for i in range(len(students)):
            if students[i]["id"] == student_id:
                ind = i
                break
        assert ind >= 0
        context.bot_data["courses"][course_id]["students"][ind]["name"] = new_name

        student_data = {}
        for student in students:
            if student["id"] == student_id:
                student_data = student
                break
        text = f"🔉 Курс: {context.bot_data['courses'][course_id]['title']}\n"\
                f"🧑🏻‍🎓 Студент: {student_data['name']}\n"
        buttons = [
            InlineKeyboardButton(
                text=f"✍🏻 Изменить имя",
                callback_data=f"edit_name_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"☠️ Забанить",
                callback_data=f"kill_{student_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data="cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_STUDENT
    
    elif callback_data == "cancel":
        student_id = context.chat_data["edit_name_student_id"]
        course_id = context.chat_data["current_course_id"]

        if f"new_name_{student_id}" in context.chat_data.keys():
            _ = context.chat_data.pop(f"new_name_{student_id}")

        student_name = \
            next((student["name"] for student in context.bot_data["courses"][course_id]["students"]\
                  if student["id"] == student_id), None)
        assert student_name is not None

        text = f"🧑🏻‍🎓 Студент: {student_name}\n"\
                f"💬 Введите новое имя: \n"
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        if "edit_name_msg_ids" not in context.chat_data.keys():
            context.chat_data["edit_name_msg_ids"] = [message.message_id]
        else:
            context.chat_data["edit_name_msg_ids"].append(message.message_id)

        return EDIT_STUDENT_NAME
        

async def remove_course_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered remove_course_request handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "yes":
        # Remove course
        course_id_to_remove = context.chat_data["current_course_id"]
        course_title_to_remove = context.bot_data["courses"][course_id_to_remove][
            "title"
        ]
        context.chat_data.pop("current_course_id")
        context.bot_data["courses"].pop(course_id_to_remove)

        text = f"✅ Курс '{course_title_to_remove}' успешно удален."
        buttons = [
            InlineKeyboardButton(
                text=f"🔙 Назад к курсам", callback_data=f"back_to_courses"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return REMOVE_COURSE

    else:
        # No
        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        text = (
            f"🔈 Название: {current_course_data['title']}\n"
            f"🆔 Код: {current_course_data['code']}\n"
            f"🔗 Ссылка: {current_course_data['link']}\n"
            f"🚼 Студентов: {len(current_course_data['students'])}\n"
            f"🛎️ Статус: {current_course_data['status']}\n"
        )

        buttons = [
            InlineKeyboardButton(text=f"✅ Тесты", callback_data=str(TESTS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🆔 Редактировать код", callback_data=str(EDIT_COURSE_CODE)
            ),
            InlineKeyboardButton(
                text=f"🔈 Редактировать название", callback_data=str(EDIT_COURSE_TITLE)
            ),
            InlineKeyboardButton(
                text=f"🔗 Редактировать ссылку", callback_data=str(EDIT_COURSE_LINK)
            ),
            InlineKeyboardButton(
                text=f"🗑️ Удалить курс", callback_data=str(REMOVE_COURSE_REQUEST)
            ),
            InlineKeyboardButton(text=f"🏠 Домашки", callback_data=str(HWS_MANAGEMENT)),
            InlineKeyboardButton(
                text=f"🔄 Изменить статус курса", callback_data=str(SWITCH_COURSE_STATUS)
            ),
            InlineKeyboardButton(
                text=f"🔙 Назад к курсам", callback_data=str(COURSES_MANAGEMENT)
            ),
            InlineKeyboardButton(
                text=f"👥 Студенты", callback_data=str(COURSE_STUDENTS)
            ),
            InlineKeyboardButton(
                text=f"🧐 Ведомость", callback_data="statement"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MANAGEMENT


async def remove_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered remove_course handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "back_to_courses":
        user = update.effective_user
        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"

        if "current_course_id" in context.chat_data.keys():
            context.chat_data.pop("current_course_id")
        courses = get_courses_by_teacher(bot_data=context.bot_data, teacher_id=user.id)
        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"+ Добавить новый курс", callback_data="add_new_course"
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSES_MANAGEMENT


async def edit_course_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_course_code handler")
    new_course_code = update.message.text
    current_course_id = context.chat_data["current_course_id"]

    # ===========deleting is here============#
    await delete_messages(context=context, chat_id=update.effective_chat.id)

    # check code uniqueness
    for course_id, course_data in context.bot_data["courses"].items():
        if new_course_code == course_data["code"]:
            if course_id == current_course_id:
                text = f"🔂 Код текущего курса совпадает с введенным кодом. Введите, пожалуйста, другой код."
            else:
                text = f"🔄 Курс с таким кодом уже существует. Введите, пожалуйста, другой код:"
            buttons = [
                InlineKeyboardButton(
                    text=f"🔙 К меню курса", callback_data=current_course_id
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            # DELETE если введено сообщение
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return EDIT_COURSE_CODE

    # update code
    context.bot_data["courses"][current_course_id]["code"] = new_course_code

    buttons = [
        InlineKeyboardButton(text=f"🔙 К меню курса", callback_data=current_course_id)
    ]
    text = f"👍 Код курса изменен на {new_course_code}"
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

    await update.message.reply_text(text=text, reply_markup=keyboard)
    return COURSES_MANAGEMENT


async def edit_course_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_course_title handler")
    new_course_title = update.message.text
    course_id = context.chat_data["current_course_id"]

    context.bot_data["courses"][course_id]["title"] = new_course_title

    buttons = [InlineKeyboardButton(text=f"🔙 К меню курса", callback_data=course_id)]
    text = f"👍 Название курса изменено на {new_course_title}"
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    await update.message.reply_text(text=text, reply_markup=keyboard)
    return COURSES_MANAGEMENT


async def edit_course_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_course_title handler")
    new_course_link = update.message.text
    course_id = context.chat_data["current_course_id"]

    # update link
    context.bot_data["courses"][course_id]["link"] = new_course_link

    buttons = [InlineKeyboardButton(text=f"🔙 К меню курса", callback_data=course_id)]
    text = f"👍 Ссылка изменена на {new_course_link}"
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    await update.message.reply_text(text=text, reply_markup=keyboard)

    return COURSES_MANAGEMENT


async def add_course_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_course_code handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        new_title = update.message.text

    if callback_data == "cancel":
        user = update.effective_user
        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"
        courses = get_courses_by_teacher(bot_data=context.bot_data, teacher_id=user.id)
        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"+ Добавить курс", callback_data="add_new_course"
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSES_MANAGEMENT

    context.chat_data["new_course_title"] = new_title
    text = f"🆔 Введите код курса:"
    buttons = [InlineKeyboardButton(text=f"↩️ Отмена", callback_data=f"cancel")]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    # DELETE если введено сообщение
    message = await update.message.reply_text(text=text, reply_markup=keyboard)
    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
    )
    return ADD_COURSE_LINK


async def add_course_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_course_link handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        new_code = update.message.text

    if callback_data == "cancel":
        user = update.effective_user
        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"
        courses = get_courses_by_teacher(bot_data=context.bot_data, teacher_id=user.id)

        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"+ Добавить курс", callback_data="add_new_course"
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        return COURSES_MANAGEMENT

    await delete_messages(context=context, chat_id=update.effective_chat.id)
    # check code uniqness
    for course_code in context.bot_data["courses"].keys():
        if course_code == new_code:
            text = f"🛑 Курс с кодом '{new_code}' уже существует. Выберите другой код"
            courses = get_courses_by_teacher(
                bot_data=context.bot_data, teacher_id=user.id
            )
            buttons = [
                InlineKeyboardButton(
                    text=f"{course_data['title']}", callback_data=course_id
                )
                for course_id, course_data in courses.items()
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            # DELETE если введено сообщение
            message = await update.callback_query.edit_message_text(
                text=f"🆔 Введите новый код курса.", reply_markup=keyboard
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return ADD_COURSE_CODE

    context.chat_data["new_course_code"] = new_code
    text = f"🔗 Введите ссылку:"
    buttons = [InlineKeyboardButton(text=f"↩️ Отмена", callback_data=f"cancel")]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    # DELETE если введено сообщение
    message = await update.message.reply_text(text=text, reply_markup=keyboard)
    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
    )
    return ADD_COURSE


async def add_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_course handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        new_link = update.message.text

    if callback_data == "cancel":
        user = update.effective_user
        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"
        courses = get_courses_by_teacher(bot_data=context.bot_data, teacher_id=user.id)
        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"+ Добавить курс", callback_data="add_new_course"
            )
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSES_MANAGEMENT

    new_course_id = generate_unique_id(existing_ids=context.bot_data["courses"].keys())
    title = context.chat_data.pop("new_course_title")
    link = new_link
    code = context.chat_data.pop("new_course_code")
    new_course = {
        "teachers": [context.user_data["current_user"]],
        "title": title,
        "link": link,
        "status": "opened",
        "code": code,
        "students": [],
        "tests": {},
        "HWs": {},
    }

    context.bot_data["courses"][new_course_id] = new_course

    text = f"✅ Курс '{title}' успешно создан."
    buttons = [
        InlineKeyboardButton(text=f"↩️ Назад к курсам", callback_data="all_courses")
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    await update.message.reply_text(text=text, reply_markup=keyboard)
    return COURSES_MANAGEMENT
