# handlers.py
from telegram.ext import (
    filters,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    CommandHandler,
    PollAnswerHandler,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document

from handlers.states import *
import logging
import os
import json
from datetime import datetime, timedelta
import pytz
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from handlers.student_handlers import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

from utils.utils import create_scores_file

from handlers.hw_teacher_handlers import (
    hws_management,
    hw_management,
    hw_info,
    hw_grade,
    hw_save_grade,
    add_hw_title,
    add_deadline,
    add_hw,
    edit_hw_deadline,
    save_hw_deadline,
    edit_hw_title,
    save_hw_title,
    remove_hw,
    comment_hw_request,
    send_hw_comment,
    upload_scores_hw_document,
    upload_scores_hw_bttn,
    uploading_scores_hw,
    download_hw_solutions
)

from handlers.course_teacher_handlers import (
    courses_management,
    course_management,
    remove_course_request,
    remove_course,
    edit_course_code,
    edit_course_title,
    edit_course_link,
    add_course_code,
    add_course_link,
    add_course,
    course_students,
    course_student,
    kick_student,
    edit_student_name,
    save_student_name,
    add_teacher_name,
    add_teacher_username_bttn,
    add_teacher_username_msg,
    add_teacher_id_bttn,
    add_teacher_id_msg,
    add_teacher
)

from handlers.future_test_handlers import (
    edit_future_test,
    edit_test_title,
    remove_test,
    reupload_test,
)

from handlers.active_test_handlers import (
    active_test_management,
    send_message_request,
    send_message,
    finalize_test_action,
)

from handlers.past_test_handlers import (
    send_answers, 
    sent_answers, 
    test_grade, 
    test_save_grade,
    upload_scores_test_bttn,
    upload_scores_test_document,
    uploading_scores_test
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning("🤖 Entered start handler")

    deleted_webhook = await context.bot.delete_webhook()
    print(f"deleted_webhook: {deleted_webhook}")
    if False:
        # normalize past tests scores in "BLM4" course (main course)
        for test_id, test_data in context.bot_data["courses"]["BLM4"]["tests"].items():
            total_score = 0
            if "total_score" in test_data.keys():
                total_score = float(test_data["total_score"])
            else:
                for question_id, question_data in test_data["questions"].items():
                    total_score += float(question_data["score"])

            # normalize student's scores:
            # new_question_score = question_score / total_score * 100
            for student_id, student_data in test_data["scores"].items():
                for question_id, question_score in student_data.items():
                    if question_score:
                        context.bot_data["courses"]["BLM4"]["tests"][test_id]["scores"][student_id][question_id] = float(question_score) / total_score * 100

            # normalize question's scores
            for question_id, question_data in test_data["questions"].items():
                if question_data["score"]:
                    context.bot_data["courses"]["BLM4"]["tests"][test_id]["questions"][question_id]["score"] = float(question_data["score"]) / total_score * 100

            if "total_score" in test_data.keys():
                context.bot_data["courses"]["BLM4"]["tests"][test_id]["total_score"] = 100

    with open("init_config.json", "r") as init_config_file:
        init_config = json.load(init_config_file)

    if "creators" not in context.bot_data.keys():
        context.bot_data["creators"] = init_config["creators"]

    if "courses" not in context.bot_data.keys():
        context.bot_data["courses"] = init_config["courses"]

    if "BLM4" in context.bot_data["courses"].keys() and \
        292216327 not in [teacher["id"] for teacher in context.bot_data["courses"]["BLM4"]["teachers"]]:
        context.bot_data["courses"]["BLM4"]["teachers"].append(
            {
                "name": "Eugene Riabinin",
                "username": "REV757",
                "id": 292216327
            }
        )

    user = update.message.from_user
    context.user_data["current_user"] = {
        "name": f"{user.first_name} {user.last_name}",
        "username": user.username,
        "id": int(user.id),
    }

    if "start_msg_id" in context.chat_data.keys():
        for msg_id in context.chat_data["start_msg_id"]:
        #msg_id = context.chat_data.pop("start_msg_id")
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=msg_id
                )
            except:
                pass
        _ = context.chat_data.pop("start_msg_id")

    await delete_messages(
        context=context,
        chat_id=update.effective_chat.id
    )
    
    is_creator = user.id in [creator["id"] for creator in context.bot_data["creators"]]
    is_teacher = False
    for course_id, course_data in context.bot_data["courses"].items():
        if user.id in [teacher["id"] for teacher in course_data["teachers"]]:
            is_teacher = True
            break

    context.chat_data["chat_id"] = update.message.chat_id

    if is_teacher:
        logging.warning(f"🤖 Detected teacher {user.username}")

        text = f"🤖 Здравствуйте, преподаватель {user.first_name}"
        courses = {}
        for course_id, course_data in context.bot_data["courses"].items():
            if user.id in [teacher["id"] for teacher in course_data["teachers"]]:
                courses[course_id] = course_data

        buttons = [
            InlineKeyboardButton(
                text=f"{course_data['title']}", callback_data=course_id
            )
            for course_id, course_data in courses.items()
        ]

        if is_creator or is_teacher:
            buttons.append(
                InlineKeyboardButton(
                    text=f"+ Добавить новый курс", callback_data="add_new_course"
                )
            )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message = await update.message.reply_text(text, reply_markup=keyboard)
        if "start_msg_id" not in context.chat_data.keys():
            context.chat_data["start_msg_id"] = [message.message_id]
        else:
            context.chat_data["start_msg_id"].append(message.message_id)
        return COURSES_MANAGEMENT
    else:
        logging.warning(f"🤖 Detected student {user.username}")

        courses = {}
        for course_id, course_data in context.bot_data["courses"].items():
            if user.id in [student["id"] for student in course_data["students"]]:
                courses[course_id] = course_data

        if len(courses.keys()) == 0:
            # new student
            text = f"🤖 Добро пожаловать, {user.first_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"🙇🏼‍ Присоединиться к курсу", callback_data="join_course"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            if "start_msg_id" not in context.chat_data.keys():
                context.chat_data["start_msg_id"] = [message.message_id]
            else:
                context.chat_data["start_msg_id"].append(message.message_id)
        else:
            text = f"🖖🏻 Привет, {user.first_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"{course_data['title']}", callback_data=course_id
                )
                for course_id, course_data in courses.items()
            ]
            buttons.append(
                InlineKeyboardButton(
                    text=f"🙇🏼‍ Присоединиться к курсу", callback_data=f"join_course"
                )
            )
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            if "start_msg_id" not in context.chat_data.keys():
                context.chat_data["start_msg_id"] = [message.message_id]
            else:
                context.chat_data["start_msg_id"].append(message.message_id)
        return STUDENT_MENU


async def tests_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered tests_management handler")
    await update.callback_query.answer()
    # callback_data: "add_new_test", test_id, course_id
    callback_data = update.callback_query.data
    course_id = context.chat_data["current_course_id"]

    # await delete_messages(
    #    context=context,
    #    chat_id=update.effective_chat.id
    # )

    if callback_data == "add_new_test":
        buttons = [
            InlineKeyboardButton(
                text=f"🔙 К меню курса", callback_data=str(TESTS_MANAGEMENT)
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE если отправлен файл
        message = await update.callback_query.edit_message_text(
            text=f"📤 Загрузите YAML файл", reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return ADDING_TEST

    elif callback_data in context.bot_data["courses"].keys():
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

        course_data = context.bot_data["courses"][course_id]
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

    elif callback_data in context.bot_data["courses"][course_id]["tests"].keys():
        test_id = callback_data
        context.chat_data["current_test_id"] = test_id
        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        # test.status: "future", "active", "past"
        if test_data["status"] == "future":
            # future test branch
            buttons = [
                InlineKeyboardButton(
                    text=f"✍ Редактировать тест", callback_data=f"edit_test_{test_id}"
                ),
                InlineKeyboardButton(
                    text=f"🚀 Начать тест", callback_data=f"start_test_{test_id}"
                ),
                InlineKeyboardButton(
                    text=f"↩️ Назад к тестам", callback_data=course_id
                ),
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
            text = (
                f"🔈 Название: {test_data['title']}\n"
                f"🛎️ Статус: {test_data['status']}\n"
                f"⏱️ На размышление {test_data['time_to_solve']} минут\n"
            )
            # await delete_messages(
            #    context=context,
            #    chat_id=update.effective_chat.id
            # )
            message = await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return TEST_MANAGEMENT

        elif test_data["status"] == "active":
            # active test branch
            buttons = [
                InlineKeyboardButton(
                    text=f"⏱️ Добавить время", callback_data=f"add_extra_time_{test_id}"
                ),
                InlineKeyboardButton(
                    text=f"🏁 Завершить", callback_data=f"finalize_{test_id}"
                ),
                InlineKeyboardButton(
                    text=f"💬 Отправить сообщение",
                    callback_data=f"send_message_{test_id}",
                ),
                InlineKeyboardButton(
                    text=f"↩️ Назад к тестам", callback_data=course_id
                ),
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))

            text = (
                f"🔈 Название: {test_data['title']}\n"
                f"🛎️ Статус: {test_data['status']}\n"
                f"⏱ Начат в: {test_data['start_time']}\n"
                f"⌚️ На размышление {test_data['time_to_solve']} минут\n"
            )
            # DELETE в случае таймера завершения теста
            message = await update.callback_query.edit_message_text(
                text=text, reply_markup=keyboard
            )
            if "msg_id_active_test" not in context.chat_data.keys():
                context.chat_data["msg_id_active_test"] = [message.message_id]
            else:
                context.chat_data["msg_id_active_test"].append(message.message_id)
            return ACTIVE_TEST_MANAGEMENT

        elif test_data["status"] == "past":
            # past test branch
            buttons = [
                InlineKeyboardButton(
                    text=f"💯 Оценки", callback_data=f"scores_{test_id}"
                ),
                InlineKeyboardButton(
                    text=f"🗞️ Ответы", callback_data=f"answers_{test_id}"
                ),
                InlineKeyboardButton(
                    text=f"↩️ Назад к тестам", callback_data=course_id
                ),
                InlineKeyboardButton(
                    text=f"🔼 Загрузить оценки", callback_data=f"upload_scores_{test_id}"
                )
            ]
            # + кнопка "Проверить", если есть что проверять, то есть
            # в текущем тесте (test_id) есть вопросы с тектовым ответом
            # или ответом-файлом.
            to_grade = False
            questions = test_data["questions"]
            for student_id, student_data in test_data["scores"].items():
                for question_id, score in student_data.items():
                    if (
                        questions[question_id]["type"] != "multiple_choice"
                        and score is None
                    ):
                        to_grade = True
                        break
            if to_grade:
                buttons.append(
                    InlineKeyboardButton(
                        text=f"🪶 Проверить", callback_data=f"grade_{test_id}"
                    )
                )
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
            text = (
                f"🔈 Название: {test_data['title']}\n"
                f"🛎️ Статус: {test_data['status']}\n"
            )
            try:
                message = await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
            except:
                await delete_messages(context=context, chat_id=update.effective_chat.id)
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=text, reply_markup=keyboard
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
            return TEST_MANAGEMENT

    elif callback_data == str(TESTS_MANAGEMENT):
        tests = context.bot_data["courses"][course_id]["tests"]
        buttons = [
            InlineKeyboardButton(text=f"📃 {test_data['title']}", callback_data=test_id)
            for test_id, test_data in tests.items()
        ]
        buttons.append(
            InlineKeyboardButton(
                text=f"🆕 Добавить новый тест", callback_data="add_new_test"
            )
        )
        buttons.append(
            InlineKeyboardButton(text=f"🔙 К меню курса", callback_data=course_id)
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(
            text=f"✅ Выберите тест.", reply_markup=keyboard
        )
        return TESTS_MANAGEMENT


async def adding_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered adding_test handler")

    document = update.message.document

    if document.mime_type != "application/x-yaml":
        file_name = document.file_name
        file_extension = os.path.splitext(file_name)[1]
        logging.warning(f"🤖🤬 Not YAML Test file warning from adding_test handler")
        text = (
            f"🤬 Файл с тестом должен иметь расширение '.yml', получено '{file_extension}'.\n"
            f"Пожалуйста, загрузите YAML файл.\n"
        )
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE в случае отправки файла
        message = await update.message.reply_text(text=text)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return ADDING_TEST

    # Создание временного файла для сохранения
    temp_file_path = "temp_file_test.yml"

    # Сохранение файла на диск
    await save_document_to_disk(document, temp_file_path)

    # Чтение содержимого YAML файла
    with open(temp_file_path, "r", encoding="utf-8") as yaml_file:
        yaml_content = yaml_file.read()
    try:
        parsed_yaml = yaml.load(yaml_content, Loader=Loader)
    except yaml.YAMLError  as e:
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE в случае отправки файла
        message = await update.message.reply_text(
            "Неверный формат YAML. Пожалуйста, исправьте файл и отправьте его снова."
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        logging.warning(e)
        return ADDING_TEST
    

    os.remove(temp_file_path)

    course_id = context.chat_data["current_course_id"]
    tests = context.bot_data["courses"][course_id]["tests"]
    new_test_id = generate_unique_id(existing_ids=tests.keys())

    questions = {}
    compulsory_question_keys = ["type", "text", "score"]
    total_score = 0
    question_index = 0
    for question in parsed_yaml["questions"]:
        for comp_key in compulsory_question_keys:
            if comp_key not in question.keys():
                await delete_messages(context=context, chat_id=update.effective_chat.id)
                # DELETE в случае отправки файла
                message = await update.message.reply_text(
                    "Неверный формат YAML. Пожалуйста, исправьте файл и отправьте его снова."
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
                return ADDING_TEST

        if question['type'] not in ['text_answer', 'file_answer', 'multiple_choice']:
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            # DELETE в случае отправки файла
            message = await update.message.reply_text(
                f"Неверный формат YAML. Неизвестный тип вопроса '{question['type']}'. Пожалуйста, исправьте файл и отправьте его снова."
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return ADDING_TEST
        if question["type"] == "multiple_choice":
            question['options'] = [str(val) for val in question['options']]
            question['correct_answers'] = [str(val) for val in question['correct_answers']]
        q_id = generate_unique_id(existing_ids=questions.keys())
        questions[q_id] = question
        questions[q_id]['index'] = question_index
        question_index += 1
        total_score += float(question["score"])
        #print(f"is_markdown in keys: {'is_markdown' in question.keys()}")
        #if "is_markdown" in question.keys():
        #    print(f"question['is_markdown']: '{question['is_markdown'] }'")
        if "is_markdown" in question.keys() and (question["is_markdown"] == "true" or question["is_markdown"] == "True" or question["is_markdown"] == True):
            dir_path = f"test_{new_test_id}_questions"
            await create_directory_if_not_exists("./" + dir_path)
            md_text = question["text"]
            await md2png(md_text, dir_path, f"question_{q_id}")

    # Normalizing the scores for individual questions so that they add up to 100 points.
    normalizer = lambda question: float(question["score"]) / total_score * 100
    for question_id, question_data in questions.items():
        questions[question_id]["score"] = normalizer(question_data)

    context.bot_data["courses"][course_id]["tests"][new_test_id] = {
        "title": parsed_yaml["title"],
        "time_to_solve": float(parsed_yaml["time_to_solve"]),
        "start_time": None,
        "status": "future",
        "total_score": 100,
        "questions": questions,
        "answers": {},
        "scores": {},
        "active_data": {},
        "entered_students": [],
    }

    buttons = [
        InlineKeyboardButton(text=f"🔙 К тестам", callback_data=str(TESTS_MANAGEMENT))
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    await update.message.reply_text(
        text=f"🟢 Получены YAML данные", reply_markup=keyboard
        # text=f"🟢 Получены YAML данные: {parsed_yaml}", reply_markup=keyboard
    )

    return TESTS_MANAGEMENT


async def test_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered test_management handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("edit_test_"):
        # keyboard for EditFutureTest
        test_id = callback_data[len("edit_test_") :]

        buttons = [
            InlineKeyboardButton(
                text=f"🔉Редактировать название", callback_data=f"edit_title_{test_id}"
            ),
            InlineKeyboardButton(
                text=f"🗑️ Удалить тест", callback_data=f"remove_test_{test_id}"
            ),
            InlineKeyboardButton(
                text=f"↪️ Загрузить заново", callback_data=f"reupload_{test_id}"
            ),
            InlineKeyboardButton(text=f"↩️ Меню теста", callback_data=test_id),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        course_id = context.chat_data["current_course_id"]
        test_title = context.bot_data["courses"][course_id]["tests"][test_id]["title"]

        text = f"🔉 Название: {test_title}\n"
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return EDIT_FUTURE_TEST

    elif callback_data.startswith("start_test_"):
        moscow_tz = pytz.timezone("Europe/Moscow")
        current_time = datetime.now(moscow_tz)
        formatted_time = current_time.strftime("%H:%M:%S")

        test_id = callback_data[len("start_test_") :]
        context.bot_data[f"to_send_scores_{test_id}"] = []
        course_id = context.chat_data["current_course_id"]
        context.bot_data[f"students_{test_id}"] = []

        context.bot_data["courses"][course_id]["tests"][test_id]["status"] = "active"
        context.bot_data["courses"][course_id]["tests"][test_id][
            "start_time"
        ] = current_time

        minutes_to_solve = context.bot_data["courses"][course_id]["tests"][test_id][
            "time_to_solve"
        ]

        # таймер на завершение теста
        context.job_queue.run_once(
            callback=finalize_test_action,
            when=float(minutes_to_solve) * 60,
            name=f"timer_job_{test_id}",
            chat_id=update.effective_chat.id,
            data={"course_id": course_id, "test_to_fin_id": test_id},
        )
        buttons = [
            InlineKeyboardButton(text=f"Active test menu", callback_data=test_id)
        ]
        text = (
            f"Тест начат в {formatted_time}\n"
            f"На выполнение {minutes_to_solve} минут\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE при срабатывании таймера теста
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        if "msg_id_active_test" not in context.chat_data.keys():
            context.chat_data["msg_id_active_test"] = [message.message_id]
        else:
            context.chat_data["msg_id_active_test"].append(message.message_id)
        return TESTS_MANAGEMENT

    elif callback_data == context.chat_data["current_course_id"]:
        course_id = context.chat_data["current_course_id"]
        tests = context.bot_data["courses"][course_id]["tests"]

        buttons = [
            InlineKeyboardButton(text=f"{test_data['title']}", callback_data=test_id)
            for test_id, test_data in tests.items()
        ]
        buttons.append(
            InlineKeyboardButton(text=f"🆕 Добавить тест", callback_data="add_new_test")
        )
        buttons.append(
            InlineKeyboardButton(text=f"🔙 К меню курса", callback_data=course_id)
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(
            text=f"✅ Выберите тест.", reply_markup=keyboard
        )

        return TESTS_MANAGEMENT

    elif callback_data.startswith("scores_"):
        test_id = callback_data[len("scores_") :]
        course_id = context.chat_data["current_course_id"]

        test_data = context.bot_data["courses"][course_id]["tests"][test_id]

        text = f"📃 Тест: '{test_data['title']}'\n" f"💯 Оценки:\n"
        to_grade = False
        for student_id, student_data in test_data["scores"].items():
            total_student_score = 0
            student_name = get_student_name_by_id(
                students=context.bot_data["courses"][course_id]["students"],
                id=student_id,
            )
            assert student_name is not None
            text += f"🤓 {student_name}:\n"

            for question_id, score in student_data.items():
                question_text = context.bot_data["courses"][course_id]["tests"][
                    test_id
                ]["questions"][question_id]["text"]
                question_full_score = context.bot_data["courses"][course_id]["tests"][
                    test_id
                ]["questions"][question_id]["score"]
                if score is not None:
                    total_student_score += score
                else:
                    to_grade = True
                text += f"✅ Вопрос: '{question_text}': {score}/{question_full_score}\n"
            text += (
                f"💯 Суммарный балл: {total_student_score}/{test_data['total_score']}\n"
            )

        if to_grade:
            text += (
                f"⚠️ Тест содержит вопросы, которые не проверяются автоматически. "
                f"Некоторые из этих вопросов не были оценены преподавателем. "
                f"Баллы выше рассчитаны без учета непроверенных вопросов."
            )

        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад к тесту", callback_data=test_id)
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        message_parts_to_send = split_long_message(long_msg=text)
        for text_part in message_parts_to_send:
            if text_part == message_parts_to_send[0]:
                if len(message_parts_to_send) > 1:
                    await update.callback_query.edit_message_text(text=text_part)
                else:
                    await update.callback_query.edit_message_text(
                        text=text_part, reply_markup=keyboard
                    )
            elif text_part == message_parts_to_send[-1]:
                message = await context.bot.send_message(
                    chat_id=context.chat_data["chat_id"],
                    text=text_part,
                    reply_markup=keyboard,
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
            else:
                message = await context.bot.send_message(
                    chat_id=context.chat_data["chat_id"], text=text_part
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
        return TESTS_MANAGEMENT

    elif callback_data.startswith("grade_"):
        test_id = callback_data[len("grade_") :]

        to_grade_dict = {test_id: {}}

        course_id = context.chat_data["current_course_id"]
        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        questions = test_data["questions"]
        question_to_grade_ids = []
        for question_id, question_data in questions.items():
            if question_data["type"] != "multiple_choice":
                question_to_grade_ids.append(question_id)

        for question_id in question_to_grade_ids:
            for student_id, student_data in test_data["scores"].items():
                for st_question_id, score in student_data.items():
                    if question_id == st_question_id and score is None:
                        if question_id not in to_grade_dict[test_id].keys():
                            to_grade_dict[test_id][question_id] = {
                                student_id: test_data["answers"][student_id][question_id]
                            }
                        else:
                            to_grade_dict[test_id][question_id][student_id] = test_data["answers"][student_id][question_id]

        context.chat_data["to_grade"] = to_grade_dict

        question_to_grade_id = next(iter(to_grade_dict[test_id]))
        question_data = questions[question_to_grade_id]
        student_id = next(iter(to_grade_dict[test_id][question_to_grade_id]))
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        answer = to_grade_dict[test_id][question_to_grade_id][student_id]

        buttons = [InlineKeyboardButton(text=f"↩️ Назад", callback_data=test_id)]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # ======== DEL DEL DEL ==========#
        await delete_messages(context=context, chat_id=update.effective_chat.id)

        if question_data["type"] == "text_answer":
            text = (
                f"🤔 Вопрос: {question_data['text']}\n"
                f"🧑🏻‍🎓 Студент: {student_name}\n"
                f"👁️‍🗨️ Ответ: {answer}\n"
                f"💯 Введите оценку от 0 до {question_data['score']}\n"
            )

            if "file_answer_message_id" not in context.chat_data.keys():
                # DELETE если введено сообщение
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=text, reply_markup=keyboard
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
                context.chat_data["save_score_message_id"] = message.message_id
            else:
                # DELETE если введено сообщение
                message = await context.bot.send_message(
                    text=text,
                    chat_id=context.chat_data["chat_id"],
                    reply_markup=keyboard,
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )

        elif question_data["type"] == "file_answer":
            text = (
                f"🤔 Вопрос: {question_data['text']}\n"
                f"🧑🏻‍🎓 Студент: {student_name}\n"
                f"👁️‍🗨️ Ответ: в файле\n"
                f"💯 Введите оценку от 0 до {question_data['score']}\n"
            )

            try:
                # DELETE если введено сообщение
                message = await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=answer[0],  # aka file_id
                    caption=text,
                    reply_markup=keyboard,
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
            except:
                # DELETE если введено сообщение
                message = await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=answer[0],  # aka file_id
                    caption=text,
                    reply_markup=keyboard,
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
            context.chat_data["file_answer_message_id"] = message.message_id
        return TEST_GRADE

    elif callback_data.startswith("answers_"):
        test_id = callback_data[len("answers_") :]
        course_id = context.chat_data["current_course_id"]

        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        questions = test_data["questions"]
        answers = test_data["answers"]
        text = f"Тест: {test_data['title']}"
        buttons = []
        for student_id, student_data in answers.items():
            student_name = get_student_name_by_id(
                students=context.bot_data["courses"][course_id]["students"],
                id=student_id,
            )
            buttons.append(
                InlineKeyboardButton(
                    text=f"🧑🏻‍🎓 {student_name}", callback_data=f"{student_id}_{test_id}"
                )
            )

        buttons.append(
            InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"cancel_{test_id}")
        )
        buttons_pack = split_many_buttons(buttons)
        for i in range(len(buttons_pack)):
            buttons = buttons_pack[i]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            if i == 0:
                await update.callback_query.edit_message_text(
                    text=text, reply_markup=keyboard
                )
            else:
                message = await context.bot.send_message(
                    chat_id=context.chat_data["chat_id"],
                    text=text,
                    reply_markup=keyboard,
                )
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
        return SEND_ANSWERS

    elif callback_data.startswith("upload_scores_"):
        test_id = callback_data[len("upload_scores_"):]
        course_id = context.chat_data["current_course_id"]
        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        test_title = test_data['title']

        # TODO =========================================================
        # Сделать файл с оценками
        # Отправить сообщение с этим файлом и кнопкой

        filename = f'test_{test_id}_scores.yml'
        scores = create_scores_file(
            test_data=test_data,
            students=context.bot_data['courses'][course_id]['students'],
            filename=filename
        )

        text = f'Тест: {test_title}\n'
        """
        for student_name, student_score in scores.items():
            if student_name != 'Test':
                text += f'{student_name}: {student_score}\n'
        """
        text += f'Загрузите файл такого же формата\n'

        buttons = [
            InlineKeyboardButton(
                text='Назад', callback_data=f'cancel_{test_id}'
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )

        message = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(filename, 'rb'),
            caption=text,
            reply_markup=keyboard
        )

        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id
        )

        return UPLOAD_SCORES_TEST


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🤖 Sorry, I didn't understand that command.",
    )


mode_conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        COURSES_MANAGEMENT: [CallbackQueryHandler(courses_management)],
        COURSE_MANAGEMENT: [CallbackQueryHandler(course_management)],
        TESTS_MANAGEMENT: [CallbackQueryHandler(tests_management)],
        TEST_MANAGEMENT: [CallbackQueryHandler(test_management)],
        TEST_GRADE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, test_grade),
            CallbackQueryHandler(tests_management),
        ],
        TEST_SAVE_GRADE: [CallbackQueryHandler(test_save_grade)],
        ACTIVE_TEST_MANAGEMENT: [CallbackQueryHandler(active_test_management)],
        EDIT_FUTURE_TEST: [CallbackQueryHandler(edit_future_test)],
        ADDING_TEST: [
            MessageHandler(filters.Document.ALL, adding_test),
            CallbackQueryHandler(tests_management),
        ],
        REUPLOAD_TEST: [
            MessageHandler(filters.Document.ALL, reupload_test),
            CallbackQueryHandler(test_management),
        ],
        EDIT_TEST_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_test_title),
            CallbackQueryHandler(test_management),
        ],
        REMOVE_TEST_REQUEST: [CallbackQueryHandler(remove_test)],
        EDIT_COURSE_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_course_code),
            CallbackQueryHandler(courses_management),
        ],
        EDIT_COURSE_TITLE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_course_title),
            CallbackQueryHandler(courses_management),
        ],
        EDIT_COURSE_LINK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_course_link),
            CallbackQueryHandler(courses_management),
        ],
        SEND_MESSAGE_REQUEST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_message_request),
            CallbackQueryHandler(send_message_request),
        ],
        SEND_MESSAGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_message),
            CallbackQueryHandler(send_message),
        ],
        ADD_COURSE_LINK: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_link),
            CallbackQueryHandler(add_course_link),
        ],
        ADD_COURSE_CODE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_code),
            CallbackQueryHandler(add_course_code),
        ],
        ADD_COURSE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_course),
            CallbackQueryHandler(add_course),
        ],
        STUDENT_MENU: [CallbackQueryHandler(student_menu)],
        JOIN_COURSE_REQUEST: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, join_course_request),
            CallbackQueryHandler(join_course_request),
        ],
        UNKNOWN_COURSE_TAG: [CallbackQueryHandler(unknown_course_tag)],
        ALREADY_JOINED: [CallbackQueryHandler(already_joined)],
        UNAVAILABLE_COURSE: [CallbackQueryHandler(unavailable_course)],
        JOINED_COURSE: [CallbackQueryHandler(joined_course)],
        COURSE_MENU: [CallbackQueryHandler(course_menu)],
        TESTS_MENU: [CallbackQueryHandler(tests_menu)],
        SEND_QUESTION: [
            PollAnswerHandler(send_question),
            CallbackQueryHandler(send_question),
            MessageHandler(filters.TEXT & ~filters.COMMAND, send_question),
            MessageHandler(filters.Document.ALL, send_question),
            MessageHandler(filters.PHOTO, send_question),
        ],
        WAIT_TEST_FINISH: [CallbackQueryHandler(wait_test_finish)],
        TEST_SCORE: [CallbackQueryHandler(course_menu)],
        HWS_MANAGEMENT: [CallbackQueryHandler(hws_management)],
        HW_MANAGEMENT: [CallbackQueryHandler(hw_management)],
        HW_INFO: [CallbackQueryHandler(hw_info)],
        HW_GRADE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, hw_grade),
            CallbackQueryHandler(hw_management),
        ],
        HW_SAVE_GRADE: [CallbackQueryHandler(hw_save_grade)],
        ADD_HW_TITLE: [
            CallbackQueryHandler(add_hw_title),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_hw_title),
        ],
        ADD_DEADLINE: [
            CallbackQueryHandler(add_deadline),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_deadline),
        ],
        ADD_HW: [CallbackQueryHandler(add_hw)],
        SUBMIT_HW_REQUEST: [CallbackQueryHandler(submit_hw_request)],
        SUBMIT_HW: [
            MessageHandler(filters.Document.ALL, submit_hw),
            CallbackQueryHandler(submit_hw),
        ],
        REMOVE_COURSE_REQUEST: [CallbackQueryHandler(remove_course_request)],
        REMOVE_COURSE: [CallbackQueryHandler(remove_course)],
        SWITCH_COURSE_STATUS: [CallbackQueryHandler(courses_management)],
        SEND_ANSWERS: [CallbackQueryHandler(send_answers)],
        SENT_ANSWERS: [CallbackQueryHandler(sent_answers)],
        COURSE_STUDENTS: [CallbackQueryHandler(course_students)],
        COURSE_STUDENT: [CallbackQueryHandler(course_student)],
        KICK_STUDENT: [CallbackQueryHandler(kick_student)],
        EDIT_STUDENT_NAME: [CallbackQueryHandler(edit_student_name),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_student_name)],
        SAVE_STUDENT_NAME: [CallbackQueryHandler(save_student_name)],
        EDIT_HW_DEADLINE: [CallbackQueryHandler(edit_hw_deadline),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_hw_deadline)],
        SAVE_HW_DEADLINE: [CallbackQueryHandler(save_hw_deadline)],
        EDIT_HW_TITLE: [CallbackQueryHandler(edit_hw_title),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_hw_title)],
        SAVE_HW_TITLE: [CallbackQueryHandler(save_hw_title)],
        REMOVE_HW: [CallbackQueryHandler(remove_hw)],
        COMMENT_HW_REQUEST: [CallbackQueryHandler(comment_hw_request),
            MessageHandler(filters.TEXT & ~filters.COMMAND, comment_hw_request),
            MessageHandler(filters.Document.ALL, comment_hw_request),
            MessageHandler(filters.PHOTO, comment_hw_request)],
        SEND_HW_COMMENT: [CallbackQueryHandler(send_hw_comment)],
        HW_MENU: [CallbackQueryHandler(hw_menu)],
        HW_COMMENT: [CallbackQueryHandler(hw_comment)],
        ADD_TEACHER_NAME: [CallbackQueryHandler(courses_management),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_teacher_name)],
        ADD_TEACHER_USERNAME: [CallbackQueryHandler(add_teacher_username_bttn),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_teacher_username_msg)],
        ADD_TEACHER_ID: [CallbackQueryHandler(add_teacher_id_bttn),
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_teacher_id_msg)],
        ADD_TEACHER: [CallbackQueryHandler(add_teacher)],
        UPLOAD_SCORES_TEST: [MessageHandler(filters.Document.ALL, upload_scores_test_document),
                            CallbackQueryHandler(upload_scores_test_bttn)],
        UPLOADING_SCORES_TEST: [CallbackQueryHandler(uploading_scores_test)],
        UPLOAD_SCORES_HW: [MessageHandler(filters.Document.ALL, upload_scores_hw_document),
                            CallbackQueryHandler(upload_scores_hw_bttn)],
        UPLOADING_SCORES_HW: [CallbackQueryHandler(uploading_scores_hw)],
        DOWNLOAD_HW_SOLUTIONS: [CallbackQueryHandler(download_hw_solutions)]
    },
    fallbacks=[CommandHandler("start", start)],
    per_chat=False,  # for PollAnswerHandler(send_question) according PTBUserWarning
    name="main_conversation",
    persistent=True,
)
