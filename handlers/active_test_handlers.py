from telegram.ext import ContextTypes

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document

import logging
import pytz
from datetime import datetime, timedelta
import os
import shutil

from handlers.states import *
from utils.utils import (
    build_menu,
    remove_job_if_exists,
    save_message,
    delete_messages,
    get_student_name_by_id,
)


async def active_test_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered active_test_management handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("add_extra_time_"):
        test_id = context.chat_data["current_test_id"]
        course_id = context.chat_data["current_course_id"]
        # удаляем старый таймер
        job_name = f"timer_job_{test_id}"
        current_jobs = context.job_queue.get_jobs_by_name(job_name)
        if current_jobs:
            for job in current_jobs:
                job.schedule_removal()

        # считаем, сколько времени осталось
        moscow_tz = pytz.timezone("Europe/Moscow")
        current_date = datetime.now(moscow_tz).date()
        test_start_time = context.bot_data["courses"][course_id]["tests"][test_id][
            "start_time"
        ].time()
        test_start = moscow_tz.localize(datetime.combine(current_date, test_start_time))
        time_to_solve = context.bot_data["courses"][course_id]["tests"][test_id][
            "time_to_solve"
        ]
        new_finish_time = test_start + timedelta(minutes=time_to_solve + 1)
        current_time = datetime.now(moscow_tz)
        time_difference = new_finish_time - current_time
        due = time_difference.total_seconds()

        # заводим новый таймер
        context.job_queue.run_once(
            callback=finalize_test_action,
            when=due,
            name=f"timer_job_{test_id}",
            chat_id=update.effective_chat.id,
            data={"course_id": course_id, "test_to_fin_id": test_id},
        )

        context.bot_data["courses"][course_id]["tests"][test_id]["time_to_solve"] += 1
        text = f"👽 Добавлена 1 минута на выполнение"
        buttons = [InlineKeyboardButton(text=f"↩️ К меню теста", callback_data=test_id)]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE в случае таймера завершения теста
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )

        if "msg_id_active_test" not in context.chat_data.keys():
            context.chat_data["msg_id_active_test"] = [message.message_id]
        else:
            context.chat_data["msg_id_active_test"].append(message.message_id)

        return TESTS_MANAGEMENT

    elif callback_data.startswith("finalize_"):
        if "msg_id_active_test" in context.chat_data.keys():
            context.chat_data.pop("msg_id_active_test")

        course_id = context.chat_data["current_course_id"]
        test_id = context.chat_data["current_test_id"]

        context.bot_data["courses"][course_id]["tests"][test_id]["status"] = "past"

        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        questions = test_data["questions"]

        is_for_teacher_check = False
        for student_id, student_data in test_data["answers"].items():
            for question_id, student_answers in student_data.items():
                if questions[question_id]["type"] == "multiple_choice":
                    question_score = 0
                    if set(student_answers) == set(
                        questions[question_id]["correct_answers"]
                    ):
                        question_score = questions[question_id]["score"]
                    if (
                        student_id
                        not in context.bot_data["courses"][course_id]["tests"][test_id][
                            "scores"
                        ].keys()
                    ):
                        context.bot_data["courses"][course_id]["tests"][test_id][
                            "scores"
                        ][student_id] = {question_id: question_score}
                    else:
                        context.bot_data["courses"][course_id]["tests"][test_id][
                            "scores"
                        ][student_id][question_id] = question_score
                else:
                    is_for_teacher_check = True
                    if (
                        student_id
                        not in context.bot_data["courses"][course_id]["tests"][test_id][
                            "scores"
                        ].keys()
                    ):
                        context.bot_data["courses"][course_id]["tests"][test_id][
                            "scores"
                        ][student_id] = {question_id: None}
                    else:
                        context.bot_data["courses"][course_id]["tests"][test_id][
                            "scores"
                        ][student_id][question_id] = None

        # удалить таймер!
        remove_job_if_exists(name=f"timer_job_{test_id}", context=context)

        # отправить оценки студентам, писавшим тест
        students_ids = context.bot_data.pop(f"students_{test_id}")
        students_ids = [
            student_id
            for student_id in students_ids
            if student_id in context.bot_data[f"to_send_scores_{test_id}"]
        ]
        scores = context.bot_data["courses"][course_id]["tests"][test_id]["scores"]
        answers = context.bot_data["courses"][course_id]["tests"][test_id]["answers"]
        for student_id in students_ids:
            # if student_id in answers.keys():
            total_student_score = 0

            if student_id in scores.keys():
                for question_id, score in scores[student_id].items():
                    if score is not None:
                        total_student_score += score

            incorrect_answers = {}
            if student_id in answers.keys():
                for question_id, student_answers in answers[student_id].items():
                    if questions[question_id]["type"] == "multiple_choice":
                        if set(questions[question_id]["correct_answers"]) != set(
                            student_answers
                        ):
                            incorrect_answers[question_id] = student_answers
                    elif (
                        scores[student_id][question_id] is not None
                        and scores[student_id][question_id]
                        < questions[question_id]["score"]
                    ):
                        incorrect_answers[question_id] = student_answers
            unanswered_questions_ids = []
            for question_id in questions.keys():
                if student_id not in answers.keys():
                    unanswered_questions_ids.append(question_id)
                elif question_id not in answers[student_id].keys():
                    unanswered_questions_ids.append(question_id)
            text = f""
            if is_for_teacher_check:
                text += (
                    f"🚸 Тест содержит вопросы, ответы на которые не проверяются автоматически."
                    f"Ниже приведена оценка, полученная с учетом только тех вопросов, которые не"
                    f"требуют проверки преподавателем. Дождитесь проверки остальных вопросов,"
                    f" чтобы увидеть релевантную оценку."
                )
            text += f"<b>Оценка: {total_student_score}/{test_data['total_score']}</b>\n"
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
                if len(unanswered_questions_ids) > 0:
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
                    text=f"↩️ Назад к тестам", callback_data=str(TESTS_MANAGEMENT)
                )
            ]
            # удалить опросик у студика
            active_data = None
            if course_id in context.bot_data["courses"].keys() \
                and test_id in context.bot_data["courses"][course_id]["tests"].keys() \
                and student_id in context.bot_data["courses"][course_id]["tests"][test_id]["active_data"].keys():
                active_data = context.bot_data["courses"][course_id]["tests"][test_id][
                    "active_data"
                ][student_id]
            if active_data:
                try:
                    # удалить предыдущую пару сообщение+тест, если есть
                    await context.bot.delete_message(
                        chat_id=active_data["chat_id"], 
                        message_id=active_data["message_id"]
                    )
                except:
                    pass
                try:
                    # удаляем опрос, на который студик уже ответил
                    await context.bot.delete_message(
                        chat_id=active_data["chat_id"],
                        message_id=active_data["poll_message_id"],
                    )
                    context.bot_data["courses"][course_id]["tests"][test_id][
                        "active_data"
                    ] = {}
                except:
                    pass
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            await context.bot.send_message(
                chat_id=int(student_id),
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

        text = f"🏁 Тест '{test_data['title']}' завершен."
        buttons = [InlineKeyboardButton(text=f"🏴‍Меню теста", callback_data=test_id)]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        # удалить картинки вопросов, если есть
        if os.path.exists(f"./test_{test_id}_questions"):
            shutil.rmtree(f"test_{test_id}_questions")
        return TESTS_MANAGEMENT

    elif callback_data.startswith("send_message_"):
        test_id = context.chat_data["current_test_id"]
        text = f"💬 Введите сообщение:"
        # DELETE если введено сообщение
        message = await update.callback_query.edit_message_text(text=text)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return SEND_MESSAGE_REQUEST
    else:
        # Back to tests button
        if "msg_id_active_test" in context.chat_data.keys():
            context.chat_data.pop("msg_id_active_test")

        course_id = callback_data
        tests = context.bot_data["courses"][course_id]["tests"]
        buttons = [
            InlineKeyboardButton(text=f"📃 {test_data['title']}", callback_data=test_id)
            for test_id, test_data in tests.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"🆕 Добавить новый тест", callback_data="add_new_test"
            ),
            InlineKeyboardButton(text=f"↩️ К меню курса", callback_data=course_id),
        ]
        text = f"✅ Выберите тест."
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return TESTS_MANAGEMENT


async def send_message_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered send_message_request handler")
    message = update.message.text

    text = f"💬 Сообщение: '{message}'"
    buttons = [
        InlineKeyboardButton(text=f"📨 Отправить", callback_data=f"send_{message}"),
        InlineKeyboardButton(text=f"✍🏻 Редактировать", callback_data="edit"),
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    await update.message.reply_text(text=text, reply_markup=keyboard)
    return SEND_MESSAGE


async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered send_message handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("send_"):
        message = callback_data[len("send_") :]
        # sending...
        test_id = context.chat_data["current_test_id"]
        if f"students_{test_id}" in context.bot_data.keys():
            for student_id in context.bot_data[f"students_{test_id}"]:
                await context.bot.send_message(chat_id=int(student_id), text=message)
        else:
            logging.warning(f"😾 There are no students writing this test.")
        # keyboard to process in active_test_management
        course_id = context.chat_data["current_course_id"]
        buttons = [
            InlineKeyboardButton(
                text=f"⏱️ Добавить время", callback_data=f"add_extra_time_{test_id}"
            ),
            InlineKeyboardButton(
                text=f"🏁 Завершить", callback_data=f"finalize_{test_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Отправить сообщение", callback_data=f"send_message_{test_id}"
            ),
            InlineKeyboardButton(text=f"↩️ Назад к тестам", callback_data=course_id),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))

        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        time_to_solve = test_data["time_to_solve"]
        start_time = test_data["start_time"].time()

        text = (
            f"🔈 Название: {test_data['title']}\n"
            f"🛎️ Статус: {test_data['status']}\n"
            f"⏱ Начат в: {start_time}\n"
            f"⌚️ На размышление {time_to_solve} минут\n"
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
    elif callback_data == "edit":
        text = f"💬 Введите сообщение:"
        # DELETE если введено сообщение
        message = await update.callback_query.edit_message_text(text=text)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return SEND_MESSAGE_REQUEST


async def finalize_test_action(context: ContextTypes.DEFAULT_TYPE):
    """
    Завершает текущий тест. Делает то же самое, что и при нажатии Finalize, только
    по таймеру.
    """
    logging.warning(f"⏰ finalize_test_action function")

    test_to_fin_id = context.job.data["test_to_fin_id"]
    course_id = context.job.data["course_id"]

    students_ids = context.bot_data.pop(f"students_{test_to_fin_id}")

    context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["status"] = "past"

    test_data = context.bot_data["courses"][course_id]["tests"][test_to_fin_id]
    questions = test_data["questions"]

    is_for_teacher_check = False
    for student_id, student_data in test_data["answers"].items():
        for question_id, student_answers in student_data.items():
            if questions[question_id]["type"] == "multiple_choice":
                question_score = 0
                if set(student_answers) == set(questions[question_id]["correct_answers"]):
                    question_score = questions[question_id]["score"]
                if (student_id not in context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"].keys()):
                    context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"][student_id] = {question_id: question_score}
                else:
                    context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"][student_id][question_id] = question_score
            else:
                is_for_teacher_check = True
                if (student_id not in context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"].keys()):
                    context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"][student_id] = {question_id: None}
                else:
                    context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"][student_id][question_id] = None
    text = f"Тест '{test_data['title']}' завершен."

    # отправить оценки студентам, писавшим тест
    scores = context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["scores"]
    answers = context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["answers"]
    students_ids = [
        student_id
        for student_id in students_ids
        if student_id in context.bot_data[f"to_send_scores_{test_to_fin_id}"]
    ]
    for student_id in students_ids:
        # if student_id in answers.keys():
        total_student_score = 0

        if student_id in scores.keys():
            for question_id, score in scores[student_id].items():
                if score is not None:
                    total_student_score += score

        incorrect_answers = {}
        if student_id in answers.keys():
            for question_id, student_answers in answers[student_id].items():
                if questions[question_id]["type"] == "multiple_choice":
                    if set(questions[question_id]["correct_answers"]) != set(
                        student_answers
                    ):
                        incorrect_answers[question_id] = student_answers
                elif (
                    scores[student_id][question_id] is not None
                    and scores[student_id][question_id]
                    < questions[question_id]["score"]
                ):
                    incorrect_answers[question_id] = student_answers
        unanswered_questions_ids = []
        for question_id in questions.keys():
            if student_id not in answers.keys():
                unanswered_questions_ids.append(question_id)
            elif question_id not in answers[student_id].keys():
                unanswered_questions_ids.append(question_id)
        text = f""
        if is_for_teacher_check:
            text += (
                f"🚸 Тест содержит вопросы, ответы на которые не проверяются автоматически."
                f"Ниже приведена оценка, полученная с учетом только тех вопросов, которые не"
                f"требуют проверки преподавателем. Дождитесь проверки остальных вопросов,"
                f" чтобы увидеть релевантную оценку.\n"
            )
        text += f"<b>Оценка: {total_student_score}/{test_data['total_score']}</b>\n"
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
            if len(unanswered_questions_ids) > 0:
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
        elif len(unanswered_questions_ids) == 0:
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
                text=f"↩️ Назад к тестам", callback_data=str(TESTS_MANAGEMENT)
            )
        ]
        try:
            # удалить предыдущую пару сообщение+тест, если есть

            active_data = context.bot_data["courses"][course_id]["tests"][
                test_to_fin_id
            ]["active_data"][student_id]
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

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await context.bot.send_message(
            chat_id=int(student_id), text=text, reply_markup=keyboard, parse_mode="HTML"
        )

    context.bot_data["courses"][course_id]["tests"][test_to_fin_id]["active_data"] = {}
    # отправить препу меню завершенного теста
    text = f"Тест: '{test_data['title']}'\n" f"Оценки:\n"
    to_grade = False
    for student_id, student_data in test_data["scores"].items():
        total_student_score = 0
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        assert student_name is not None
        text += f"🤓 {student_name}:\n"
        for question_id, score in student_data.items():
            question_text = context.bot_data["courses"][course_id]["tests"][
                test_to_fin_id
            ]["questions"][question_id]["text"]
            question_full_score = context.bot_data["courses"][course_id]["tests"][
                test_to_fin_id
            ]["questions"][question_id]["score"]
            if score is not None:
                total_student_score += score
            else:
                to_grade = True
            text += f"✅ Вопрос: '{question_text}': {score}/{question_full_score}\n"
        text += f"💯 Суммарный балл: {total_student_score}/{test_data['total_score']}\n"

    if to_grade:
        text += (
            f"⚠️ Тест содержит вопросы, которые не проверяются автоматически. "
            f"Некоторые из этих вопросов не были оценены преподавателем. "
            f"Баллы выше рассчитаны без учета непроверенных вопросов."
        )

    buttons = [
        InlineKeyboardButton(text=f"↩️ Меню теста", callback_data=test_to_fin_id)
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    # await delete_messages(
    #    context=context,
    #    chat_id=context.chat_data["chat_id"]
    # )
    send_msg = False
    if "msg_id_active_test" in context.chat_data.keys():
        send_msg = True
        for msg_id in context.chat_data["msg_id_active_test"]:
            try:
                await context.bot.delete_message(
                    chat_id=context.chat_data["chat_id"], message_id=msg_id
                )
            except:
                pass
        context.chat_data.pop("msg_id_active_test")

    if send_msg:
        await context.bot.send_message(
            chat_id=context.chat_data["chat_id"], text=text, reply_markup=keyboard
        )
        return TESTS_MANAGEMENT

    # удалить картинки вопросов, если есть
    if os.path.exists(f"./test_{test_to_fin_id}_questions"):
        shutil.rmtree(f"test_{test_to_fin_id}_questions")
