from telegram.ext import (
    ContextTypes,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from utils.utils import *
from handlers.states import *

import logging
import random
from datetime import datetime, timedelta
import pytz

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered student_menu handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data
    
    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "join_course":
        text = f"🆔 Введите код курса:"
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена", callback_data="back_to_student_menu"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return JOIN_COURSE_REQUEST

    elif callback_data in context.bot_data["courses"].keys():
        course_id = callback_data
        course_data = context.bot_data["courses"][course_id]

        context.chat_data["current_course_id"] = course_id
        context.user_data["current_course_id"] = course_id

        text = f"📚 Курс: {course_data['title']}\n" f"🔗 Ссылка: {course_data['link']}\n"
        buttons = [
            InlineKeyboardButton(text=f"📃 Тесты", callback_data=f"tests"),
            InlineKeyboardButton(text=f"📤 Сдать ДЗ", callback_data=f"submit_hw"),
            InlineKeyboardButton(
                text=f"↩️ Назад к курсам", callback_data=f"back_to_courses"
            ),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MENU


async def join_course_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered join_course_request handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        entered_course_code = update.message.text

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "...":
        # entered course code
        course_to_join_id = None
        for course_id, course_data in context.bot_data["courses"].items():
            if course_data["code"] == entered_course_code:
                course_to_join_id = course_id
                break

        if course_to_join_id is None:
            # course not found
            text = f"⛔️ Курса с кодом '{entered_course_code}' не существует. Попробуйте ещё раз."
            buttons = [
                InlineKeyboardButton(text=f"↪️ Ещё раз", callback_data=f"try_again")
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await delete_messages(
                context=context,
                chat_id=update.effective_chat.id
            )
            message = await update.message.reply_text(
                text=text, reply_markup=keyboard)
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id
            )
            return UNKNOWN_COURSE_TAG
        else:
            await delete_messages(
                context=context,
                chat_id=update.effective_chat.id
            )
            course_data = context.bot_data["courses"][course_to_join_id]
            if course_data["status"] == "opened":
                student = context.user_data["current_user"]
                if student in course_data["students"]:
                    # already joined
                    text = f"☺️ Вы уже присоединились к этому курсу!"
                    buttons = [
                        InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"cancel")
                    ]
                    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                    await update.message.reply_text(text, reply_markup=keyboard)
                    return ALREADY_JOINED
                else:
                    context.bot_data["courses"][course_to_join_id]["students"].append(
                        student
                    )
                    text = f"✅ Вы присоединились к курсу '{course_data['title']}'"
                    buttons = [
                        InlineKeyboardButton(
                            text=f"↩️ Мои курсы", callback_data=f"to_my_courses"
                        )
                    ]
                    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                    message = await update.message.reply_text(text, reply_markup=keyboard)
                    save_message(
                        bot_data=context.bot_data,
                        chat_id=update.effective_chat.id,
                        message_id=message.message_id
                    )
                    return JOINED_COURSE
            else:
                # нельзя присоединиться
                text = f"🛠️ Курс '{course_data['title']}' сейчас недоступен."
                buttons = [
                    InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"cancel")
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                message = await update.message.reply_text(text, reply_markup=keyboard)
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id
                )
                return UNAVAILABLE_COURSE

    elif callback_data == "back_to_student_menu":
        # back to student menu
        user = update.effective_user
        student_courses = get_courses_by_student(
            bot_data=context.bot_data, student_id=user.id
        )
        if len(student_courses.keys()) == 0:
            # new student
            text = f"🤖 Добро пожаловать, {user.first_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"🙇🏼 Присоединиться к курсу", callback_data="join_course"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
        else:
            key = list(student_courses.keys())[0]
            student_name = get_student_name_by_id(
                students=student_courses[key]["students"],
                id=user.id
            )
            text = f"Привет, {student_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"{course_data['title']}", callback_data=f"{course_id}"
                )
                for course_id, course_data in student_courses.items()
            ]
            buttons.append(
                InlineKeyboardButton(
                    text=f"🙇🏼 Присоединиться к курсу", callback_data=f"join_course"
                )
            )
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )

        return STUDENT_MENU


async def unknown_course_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered unknown_course_tag handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "try_again":
        text = f"🆔 Введите код курса:"
        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад", callback_data="back_to_student_menu")
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return JOIN_COURSE_REQUEST


async def already_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered already_joined handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "cancel":
        text = f"🆔 Введите код курса:"
        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад", callback_data="back_to_student_menu")
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return JOIN_COURSE_REQUEST


async def unavailable_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered unavailable_course handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "cancel":
        text = f"🆔 Введите код курса:"
        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад", callback_data="back_to_student_menu")
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return JOIN_COURSE_REQUEST


async def joined_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered joined_course handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "to_my_courses":
        user = update.effective_user
        student_courses = get_courses_by_student(
            bot_data=context.bot_data, student_id=user.id
        )
        if len(student_courses) == 0:
            # new student
            text = f"🤖 Добро пожаловать, {user.first_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"🙇🏼 Присоединиться к курсу", callback_data="join_course"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await update.message.reply_text(text=text, reply_markup=keyboard)
        else:
            key = list(student_courses.keys())[0]
            student_name = get_student_name_by_id(
                students=student_courses[key]["students"],
                id=user.id
            )
            text = f"Привет, {student_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"{course_data['title']}", callback_data=f"{course_id}"
                )
                for course_id, course_data in student_courses.items()
            ]
            buttons.append(
                InlineKeyboardButton(
                    text=f"🙇🏼 Присоединиться к курсу", callback_data=f"join_course"
                )
            )
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
        return STUDENT_MENU


async def course_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered course_menu handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data == "tests":
        course_id = context.chat_data["current_course_id"]
        student_id = context.user_data["current_user"]["id"]
        tests_to_display = {}
        for test_id in context.bot_data["courses"][course_id][
            "tests"
        ].keys():
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if "entered_students" not in test_data.keys():
                context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"] = \
                    recover_entered_students_data(
                        test_data=test_data,
                        course_students=context.bot_data["courses"][course_id]["students"]
                    )
                test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if (
                test_data["status"] == "active"
                or test_data["status"] == "past"
                and (
                    student_id in test_data["answers"].keys()
                    or student_id in [st["id"] for st in test_data["entered_students"]]
                )
            ):
                tests_to_display[test_id] = test_data

        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Назад", callback_data=f"back_to_course_{course_id}"
            )
        ]
        if len(tests_to_display.keys()) > 0:
            buttons += [
                InlineKeyboardButton(
                    text=f"{test_data['title']}", callback_data=f"{test_id}"
                )
                for test_id, test_data in tests_to_display.items()
            ]
            text = f"✅ Тесты:"
        else:
            text = f"❌У вас нет активных или завершенных тестов."

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        context.chat_data["tests_del_msg_id"] = message.message_id
        return TESTS_MENU
    elif callback_data == "submit_hw":
        course_id = context.chat_data["current_course_id"]
        hws = context.bot_data["courses"][course_id]["HWs"]
        moscow_tz = pytz.timezone("Europe/Moscow")
        buttons = [
            InlineKeyboardButton(
                text=f"🏠 {hw_data['title']}", callback_data=f"hw_{hw_id}"
            )
            for hw_id, hw_data in hws.items()
        ]
        buttons.append(
            InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"back_to_course")
        )
        text = f"🚨 Доступны домашние задания:"
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return SUBMIT_HW_REQUEST

    elif callback_data == "back_to_courses":
        user = update.effective_user
        student_courses = get_courses_by_student(
            bot_data=context.bot_data, student_id=user.id
        )
        if len(student_courses.keys()) == 0:
            # new student
            text = f"🤖 Добро пожаловать, {user.first_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"🙇🏼 Присоединиться к курсу", callback_data="join_course"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
        else:
            key = list(student_courses.keys())[0]
            student_name = get_student_name_by_id(
                students=student_courses[key]["students"],
                id=user.id
            )
            text = f"Привет, {student_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"{course_data['title']}", callback_data=f"{course_id}"
                )
                for course_id, course_data in student_courses.items()
            ]
            buttons.append(
                InlineKeyboardButton(
                    text=f"🙇🏼 Присоединиться к курсу", callback_data=f"join_course"
                )
            )
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )

        return STUDENT_MENU


async def submit_hw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered submit_hw_request handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    if callback_data.startswith("hw_"):
        hw_id = callback_data[len("hw_") :]
        context.chat_data["current_hw_id"] = hw_id
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        if "comments" not in hw_data.keys():
            context.bot_data["courses"][course_id]["HWs"][hw_id]["comments"] = {}
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        deadline_str = str(course_data["HWs"][hw_id]['deadline']).split('+')[0]

        student_id = context.user_data["current_user"]["id"]

        text = f"🏠 ДЗ: {hw_data['title']}\n"\
                f"🕰️ Дедлайн: {deadline_str}\n"
        
        already_sent = student_id in hw_data["students"].keys()

        commented = student_id in hw_data["comments"].keys()
        scored = student_id in hw_data["scores"].keys()

        if scored:
            text += f"💯 Оценка: {hw_data['scores'][student_id]}\n"
        
        buttons = []
        
        if commented:
            buttons.append(
                InlineKeyboardButton(
                    text=f"💬 Комментарий",
                    callback_data=f"comment_{hw_id}"
                )
            )
        
        moscow_tz = pytz.timezone("Europe/Moscow")
        if hw_data["deadline"] >= datetime.now(moscow_tz):
            buttons.append(
                InlineKeyboardButton(
                    text=f"📤 Загрузить ДЗ",
                    callback_data=f"upload_{hw_id}"
                )
            )
        
        buttons.append(
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"cancel_{hw_id}"
            )
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return HW_MENU

    elif callback_data == "back_to_course":
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        text = f"Курс: {course_data['title']}\n" f"Ссылка: {course_data['link']}\n"
        buttons = [
            InlineKeyboardButton(text=f"📃 Тесты", callback_data=f"tests"),
            InlineKeyboardButton(text=f"📤 Сдать ДЗ", callback_data=f"submit_hw"),
            InlineKeyboardButton(
                text=f"↩️ Назад к курсам", callback_data=f"back_to_courses"
            ),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MENU


async def hw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered hw_menu handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    course_id = context.chat_data["current_course_id"]
    course_data = context.bot_data["courses"][course_id]
    student_id = context.user_data["current_user"]["id"]

    if callback_data.startswith("comment_"):
        hw_id = callback_data[len("comment_"):]
        hw_data = course_data["HWs"][hw_id]

        text = f"🏠 ДЗ: {hw_data['title']}\n"

        scored = student_id in hw_data["scores"].keys()
        if scored:
            text += f"💯 Оценка: {hw_data['scores'][student_id]}\n"
        
        comment_data = hw_data["comments"][student_id]

        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад",
            callback_data=f"cancel"
        )]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        if int(comment_data['is_doc']) == 1:
            text += "💬 Комментарий: в файле\n"
            file_id = comment_data['comment']
            await delete_messages(
                context=context,
                chat_id=update.effective_chat.id
            )
            message = await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_id,
                caption=text,
                reply_markup=keyboard
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id
            )
            return HW_COMMENT
        elif int(comment_data['is_photo']) == 1:
            text += "💬 Комментарий: на фото\n"
            file_id = comment_data['comment']
            await delete_messages(
                context=context,
                chat_id=update.effective_chat.id
            )
            message = await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=file_id,
                caption=text,
                reply_markup=keyboard
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id
            )
            return HW_COMMENT
        else:
            text += f"💬 Комментарий: {comment_data['comment']}\n"
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
            return HW_COMMENT

    elif callback_data.startswith("upload_"):
        hw_id = callback_data[len("upload_"):]
        hw_data = course_data["HWs"][hw_id]

        text = f"🏠 ДЗ: {hw_data['title']}\n"\
                f"📄 Загрузите файл с домашним заданием\n"
        
        buttons = [InlineKeyboardButton(
            text=f"↩️ Назад",
            callback_data=f"cancel"
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
        return SUBMIT_HW

    elif callback_data.startswith("cancel_"):
        course_id = context.chat_data["current_course_id"]
        hws = context.bot_data["courses"][course_id]["HWs"]
        moscow_tz = pytz.timezone("Europe/Moscow")
        buttons = [
            InlineKeyboardButton(
                text=f"🏠 {hw_data['title']}", callback_data=f"hw_{hw_id}"
            )
            for hw_id, hw_data in hws.items()
        ]
        buttons.append(
            InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"back_to_course")
        )
        text = f"🚨 Доступны домашние задания:"
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return SUBMIT_HW_REQUEST


async def hw_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered hw_comment handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("cancel"):
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        deadline_str = str(course_data["HWs"][hw_id]['deadline']).split('+')[0]

        student_id = context.user_data["current_user"]["id"]

        text = f"🏠 ДЗ: {hw_data['title']}\n"\
                f"🕰️ Дедлайн: {deadline_str}\n"
        
        already_sent = student_id in hw_data["students"].keys()

        if "comments" not in hw_data.keys():
            context.bot_data["courses"][course_id]["HWs"][hw_id]["comments"] = {}

        commented = student_id in hw_data["comments"].keys()
        scored = student_id in hw_data["scores"].keys()

        if scored:
            text += f"💯 Оценка: {hw_data['scores'][student_id]}\n"
        
        buttons = []
        
        if commented:
            buttons.append(
                InlineKeyboardButton(
                    text=f"💬 Комментарий",
                    callback_data=f"comment_{hw_id}"
                )
            )
        
        moscow_tz = pytz.timezone("Europe/Moscow")
        if hw_data["deadline"] >= datetime.now(moscow_tz):
            buttons.append(
                InlineKeyboardButton(
                    text=f"📤 Загрузить ДЗ",
                    callback_data=f"upload_{hw_id}"
                )
            )
        
        buttons.append(
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"cancel_{hw_id}"
            )
        )

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
        return HW_MENU


async def submit_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered submit_hw handler")

    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        pass
    
    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU
    if callback_data == "...":
        document = update.message.document
        course_id = context.chat_data["current_course_id"]
        hw_id = context.chat_data["current_hw_id"]
        student_id = context.user_data["current_user"]["id"]

        context.bot_data["courses"][course_id]["HWs"][hw_id]["students"][
            student_id
        ] = document.file_id

        text = f"✅ Файл {document.file_name} успешно загружен."
        buttons = [InlineKeyboardButton(text=f"🫡 Ладно.", callback_data=f"submit_hw")]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )
        await update.message.reply_text(text=text, reply_markup=keyboard)
        return COURSE_MENU

    elif callback_data == "cancel":
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        if "comments" not in hw_data.keys():
            context.bot_data["courses"][course_id]["HWs"][hw_id]["comments"] = {}
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        deadline_str = str(course_data["HWs"][hw_id]['deadline']).split('+')[0]

        student_id = context.user_data["current_user"]["id"]

        text = f"🏠 ДЗ: {hw_data['title']}\n"\
                f"🕰️ Дедлайн: {deadline_str}\n"
        
        already_sent = student_id in hw_data["students"].keys()

        commented = student_id in hw_data["comments"].keys()
        scored = student_id in hw_data["scores"].keys()

        if scored:
            text += f"💯 Оценка: {hw_data['scores'][student_id]}\n"
        
        buttons = []
        
        if commented:
            buttons.append(
                InlineKeyboardButton(
                    text=f"💬 Комментарий",
                    callback_data=f"comment_{hw_id}"
                )
            )
        
        moscow_tz = pytz.timezone("Europe/Moscow")
        if hw_data["deadline"] >= datetime.now(moscow_tz):
            buttons.append(
                InlineKeyboardButton(
                    text=f"📤 Загрузить ДЗ",
                    callback_data=f"upload_{hw_id}"
                )
            )
        
        buttons.append(
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"cancel_{hw_id}"
            )
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )
        return HW_MENU


async def tests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered tests_menu handler")

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    await update.callback_query.answer()
    callback_data = update.callback_query.data

    course_id = context.chat_data["current_course_id"]

    if callback_data in context.bot_data["courses"][course_id]["tests"].keys():
        test_id = callback_data
        context.user_data["current_test_id"] = test_id
        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        student_id = context.user_data["current_user"]["id"]
        if test_data["status"] == "active":
            # active test branch
            if "entered_students" not in context.bot_data["courses"][course_id]["tests"][test_id].keys():
                context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"] = \
                    recover_entered_students_data(
                        test_data=test_data,
                        course_students=context.bot_data["courses"][course_id]["students"]
                    )
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            context.bot_data["courses"][course_id]["tests"][test_id][
                "entered_students"
            ].append(context.user_data["current_user"])
            context.bot_data[f"to_send_scores_{test_id}"].append(student_id)
            if f"students_{test_id}" not in context.bot_data.keys():
                context.bot_data[f"students_{test_id}"] = [student_id]
            elif student_id not in context.bot_data[f"students_{test_id}"]:
                context.bot_data[f"students_{test_id}"].append(student_id)

            if student_id in test_data["answers"].keys() and len(
                test_data["answers"][student_id].keys()
            ) == len(test_data["questions"].keys()):
                # на все вопросы уже ответил
                text = (
                    f"⛱️ Вы уже ответили на все вопросы."
                    f"Дождитесь завершения теста, чтобы увидеть свою оценку."
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"↩️ Назад к тестам", callback_data=f"back_to_tests"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
                return WAIT_TEST_FINISH
            else:
                # есть неотвеченные вопросы
                all_questions_ids = test_data["questions"].keys()
                answered_questions_ids = []
                if student_id in test_data["answers"].keys():
                    answered_questions_ids = list(
                        test_data["answers"][student_id].keys()
                    )
                unanswered_questions_ids = [
                    question_id
                    for question_id in all_questions_ids
                    if question_id not in answered_questions_ids
                ]
                question_to_ask_id = random.choice(unanswered_questions_ids)
                context.user_data["current_question_id"] = question_to_ask_id

                # оставшееся время
                moscow_tz = pytz.timezone("Europe/Moscow")
                start_test_time = test_data["start_time"]
                duration = timedelta(minutes=test_data["time_to_solve"])
                finish_test_time = start_test_time + duration
                current_time = datetime.now(moscow_tz)
                delta = finish_test_time - current_time
                total_seconds = delta.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                text = (
                    f"Тест: {test_data['title']}\n"
                    f"⏳ Осталось времени: {minutes}:{seconds}"
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                question_data = test_data["questions"][question_to_ask_id]

                # удаляем сообщение со списком тестов
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.chat_data["tests_del_msg_id"],
                    )
                except:
                    pass

                if (
                    question_data["type"] == "multiple_choice"
                    and "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True] 
                ):
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message = await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=question_photo,
                        caption=text,
                        reply_markup=keyboard,
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=text,
                        reply_markup=keyboard,
                    )

                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ] = {
                    "chat_id": update.effective_chat.id,
                    "message_id": message.message_id,
                }
                if question_data["type"] == "multiple_choice":
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        poll = await context.bot.send_poll(
                            chat_id=update.effective_chat.id,
                            question="Смотри картинку",
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    else:
                        poll = await context.bot.send_poll(
                            chat_id=update.effective_chat.id,
                            question=question_data["text"],
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = poll.message_id
                    logging.warning(
                        f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                    )
                elif question_data["type"] == "text_answer":
                    question_data = test_data["questions"][question_to_ask_id]
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                elif question_data["type"] == "file_answer":
                    question_data = test_data["questions"][question_to_ask_id]

                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                return SEND_QUESTION
        elif test_data["status"] == "past":
            # past test branch
            if student_id in test_data["answers"].keys():
                scores = test_data["scores"]
                answers = test_data["answers"]
                questions = test_data["questions"]

                total_student_score = 0
                for question_id, score in scores[student_id].items():
                    if score is not None:
                        total_student_score += score

                incorrect_answers = {}
                is_for_teacher_check = False
                for question_id, student_answers in answers[student_id].items():
                    if questions[question_id]["type"] == "multiple_choice":
                        if set(questions[question_id]["correct_answers"]) != set(
                            student_answers
                        ):
                            incorrect_answers[question_id] = student_answers
                    elif scores[student_id][question_id] is not None:
                        if (
                            scores[student_id][question_id]
                            < questions[question_id]["score"]
                        ):
                            incorrect_answers[question_id] = student_answers
                    else:
                        is_for_teacher_check = True

                unanswered_questions_ids = []
                for question_id in questions.keys():
                    if question_id not in answers[student_id].keys():
                        unanswered_questions_ids.append(question_id)

                text = f""
                if is_for_teacher_check:
                    text += (
                        f"🚸 Тест содержит вопросы, ответы на которые не проверяются автоматически."
                        f"Ниже приведена оценка, полученная с учетом только тех вопросов, которые не"
                        f"требуют проверки преподавателем. Дождитесь проверки остальных вопросов,"
                        f" чтобы увидеть релевантную оценку.\n"
                    )
                text += (
                    f"<b>Оценка: {total_student_score}/{test_data['total_score']}</b>\n"
                )
                if incorrect_answers:
                    # есть неправильные ответы
                    text += f"❌ <b>Ошибки:</b>\n"
                    for question_id, student_answers in incorrect_answers.items():
                        if questions[question_id]["type"] == "multiple_choice":
                            student_answers_str = ""
                            for answer in student_answers:
                                if answer != student_answers[-1]:
                                    student_answers_str += f"'{answer}', "
                                else:
                                    student_answers_str += f"'{answer}'"
                            text += (
                                f"<b>Вопрос:</b> '{questions[question_id]['text']}'\n"
                                f"<b>Ваши ответы:</b> {student_answers_str}\n"
                                f"<b>Правильные ответы:</b> {questions[question_id]['correct_answers']}\n"
                            )
                        elif questions[question_id]["type"] == "text_answer":
                            student_answers_str = ""
                            for answer in student_answers:
                                if answer != student_answers[-1]:
                                    student_answers_str += f"'{answer}', "
                                else:
                                    student_answers_str += f"'{answer}'"
                            text += (
                                f"<b>Вопрос:</b> '{questions[question_id]['text']}'\n"
                                f"<b>Ваши ответ:</b> {student_answers_str}\n"
                            )
                        else:
                            student_answers_str = ""
                            for answer in student_answers:
                                if answer != student_answers[-1]:
                                    student_answers_str += f"'{answer}', "
                                else:
                                    student_answers_str += f"'{answer}'"
                            text += (
                                f"<b>Вопрос:</b> '{questions[question_id]['text']}'\n"
                            )
                    if len(unanswered_questions_ids) > 0:
                        text += f"🙊 <b>Нет ответа:</b>\n"
                        for question_id in unanswered_questions_ids:
                            question_text = questions[question_id]["text"]
                            text += f"<b>Вопрос:</b> {question_text}\n"
                            if questions[question_id]["type"] == "multiple_choice":
                                correct_answers = questions[question_id][
                                    "correct_answers"
                                ]
                                text += f"<b>Правильные ответы:</b> {correct_answers}\n"
                elif len(unanswered_questions_ids) == 0:
                    if not is_for_teacher_check:
                        text += f"🤓 Вы ответили правильно на все вопросы!\n"
                else:
                    text += f"🙊 <b>Нет ответа:</b>\n"
                    for question_id in unanswered_questions_ids:
                        question_text = questions[question_id]["text"]
                        if questions[question_id]["type"] == "multiple_choice":
                            correct_answers = questions[question_id]["correct_answers"]
                            text += (
                                f"<b>Вопрос:</b> {question_text}\n"
                                f"<b>Правильные ответы:</b> {correct_answers}\n"
                            )
                        else:
                            text += f"<b>Вопрос:</b> {question_text}\n"
                buttons = [
                    InlineKeyboardButton(
                        text=f"↩️ Назад к тестам", callback_data="tests"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard, parse_mode="HTML"
                )
                return TEST_SCORE
            else:
                # студент не писал этот тест
                text = f"🙅 В этом тесте вы не ответили ни на один вопрос."
                buttons = [
                    InlineKeyboardButton(
                        text=f"↩️ Назад к тестам", callback_data="tests"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard, parse_mode="HTML"
                )
                return COURSE_MENU
    elif callback_data.startswith("back_to_course_"):
        course_id = callback_data[len("back_to_course_") :]
        course_data = context.bot_data["courses"][course_id]
        context.chat_data["current_course_id"] = course_id

        text = f"🔉 Курс: {course_data['title']}\n" f"🔗 Ссылка: {course_data['link']}\n"
        buttons = [
            InlineKeyboardButton(text=f"📃 Тесты", callback_data=f"tests"),
            InlineKeyboardButton(text=f"📤 Сдать ДЗ", callback_data=f"submit_hw"),
            InlineKeyboardButton(
                text=f"↩️ Назад к курсам", callback_data=f"back_to_courses"
            ),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MENU


async def wait_test_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered wait_test_finish handler")

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "back_to_tests":
        course_id = context.chat_data["current_course_id"]
        student_id = context.user_data["current_user"]["id"]
        tests_to_display = {}
        for test_id in context.bot_data["courses"][course_id][
            "tests"
        ].keys():
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if "entered_students" not in test_data.keys():
                context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"] = \
                    recover_entered_students_data(
                        test_data=test_data,
                        course_students=context.bot_data["courses"][course_id]["students"]
                    )
                test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if (
                test_data["status"] == "active"
                or test_data["status"] == "past"
                and (
                    student_id in test_data["answers"].keys()
                    or student_id in [st["id"] for st in test_data["entered_students"]]
                )
            ):
                tests_to_display[test_id] = test_data
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Назад к курсу", callback_data=f"back_to_course_{course_id}"
            )
        ]
        if len(tests_to_display.keys()) > 0:
            buttons += [
                InlineKeyboardButton(
                    text=f"{test_data['title']}", callback_data=f"{test_id}"
                )
                for test_id, test_data in tests_to_display.items()
            ]
            text = f"✅ Ваши тесты:"
        else:
            text = f"❌У вас нет активных или завершенных тестов."

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        context.chat_data["tests_del_msg_id"] = message.message_id
        return TESTS_MENU


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered send_question handler")

    #flag = await check_student_consistance(
    #    context=context,
    #    chat_id=context.chat_data["chat_id"],
    #    effective_msg_id=update.effective_message.message_id
    #)
    #if flag:
    #    return STUDENT_MENU

    if update.poll_answer:
        # обработка ответа
        answer = update.poll_answer
        # answered_poll = context.bot_data[answer.poll_id]
        question_id = context.user_data["current_question_id"]
        test_id = context.user_data["current_test_id"]
        course_id = context.user_data["current_course_id"]
        question_data = context.bot_data["courses"][course_id]["tests"][test_id][
            "questions"
        ][question_id]
        selected_options_ids = answer.option_ids
        selected_options = [question_data["options"][i] for i in selected_options_ids]

        student_id = context.user_data["current_user"]["id"]
        if (
            student_id
            not in context.bot_data["courses"][course_id]["tests"][test_id][
                "answers"
            ].keys()
        ):
            context.bot_data["courses"][course_id]["tests"][test_id]["answers"][
                student_id
            ] = {question_id: list(selected_options)}
        else:
            context.bot_data["courses"][course_id]["tests"][test_id]["answers"][
                student_id
            ][question_id] = list(selected_options)

        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        logging.warning(f"🙅 test_data['active_data']: {test_data['active_data']}")
        active_data = test_data["active_data"][student_id]
        # дальнейшие действия -- отправить еще вопрос или
        # отправить ждать конца теста
        if student_id in test_data["answers"].keys() and len(
            test_data["answers"][student_id].keys()
        ) == len(test_data["questions"].keys()):
            # на все попросы уже ответил
            # удаляем сообщение непосредственно над опросом
            await context.bot.delete_message(
                chat_id=active_data["chat_id"], message_id=active_data["message_id"]
            )
            # удаляем опрос, на который студик уже ответил
            await context.bot.delete_message(
                chat_id=active_data["chat_id"],
                message_id=active_data["poll_message_id"],
            )
            try:
                context.bot_data[f"to_send_scores_{test_id}"].remove(student_id)
            except:
                pass
            text = (
                f"Вы уже ответили на все вопросы."
                f"Дождитесь завершения теста, чтобы увидеть свою оценку."
            )
            buttons = [
                InlineKeyboardButton(text=f"↩️ Тесты", callback_data=f"back_to_tests")
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await context.bot.send_message(
                chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
            )
            return WAIT_TEST_FINISH
        else:
            # еще есть вопросики
            # удаляем сообщение непосредственно над опросом
            await context.bot.delete_message(
                chat_id=active_data["chat_id"], message_id=active_data["message_id"]
            )
            # удаляем опрос, на который студик уже ответил
            await context.bot.delete_message(
                chat_id=active_data["chat_id"],
                message_id=active_data["poll_message_id"],
            )
            # ===========================================
            all_questions_ids = test_data["questions"].keys()
            answered_questions_ids = []
            if student_id in test_data["answers"].keys():
                answered_questions_ids = list(test_data["answers"][student_id].keys())
            unanswered_questions_ids = [
                question_id
                for question_id in all_questions_ids
                if question_id not in answered_questions_ids
            ]
            question_to_ask_id = random.choice(unanswered_questions_ids)
            context.user_data["current_question_id"] = question_to_ask_id
            # оставшееся время
            moscow_tz = pytz.timezone("Europe/Moscow")
            start_test_time = test_data["start_time"]
            duration = timedelta(minutes=test_data["time_to_solve"])
            finish_test_time = start_test_time + duration
            current_time = datetime.now(moscow_tz)
            delta = finish_test_time - current_time
            total_seconds = delta.total_seconds()
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            text = (
                f"Тест: {test_data['title']}\n"
                f"⏳ Оставшееся время: {minutes}:{seconds}"
            )
            buttons = [
                InlineKeyboardButton(
                    text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

            question_data = test_data["questions"][question_to_ask_id]

            if (
                question_data["type"] == "multiple_choice"
                and "is_markdown" in question_data.keys()
                and question_data["is_markdown"] in ["true", "True", True]
            ):
                question_img_path = (
                    f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                )
                question_photo = open(question_img_path, "rb")
                message = await context.bot.send_photo(
                    chat_id=active_data["chat_id"],
                    photo=question_photo,
                    caption=text,
                    reply_markup=keyboard,
                )
            else:
                message = await context.bot.send_message(
                    chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                )

            context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                student_id
            ] = {"chat_id": active_data["chat_id"], "message_id": message.message_id}
            if question_data["type"] == "multiple_choice":
                if (
                    "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    poll = await context.bot.send_poll(
                        chat_id=active_data["chat_id"],
                        question="Смотри картинку",
                        options=question_data["options"],
                        is_anonymous=False,
                        allows_multiple_answers=True,
                        protect_content=True,
                        type="regular",
                    )
                else:
                    poll = await context.bot.send_poll(
                        chat_id=active_data["chat_id"],
                        question=question_data["text"],
                        options=question_data["options"],
                        is_anonymous=False,
                        allows_multiple_answers=True,
                        protect_content=True,
                        type="regular",
                    )
                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ]["poll_message_id"] = poll.message_id
                logging.warning(
                    f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                )
            elif question_data["type"] == "text_answer":
                question_data = test_data["questions"][question_to_ask_id]
                if (
                    "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    text = (
                        f"Отправьте текстовый ответ на вопрос:\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message_question = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        protect_content=True,
                    )
                else:
                    text = (
                        f"Отправьте текстовый ответ на вопрос:\n"
                        f"{question_data['text']}\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    message_question = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, protect_content=True
                    )
                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ]["poll_message_id"] = message_question.message_id
            elif question_data["type"] == "file_answer":
                question_data = test_data["questions"][question_to_ask_id]

                if (
                    "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    text = (
                        f"Отправьте файл-ответ на вопрос:\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message_question = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        protect_content=True,
                    )
                else:
                    text = (
                        f"Отправьте файл-ответ на вопрос:\n"
                        f"{question_data['text']}\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    message_question = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, protect_content=True
                    )
                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ]["poll_message_id"] = message_question.message_id
            return SEND_QUESTION
    elif update.callback_query:
        # skip button branch
        await update.callback_query.answer()
        callback_data = update.callback_query.data

        if callback_data.startswith("skip_"):
            skipped_question_id = context.user_data["current_question_id"]
            test_id = context.user_data["current_test_id"]
            course_id = context.user_data["current_course_id"]
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            student_id = context.user_data["current_user"]["id"]
            all_questions_ids = test_data["questions"].keys()
            answered_questions_ids = []
            if student_id in test_data["answers"].keys():
                answered_questions_ids = list(test_data["answers"][student_id].keys())
            unanswered_questions_ids = [
                question_id
                for question_id in all_questions_ids
                if question_id not in answered_questions_ids
            ]
            if len(unanswered_questions_ids) > 1:
                # не будем выбирать скипнутый вопрос, если есть еще другие вопросы
                unanswered_questions_ids = [
                    question_id
                    for question_id in unanswered_questions_ids
                    if question_id != skipped_question_id
                ]
            question_to_ask_id = random.choice(unanswered_questions_ids)
            context.user_data["current_question_id"] = question_to_ask_id
            # оставшееся время
            moscow_tz = pytz.timezone("Europe/Moscow")
            start_test_time = test_data["start_time"]
            duration = timedelta(minutes=test_data["time_to_solve"])
            finish_test_time = start_test_time + duration
            current_time = datetime.now(moscow_tz)
            delta = finish_test_time - current_time
            total_seconds = delta.total_seconds()
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            text = (
                f"Тест: {test_data['title']}\n"
                f"⏳ Оставшееся время: {minutes}:{seconds}"
            )
            buttons = [
                InlineKeyboardButton(
                    text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

            active_data = test_data["active_data"][student_id]
            try:
                # удалить предыдущую пару сообщение+тест, если есть
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
            except:
                pass

            question_data = test_data["questions"][question_to_ask_id]

            if (
                question_data["type"] == "multiple_choice"
                and "is_markdown" in question_data.keys()
                and question_data["is_markdown"] in ["true", "True", True]
            ):
                question_img_path = (
                    f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                )
                question_photo = open(question_img_path, "rb")
                message = await context.bot.send_photo(
                    chat_id=active_data["chat_id"],
                    photo=question_photo,
                    caption=text,
                    reply_markup=keyboard,
                )
            else:
                message = await context.bot.send_message(
                    chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                )

            context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                student_id
            ] = {"chat_id": active_data["chat_id"], "message_id": message.message_id}
            if question_data["type"] == "multiple_choice":
                if (
                    "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    poll = await context.bot.send_poll(
                        chat_id=active_data["chat_id"],
                        question="Смотри картинку",
                        options=question_data["options"],
                        is_anonymous=False,
                        allows_multiple_answers=True,
                        protect_content=True,
                        type="regular",
                    )
                else:
                    poll = await context.bot.send_poll(
                        chat_id=active_data["chat_id"],
                        question=question_data["text"],
                        options=question_data["options"],
                        is_anonymous=False,
                        allows_multiple_answers=True,
                        protect_content=True,
                        type="regular",
                    )
                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ]["poll_message_id"] = poll.message_id
                logging.warning(
                    f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                )
            elif question_data["type"] == "text_answer":
                question_data = test_data["questions"][question_to_ask_id]
                if (
                    "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    text = (
                        f"Отправьте текстовый ответ на вопрос:\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message_question = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        protect_content=True,
                    )
                else:
                    text = (
                        f"Отправьте текстовый ответ на вопрос:\n"
                        f"{question_data['text']}\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    message_question = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, protect_content=True
                    )
                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ]["poll_message_id"] = message_question.message_id
            elif question_data["type"] == "file_answer":
                question_data = test_data["questions"][question_to_ask_id]

                if (
                    "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    text = (
                        f"Отправьте файл-ответ на вопрос:\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message_question = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        protect_content=True,
                    )
                else:
                    text = (
                        f"Отправьте файл-ответ на вопрос:\n"
                        f"{question_data['text']}\n"
                        f"⚠️ После отправки изменить ответ нельзя.\n"
                    )
                    message_question = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, protect_content=True
                    )
                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ]["poll_message_id"] = message_question.message_id
            return SEND_QUESTION

        elif callback_data == str(TESTS_MANAGEMENT):
            course_id = context.user_data["current_course_id"]
            student_id = context.user_data["current_user"]["id"]
            try:
                context.bot_data[f"to_send_scores_{test_id}"].remove(student_id)
            except:
                pass
            tests_to_display = {}
            for test_id in context.bot_data["courses"][course_id][
                "tests"
            ].keys():
                test_data = context.bot_data["courses"][course_id]["tests"][test_id]
                if "entered_students" not in test_data.keys():
                    context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"] = \
                        recover_entered_students_data(
                            test_data=test_data,
                            course_students=context.bot_data["courses"][course_id]["students"]
                        )
                    test_data = context.bot_data["courses"][course_id]["tests"][test_id]
                if (
                    test_data["status"] == "active"
                    or test_data["status"] == "past"
                    and (
                        student_id in test_data["answers"].keys()
                        or student_id
                        in [st["id"] for st in test_data["entered_students"]]
                    )
                ):
                    tests_to_display[test_id] = test_data
            buttons = [
                InlineKeyboardButton(
                    text=f"↩️ Назад к курсу",
                    callback_data=f"back_to_course_{course_id}",
                )
            ]
            if len(tests_to_display.keys()) > 0:
                buttons += [
                    InlineKeyboardButton(
                        text=f"{test_data['title']}", callback_data=f"{test_id}"
                    )
                    for test_id, test_data in tests_to_display.items()
                ]
                text = f"✅ Ваши тесты:"
            else:
                text = f"❌У вас нет активных или завершенных тестов."

            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            message = await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
            context.chat_data["tests_del_msg_id"] = message.message_id
            return TESTS_MENU
    elif update.message:
        if update.message.document or update.message.photo:
            # document or photo sent
            if update.message.document:
                document = update.message.document

            if update.message.photo:
                document = update.message.photo[-1]
            file_id = document.file_id
            course_id = context.user_data["current_course_id"]
            test_id = context.user_data["current_test_id"]
            question_id = context.user_data["current_question_id"]
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            question_data = test_data["questions"][question_id]
            student_id = context.user_data["current_user"]["id"]
            active_data = test_data["active_data"][student_id]

            if question_data["type"] != "file_answer":
                text = f"⛔️ Невозможно отправить файл в качестве ответа!\n"
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
                question_to_ask_id = question_id
                # оставшееся время
                moscow_tz = pytz.timezone("Europe/Moscow")
                start_test_time = test_data["start_time"]
                duration = timedelta(minutes=test_data["time_to_solve"])
                finish_test_time = start_test_time + duration
                current_time = datetime.now(moscow_tz)
                delta = finish_test_time - current_time
                total_seconds = delta.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                text += (
                    f"Тест: {test_data['title']}\n"
                    f"⏳ Оставшееся время: {minutes}:{seconds}"
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                question_data = test_data["questions"][question_to_ask_id]

                if (
                    question_data["type"] == "multiple_choice"
                    and "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        reply_markup=keyboard,
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                    )

                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ] = {
                    "chat_id": active_data["chat_id"],
                    "message_id": message.message_id,
                }
                if question_data["type"] == "multiple_choice":
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question="Смотри картинку",
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    else:
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question=question_data["text"],
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = poll.message_id
                    logging.warning(
                        f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                    )
                elif question_data["type"] == "text_answer":
                    question_data = test_data["questions"][question_to_ask_id]
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                elif question_data["type"] == "file_answer":
                    question_data = test_data["questions"][question_to_ask_id]

                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                return SEND_QUESTION

            # всё ок, сохраняем, отправляем следующий, если есть:
            student_id = context.user_data["current_user"]["id"]
            if (
                student_id
                not in context.bot_data["courses"][course_id]["tests"][test_id][
                    "answers"
                ].keys()
            ):
                context.bot_data["courses"][course_id]["tests"][test_id]["answers"][
                    student_id
                ] = {question_id: [file_id]}
            else:
                context.bot_data["courses"][course_id]["tests"][test_id]["answers"][
                    student_id
                ][question_id] = [file_id]

            active_data = test_data["active_data"][student_id]
            # дальнейшие действия -- отправить еще вопрос или
            # отправить ждать конца теста
            if student_id in test_data["answers"].keys() and len(
                test_data["answers"][student_id].keys()
            ) == len(test_data["questions"].keys()):
                # на все попросы уже ответил
                # удаляем сообщение непосредственно над опросом
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
                try:
                    context.bot_data[f"to_send_scores_{test_id}"].remove(student_id)
                except:
                    pass
                text = (
                    f"Вы уже ответили на все вопросы."
                    f"Дождитесь завершения теста, чтобы увидеть свою оценку."
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"↩️ Тесты", callback_data=f"back_to_tests"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                await context.bot.send_message(
                    chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                )
                return WAIT_TEST_FINISH
            else:
                # еще есть вопросики
                # удаляем сообщение непосредственно над опросом
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
                # ===========================================
                all_questions_ids = test_data["questions"].keys()
                answered_questions_ids = []
                if student_id in test_data["answers"].keys():
                    answered_questions_ids = list(
                        test_data["answers"][student_id].keys()
                    )
                unanswered_questions_ids = [
                    question_id
                    for question_id in all_questions_ids
                    if question_id not in answered_questions_ids
                ]
                question_to_ask_id = random.choice(unanswered_questions_ids)
                context.user_data["current_question_id"] = question_to_ask_id
                # оставшееся время
                moscow_tz = pytz.timezone("Europe/Moscow")
                start_test_time = test_data["start_time"]
                duration = timedelta(minutes=test_data["time_to_solve"])
                finish_test_time = start_test_time + duration
                current_time = datetime.now(moscow_tz)
                delta = finish_test_time - current_time
                total_seconds = delta.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                text = (
                    f"Тест: {test_data['title']}\n"
                    f"⏳ Оставшееся время: {minutes}:{seconds}"
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                question_data = test_data["questions"][question_to_ask_id]

                if (
                    question_data["type"] == "multiple_choice"
                    and "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        reply_markup=keyboard,
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                    )

                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ] = {
                    "chat_id": active_data["chat_id"],
                    "message_id": message.message_id,
                }
                if question_data["type"] == "multiple_choice":
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question="Смотри картинку",
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    else:
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question=question_data["text"],
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = poll.message_id
                    logging.warning(
                        f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                    )
                elif question_data["type"] == "text_answer":
                    question_data = test_data["questions"][question_to_ask_id]
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                elif question_data["type"] == "file_answer":
                    question_data = test_data["questions"][question_to_ask_id]

                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                return SEND_QUESTION
        else:
            # text answer sent
            text_answer = update.message.text
            course_id = context.user_data["current_course_id"]
            test_id = context.user_data["current_test_id"]
            question_id = context.user_data["current_question_id"]
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            question_data = test_data["questions"][question_id]
            student_id = context.user_data["current_user"]["id"]
            active_data = test_data["active_data"][student_id]

            if question_data["type"] != "text_answer":
                text = f"⛔️ Невозможно отправить текст в качестве ответа!\n"
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем (в)опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
                question_to_ask_id = question_id
                # оставшееся время
                moscow_tz = pytz.timezone("Europe/Moscow")
                start_test_time = test_data["start_time"]
                duration = timedelta(minutes=test_data["time_to_solve"])
                finish_test_time = start_test_time + duration
                current_time = datetime.now(moscow_tz)
                delta = finish_test_time - current_time
                total_seconds = delta.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                text += (
                    f"Тест: {test_data['title']}\n"
                    f"⏳ Оставшееся время: {minutes}:{seconds}"
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                question_data = test_data["questions"][question_to_ask_id]

                if (
                    question_data["type"] == "multiple_choice"
                    and "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        reply_markup=keyboard,
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                    )

                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ] = {
                    "chat_id": active_data["chat_id"],
                    "message_id": message.message_id,
                }
                if question_data["type"] == "multiple_choice":
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question="Смотри картинку",
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    else:
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question=question_data["text"],
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = poll.message_id
                    logging.warning(
                        f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                    )
                elif question_data["type"] == "text_answer":
                    question_data = test_data["questions"][question_to_ask_id]
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                elif question_data["type"] == "file_answer":
                    question_data = test_data["questions"][question_to_ask_id]

                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                return SEND_QUESTION

            # всё ок, сохраняем, отправляем следующий, если есть:
            student_id = context.user_data["current_user"]["id"]
            if (
                student_id
                not in context.bot_data["courses"][course_id]["tests"][test_id][
                    "answers"
                ].keys()
            ):
                context.bot_data["courses"][course_id]["tests"][test_id]["answers"][
                    student_id
                ] = {question_id: [text_answer]}
            else:
                context.bot_data["courses"][course_id]["tests"][test_id]["answers"][
                    student_id
                ][question_id] = [text_answer]

            active_data = test_data["active_data"][student_id]
            # дальнейшие действия -- отправить еще вопрос или
            # отправить ждать конца теста
            if student_id in test_data["answers"].keys() and len(
                test_data["answers"][student_id].keys()
            ) == len(test_data["questions"].keys()):
                # на все попросы уже ответил
                # удаляем сообщение непосредственно над опросом
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
                try:
                    context.bot_data[f"to_send_scores_{test_id}"].remove(student_id)
                except:
                    pass
                text = (
                    f"Вы уже ответили на все вопросы."
                    f"Дождитесь завершения теста, чтобы увидеть свою оценку."
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"↩️ Тесты", callback_data=f"back_to_tests"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                await context.bot.send_message(
                    chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                )
                return WAIT_TEST_FINISH
            else:
                # еще есть вопросики
                # удаляем сообщение непосредственно над опросом
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"], message_id=active_data["message_id"]
                )
                # удаляем опрос, на который студик уже ответил
                await context.bot.delete_message(
                    chat_id=active_data["chat_id"],
                    message_id=active_data["poll_message_id"],
                )
                # ===========================================
                all_questions_ids = test_data["questions"].keys()
                answered_questions_ids = []
                if student_id in test_data["answers"].keys():
                    answered_questions_ids = list(
                        test_data["answers"][student_id].keys()
                    )
                unanswered_questions_ids = [
                    question_id
                    for question_id in all_questions_ids
                    if question_id not in answered_questions_ids
                ]
                question_to_ask_id = random.choice(unanswered_questions_ids)
                context.user_data["current_question_id"] = question_to_ask_id
                # оставшееся время
                moscow_tz = pytz.timezone("Europe/Moscow")
                start_test_time = test_data["start_time"]
                duration = timedelta(minutes=test_data["time_to_solve"])
                finish_test_time = start_test_time + duration
                current_time = datetime.now(moscow_tz)
                delta = finish_test_time - current_time
                total_seconds = delta.total_seconds()
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                text = (
                    f"Тест: {test_data['title']}\n"
                    f"⏳ Оставшееся время: {minutes}:{seconds}"
                )
                buttons = [
                    InlineKeyboardButton(
                        text=f"⏩ Пропустить", callback_data=f"skip_{test_id}"
                    )
                ]
                keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                question_data = test_data["questions"][question_to_ask_id]

                if (
                    question_data["type"] == "multiple_choice"
                    and "is_markdown" in question_data.keys()
                    and question_data["is_markdown"] in ["true", "True", True]
                ):
                    question_img_path = (
                        f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                    )
                    question_photo = open(question_img_path, "rb")
                    message = await context.bot.send_photo(
                        chat_id=active_data["chat_id"],
                        photo=question_photo,
                        caption=text,
                        reply_markup=keyboard,
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=active_data["chat_id"], text=text, reply_markup=keyboard
                    )

                context.bot_data["courses"][course_id]["tests"][test_id]["active_data"][
                    student_id
                ] = {
                    "chat_id": active_data["chat_id"],
                    "message_id": message.message_id,
                }
                if question_data["type"] == "multiple_choice":
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question="Смотри картинку",
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    else:
                        poll = await context.bot.send_poll(
                            chat_id=active_data["chat_id"],
                            question=question_data["text"],
                            options=question_data["options"],
                            is_anonymous=False,
                            allows_multiple_answers=True,
                            protect_content=True,
                            type="regular",
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = poll.message_id
                    logging.warning(
                        f"⛔️ active_data: {context.bot_data['courses'][course_id]['tests'][test_id]['active_data']}"
                    )
                elif question_data["type"] == "text_answer":
                    question_data = test_data["questions"][question_to_ask_id]
                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте текстовый ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                elif question_data["type"] == "file_answer":
                    question_data = test_data["questions"][question_to_ask_id]

                    if (
                        "is_markdown" in question_data.keys()
                        and question_data["is_markdown"] in ["true", "True", True]
                    ):
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        question_img_path = f"./test_{test_id}_questions/question_{question_to_ask_id}.png"
                        question_photo = open(question_img_path, "rb")
                        message_question = await context.bot.send_photo(
                            chat_id=active_data["chat_id"],
                            photo=question_photo,
                            caption=text,
                            protect_content=True,
                        )
                    else:
                        text = (
                            f"Отправьте файл-ответ на вопрос:\n"
                            f"{question_data['text']}\n"
                            f"⚠️ После отправки изменить ответ нельзя.\n"
                        )
                        message_question = await context.bot.send_message(
                            chat_id=active_data["chat_id"],
                            text=text,
                            protect_content=True,
                        )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ][student_id]["poll_message_id"] = message_question.message_id
                return SEND_QUESTION


async def test_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"👻 Entered test_score handler")

    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU

    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "tests":
        # "Back to tests" button
        course_id = context.user_data["current_course_id"]
        student_id = context.user_data["current_user"]["id"]
        tests_to_display = {}
        for test_id in context.bot_data["courses"][course_id][
            "tests"
        ].keys():
            test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if "entered_students" not in test_data.keys():
                context.bot_data["courses"][course_id]["tests"][test_id]["entered_students"] = \
                    recover_entered_students_data(
                        test_data=test_data,
                        course_students=context.bot_data["courses"][course_id]["students"]
                    )
                test_data = context.bot_data["courses"][course_id]["tests"][test_id]
            if (
                test_data["status"] == "active"
                or test_data["status"] == "past"
                and (
                    student_id in test_data["answers"].keys()
                    or student_id in [st["id"] for st in test_data["entered_students"]]
                )
            ):
                tests_to_display[test_id] = test_data
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Назад к курсу", callback_data=f"back_to_course_{course_id}"
            )
        ]
        if len(tests_to_display.keys()) > 0:
            buttons += [
                InlineKeyboardButton(
                    text=f"{test_data['title']}", callback_data=f"{test_id}"
                )
                for test_id, test_data in tests_to_display.items()
            ]
            text = f"✅ Ваши тесты:"
        else:
            text = f"❌У вас нет активных или завершенных тестов."
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        context.chat_data["tests_del_msg_id"] = message.message_id
        return TESTS_MENU
