from telegram.ext import ContextTypes

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document
from telegram.constants import ParseMode
import logging
import yaml
import os
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from handlers.states import *

from utils.utils import (
    build_menu,
    get_student_name_by_id,
    split_many_buttons,
    save_message,
    delete_messages,
    split_long_message,
    save_document_to_disk
)


async def send_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"🤖 Entered send_answers handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("cancel_"):
        course_id = context.chat_data["current_course_id"]
        test_id = callback_data[len("cancel_") :]
        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        buttons = [
            InlineKeyboardButton(text=f"💯 Оценки", callback_data=f"scores_{test_id}"),
            InlineKeyboardButton(text=f"🗞️ Ответы", callback_data=f"answers_{test_id}"),
            InlineKeyboardButton(text=f"↩️ Назад к тестам", callback_data=course_id),
            InlineKeyboardButton(text=f"🔼 Загрузить оценки", callback_data=f"upload_scores_{test_id}")
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
            f"🔈 Название: {test_data['title']}\n" f"🛎️ Статус: {test_data['status']}\n"
        )
        ##==========delition===========#
        # await delete_messages(
        #    context=context,
        #    chat_id=update.effective_chat.id
        # )
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        # save_message(
        #    bot_data=context.bot_data,
        #    chat_id=update.effective_chat.id,
        #    message_id=message.message_id
        # )
        return TEST_MANAGEMENT
    else:
        student_id, test_id = callback_data.split("_")
        student_id = int(student_id)
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        test_data = course_data["tests"][test_id]
        questions = test_data["questions"]
        student_name = get_student_name_by_id(
            students=course_data["students"], id=student_id
        )
        text = f"📃 Тест: {test_data['title']}\n" f"🧑🏻‍🎓 Студент: {student_name}\n"

        # is_file_answers = False
        # file_ids = []
        for question_id, student_answers in test_data["answers"][student_id].items():
            question_data = questions[question_id]
            text += f"❓ Вопрос: {question_data['text']}\n"
            if (
                question_data["type"] == "multiple_choice"
                or question_data["type"] == "text_answer"
            ):
                answer_str = ""
                for ans in student_answers:
                    if ans == student_answers[-1]:
                        answer_str += f"{ans}."
                    else:
                        answer_str += f"{ans}, "
                text += f"🗿 Ответ: {answer_str}\n"
            else:
                file_id = student_answers[0]
                file_info = await context.bot.get_file(file_id)
                file_path = file_info.file_path
                file_name = file_info.file_path.split("/")[-1]
                text += f"🗿 Ответ: <a href='{file_path}'>{file_name}</a>\n"

        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"cancel_{test_id}")
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard, parse_mode=ParseMode.HTML
        )
        return SENT_ANSWERS


async def sent_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"🤖 Entered sent_answers handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("cancel_"):
        test_id = callback_data[len("cancel_") :]
        course_id = context.chat_data["current_course_id"]

        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
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


async def test_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered test_grade handler")
    entered_score = None
    message = update.message.text
    try:
        entered_score = float(message)
    except:
        pass
    test_id = context.chat_data["current_test_id"]
    question_to_grade_id = next(iter(context.chat_data["to_grade"][test_id]))
    student_id = next(
        iter(context.chat_data["to_grade"][test_id][question_to_grade_id])
    )
    course_id = context.chat_data["current_course_id"]

    test_data = context.bot_data["courses"][course_id]["tests"][test_id]
    questions = test_data["questions"]
    question_data = questions[question_to_grade_id]

    student_name = get_student_name_by_id(
        students=context.bot_data["courses"][course_id]["students"], id=student_id
    )
    answer = context.chat_data["to_grade"][test_id][question_to_grade_id][student_id]

    if entered_score is None:
        text = f"⚠️ Невозможно преобразовать в число {message}. Оценка должна быть числом. Пожалуйста, попробуйте еще раз.\n"
        buttons = [InlineKeyboardButton(text=f"↩️ Назад", callback_data=test_id)]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        if question_data["type"] == "text_answer":
            text += (
                f"🤔 Вопрос: {question_data['text']}\n"
                f"🧑🏻‍🎓 Студент: {student_name}\n"
                f"👁️‍🗨️ Ответ: {answer}\n"
                f"💯 Введите оценку от 0 до {question_data['score']}\n"
            )
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            # DELETE если введено сообщение
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
        elif question_data["type"] == "file_answer":
            text += (
                f"🤔 Вопрос: {question_data['text']}\n"
                f"🧑🏻‍🎓 Студент: {student_name}\n"
                f"👁️‍🗨️ Ответ: в файле\n"
                f"💯 Введите оценку от 0 до {question_data['score']}\n"
            )
            await delete_messages(context=context, chat_id=update.effective_chat.id)
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

    buttons = [
        InlineKeyboardButton(
            text=f"✅ Сохранить", callback_data=f"save_{entered_score}"
        ),
        InlineKeyboardButton(text=f"↩️ Назад", callback_data=test_id),
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    if question_data["type"] == "text_answer":
        text = (
            f"🤔 Вопрос: {question_data['text']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"👁️‍🗨️ Ответ: {answer}\n"
            f"💯 Оценка: {entered_score}\n"
        )
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE за ним может следовать файл
        message = await update.message.reply_text(text=text, reply_markup=keyboard)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        context.chat_data["save_score_message_id"] = message.message_id
    elif question_data["type"] == "file_answer":
        text = (
            f"🤔 Вопрос: {question_data['text']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"👁️‍🗨️ Ответ: в файле\n"
            f"💯 Оценка: {entered_score}\n"
        )
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        try:
            # DELETE за ним может следовать файл
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
            # DELETE за ним может следовать файл
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
    return TEST_SAVE_GRADE


async def test_save_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered test_save_grade handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    course_id = context.chat_data["current_course_id"]
    test_id = context.chat_data["current_test_id"]

    if callback_data.startswith("save_"):
        score = float(callback_data[len("save_") :])
        question_to_grade_id = next(iter(context.chat_data["to_grade"][test_id]))
        student_id = next(
            iter(context.chat_data["to_grade"][test_id][question_to_grade_id])
        )
        context.bot_data["courses"][course_id]["tests"][test_id]["scores"][student_id][
            question_to_grade_id
        ] = score

    # обновляем context.chat_data["to_grade"]
    to_grade_dict = {test_id: {}}
    test_data = context.bot_data["courses"][course_id]["tests"][test_id]
    questions = test_data["questions"]
    question_to_grade_ids = []
    for question_id, question_data in questions.items():
        if question_data["type"] != "multiple_choice":
            for student_id, student_data in test_data["scores"].items():
                if (
                    question_id in student_data.keys()
                    and student_data[question_id] is None
                ):
                    if question_id not in question_to_grade_ids:
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
                        to_grade_dict[test_id][question_id][student_id] = test_data[
                            "answers"
                        ][student_id][question_id]

    context.chat_data["to_grade"] = to_grade_dict

    buttons = [InlineKeyboardButton(text=f"↩️ Назад", callback_data=test_id)]

    # ======== DEL is here =========#
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    if len(question_to_grade_ids) > 0:
        question_to_grade_id = next(iter(to_grade_dict[test_id]))
        question_data = questions[question_to_grade_id]
        student_id = next(iter(to_grade_dict[test_id][question_to_grade_id]))
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        answer = to_grade_dict[test_id][question_to_grade_id][student_id]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
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
                msg_to_del_id = context.chat_data.pop("save_score_message_id", None)
                if msg_to_del_id:
                    await context.bot.delete_message(
                        chat_id=context.chat_data["chat_id"], message_id=msg_to_del_id
                    )
                message_id = context.chat_data.pop("file_answer_message_id")
                # DELETE если введено сообщение
                message = await context.bot.send_message(
                    text=text,
                    chat_id=context.chat_data["chat_id"],
                    # message_id=message_id,
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

    else:
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
                    message = await context.bot.send_message(
                        chat_id=update.effective_chat.id, text=text_part
                    )
                    save_message(
                        bot_data=context.bot_data,
                        chat_id=update.effective_chat.id,
                        message_id=message.message_id,
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=text_part,
                        reply_markup=keyboard,
                    )
                    save_message(
                        bot_data=context.bot_data,
                        chat_id=update.effective_chat.id,
                        message_id=message.message_id,
                    )
            elif text_part == message_parts_to_send[-1]:
                message = await context.bot.send_message(
                    chat_id=context.chat_data["chat_id"],
                    text=text_part,
                    reply_markup=keyboard,
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


async def upload_scores_test_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered upload_scores_test_document handler")

    if update.message and update.message.document:
        document = update.message.document
        file_extension = document.file_name.split('.')[-1].lower()
        test_id = context.chat_data['current_test_id']
        buttons = [
            InlineKeyboardButton(
                text='Назад', callback_data=f'cancel_{test_id}'
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        if file_extension != "yml":
            file_name = document.file_name
            text = (
                    f"🤬 Файл с оценками должен иметь расширение '.yml', получено '{file_extension}'.\n"
                    f"Пожалуйста, загрузите YAML файл.\n"
                )
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return UPLOAD_SCORES_TEST

        temp_file_path = f"new_scores_test_{test_id}.yml"
        await save_document_to_disk(document, temp_file_path)
        try:
            with open(temp_file_path, 'r') as file:
                yaml_content = yaml.load(file, Loader=Loader)

            if isinstance(yaml_content, dict):
                for key, value in yaml_content.items():
                    if key == 'Test':
                        continue
                    try:
                        [float(score) for score in value]
                    except ValueError:
                        # оценка не число. Коллапс!
                        text = f'❌ Файл не соответствует формату. Пара \'{key}\' : \'{value}\' не удовлетворяет формату.\n'\
                                f'❗️Файл должен содержать словарь, ключи которого -- имена студентов (строки),'\
                                f'а значения -- массивы оценок (list[float]). Исключением является только пара с ключом \'Test\', значение по этому ключу должно быть строкой.'\
                                f'Пожалуйста, проверьте корректность файла и загрузите его еще раз.'
                        if os.path.exists(temp_file_path):
                            os.remove(temp_file_path)
                        await delete_messages(context=context, chat_id=update.effective_chat.id)
                        message = await update.message.reply_text(text=text, reply_markup=keyboard)
                        save_message(
                            bot_data=context.bot_data,
                            chat_id=update.effective_chat.id,
                            message_id=message.message_id,
                        )
                        return UPLOAD_SCORES_TEST
            else:
                text = f'❌ Файл не соответствует формату. Файл должен содержать словарь, ключи которого -- имена студентов (строки),'\
                        f'а значения -- массивы оценок (list[float]). Исключением является только пара с ключом \'Test\', значение по этому ключу должно быть строкой.'\
                        f'Пожалуйста, проверьте корректность файла и загрузите его еще раз.'
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                await delete_messages(context=context, chat_id=update.effective_chat.id)
                message = await update.message.reply_text(text=text, reply_markup=keyboard)
                save_message(
                    bot_data=context.bot_data,
                    chat_id=update.effective_chat.id,
                    message_id=message.message_id,
                )
                return UPLOAD_SCORES_TEST
        except Exception as e:
            text = f'⭕️❌ Ошибка при чтении файла: {e}.🤷🏻‍♂️\nПопробуйте еще раз.'
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return UPLOAD_SCORES_TEST
    
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    course_id = context.chat_data["current_course_id"]
    course_data = context.bot_data['courses'][course_id]
    test_id = context.chat_data["current_test_id"]
    test_data = course_data['tests'][test_id]
    scores_id = {}
    for student_name, student_score in yaml_content.items():
        if student_name == 'Test':
            continue
        student_id = None
        for student in context.bot_data['courses'][course_id]['students']:
            if student_name == student['name']:
                student_id = student['id']
                break
        
        if not student_id:
            # Студента с таким именем нет на курсе
            text = f'❌ Студента с именем \'{student_name}\' нет в этом курсе, добавление оценки невозможно.'\
                    f'Пожалуйста, проверьте корректность файла и попробуйте снова.'
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            message = await update.message.reply_text(text=text, reply_markup=keyboard)
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return UPLOAD_SCORES_TEST
        
        scores_id[student_id] = student_score
    
    for student_id, student_scores in scores_id.items():
        for index in range(len(student_scores)):
            q_id = [q_id for q_id, q_data in test_data['questions'].items() if q_data['index'] == index][0]
            if student_id in context.bot_data['courses'][course_id]['tests'][test_id]['scores'].keys():
                if context.bot_data['courses'][course_id]['tests'][test_id]['scores'][student_id]:
                    context.bot_data['courses'][course_id]['tests'][test_id]['scores'][student_id][q_id] = student_scores[index]
                else:
                    context.bot_data['courses'][course_id]['tests'][test_id]['scores'][student_id] = {
                        q_id: student_scores[index]
                    }
            else:
                context.bot_data['courses'][course_id]['tests'][test_id]['scores'][student_id] = {
                    q_id: student_scores[index]
                }

    new_scores_name = {}

    context.bot_data['courses'][course_id]['tests'][test_id]['status'] = 'past'

    course_data = context.bot_data['courses'][course_id]
    test_data = course_data['tests'][test_id]
    
    for student_id, student_data in test_data['scores'].items():
        total_score = 0
        for q_id, q_score in student_data.items():
            if q_score:
                total_score += float(q_score)
        
        student_name = "Unknown"
        for student in course_data['students']:
            if student_id == student['id']:
                student_name = student['name']
                break
        
        new_scores_name[student_name] = total_score
    
    text = f'Тест: {test_data["title"]}\n'\
            f'Текущие оценки:\n'
    
    for name, score in new_scores_name.items():
        text += f'{name}: {score}\n'
    
    buttons = [
        InlineKeyboardButton(
            text=f'✅Ok', callback_data=f'ok_{test_id}'
        )
    ]

    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

    await delete_messages(
        context=context,
        chat_id=update.effective_chat.id
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=keyboard
    )

    return UPLOADING_SCORES_TEST


async def upload_scores_test_bttn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered upload_scores_test_bttn handler")
    # нажатие кнопки 'Назад'
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    test_id = callback_data[len("cancel_"):]
    context.chat_data["current_test_id"] = test_id
    course_id = context.chat_data["current_course_id"]
    test_data = context.bot_data["courses"][course_id]["tests"][test_id]
    # test.status: "future", "active", "past"
    if test_data["status"] == "past":
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
            InlineKeyboardButton(
                text=f"🔼 Загрузить оценки", callback_data=f"upload_scores_{test_id}"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        text = (
            f"🔈 Название: {test_data['title']}\n"
            f"🛎️ Статус: {test_data['status']}\n"
            f"⏱️ На размышление {test_data['time_to_solve']} минут\n"
        )
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
            message_id=message.message_id,
        )
        return TEST_MANAGEMENT


async def uploading_scores_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered uploading_scores_test handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data
    test_id = callback_data[len("ok_"):]
    context.chat_data["current_test_id"] = test_id
    course_id = context.chat_data["current_course_id"]
    test_data = context.bot_data["courses"][course_id]["tests"][test_id]
    # test.status: "future", "active", "past"
    if test_data["status"] == "past":
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
            InlineKeyboardButton(
                text=f"🔼 Загрузить оценки", callback_data=f"upload_scores_{test_id}"
            )
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
