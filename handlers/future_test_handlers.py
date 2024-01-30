from telegram.ext import ContextTypes

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document

import logging
import os
import json
import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from handlers.states import *

from utils.utils import (
    build_menu,
    save_message,
    delete_messages,
    generate_unique_id,
    create_directory_if_not_exists,
    md2png,
    save_document_to_disk,
)


async def edit_future_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_future_test handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("edit_title_"):
        test_id = callback_data[len("edit_title_") :]
        text = f"💬 Введите новое название теста:"
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена", callback_data=f"edit_test_{test_id}"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE если введено сообщение
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return EDIT_TEST_TITLE
    # ===================================================
    elif callback_data.startswith("remove_test_"):
        test_id = callback_data[len("remove_test_") :]
        course_id = context.chat_data["current_course_id"]
        test_title = context.bot_data["courses"][course_id]["tests"][test_id]["title"]
        text = f"Вы действительно хотите удалить тест '{test_title}'?"
        buttons = [
            InlineKeyboardButton(text=f"👍 Да", callback_data=f"yes_{test_id}"),
            InlineKeyboardButton(text=f"👎 Нет", callback_data=f"no_{test_id}"),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return REMOVE_TEST_REQUEST
    # ===================================================
    elif callback_data.startswith("reupload_"):
        test_id = callback_data[len("reupload_") :]
        text = f"📤 Загрузите новый YAML файл:"
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена", callback_data=f"edit_test_{test_id}"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE если загружен файл
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return REUPLOAD_TEST

    else:
        # костыль для кнопки InlineKeyboardButton(
        #        text=f"Back to test",
        #        callback_data=test_tag
        #    )
        test_id = callback_data
        course_id = context.chat_data["current_course_id"]
        test_data = context.bot_data["courses"][course_id]["tests"][test_id]
        buttons = [
            InlineKeyboardButton(
                text=f"✍🏻 Редактировать тест", callback_data=f"edit_test_{test_id}"
            ),
            InlineKeyboardButton(
                text=f"🚀 Начать тест", callback_data=f"start_test_{test_id}"
            ),
            InlineKeyboardButton(text=f"↩️ Назад к тестам", callback_data=course_id),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        text = (
            f"🔈 Название: {test_data['title']}\n" f"🛎️ Статус: {test_data['status']}\n"
        )
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return TEST_MANAGEMENT


async def edit_test_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_test_title handler")
    new_test_title = update.message.text
    test_id = context.chat_data["current_test_id"]
    course_id = context.chat_data["current_course_id"]

    context.bot_data["courses"][course_id]["tests"][test_id]["title"] = new_test_title
    buttons = [
        InlineKeyboardButton(
            text=f"↩️ К меню теста", callback_data=f"edit_test_{test_id}"
        )
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    await update.message.reply_text(
        text=f"👍 Название теста изменено на {new_test_title}", reply_markup=keyboard
    )
    return TEST_MANAGEMENT


async def remove_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered remove_test handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("yes_"):
        test_id = callback_data[len("yes_") :]
        _ = context.chat_data.pop("current_test_id")
        course_id = context.chat_data["current_course_id"]

        removed_test_data = context.bot_data["courses"][course_id]["tests"].pop(test_id)

        text = f"✅ Тест '{removed_test_data['title']}' успешно удален."
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Назад к тестам", callback_data=str(TESTS_MANAGEMENT)
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return TESTS_MANAGEMENT

    elif callback_data.startswith("no_"):
        test_id = callback_data[len("no_") :]
        course_id = context.chat_data["current_course_id"]
        test_title = context.bot_data["courses"][course_id]["tests"][test_id]["title"]
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
        text = f"🔉 Название: {test_title}\n"
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return EDIT_FUTURE_TEST


async def reupload_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered reupload_test handler")
    document = update.message.document
    test_to_update_id = context.chat_data["current_test_id"]

    await delete_messages(context=context, chat_id=update.effective_chat.id)
    if document.mime_type != "application/x-yaml":
        file_name = document.file_name
        file_extension = os.path.splitext(file_name)[1]
        text = f"🤬 Файл с тестом должен иметь расширение '.yml', получено '{file_extension}'"
        # DELETE если загружен файл
        message = await update.message.reply_text(text=text)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return REUPLOAD_TEST

    # Создание временного файла для сохранения
    temp_file_path = "temp_file_test.yml"

    # Сохранение файла на диск
    await save_document_to_disk(document, temp_file_path)

    # Чтение содержимого YAML файла
    with open(temp_file_path, "r", encoding="utf-8") as yaml_file:
        yaml_content = yaml_file.read()
    try:
        parsed_yaml = yaml.load(yaml_content, Loader=Loader)
    except yaml.YAMLError:
        await update.message.reply_text("Неверный формат YAML файла")

    os.remove(temp_file_path)

    course_id = context.chat_data["current_course_id"]
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
                return REUPLOAD_TEST

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
            return REUPLOAD_TEST
        q_id = generate_unique_id(existing_ids=questions.keys())
        questions[q_id] = question
        questions[q_id]['index'] = question_index
        question_index += 1
        total_score += float(question["score"])

        if "is_markdown" in question.keys() and (question["is_markdown"] == "true" or question["is_markdown"] == "True" or question["is_markdown"] == True):
            dir_path = f"test_{test_to_update_id}_questions"
            await create_directory_if_not_exists("./" + dir_path)
            md_text = question["text"]
            await md2png(md_text, dir_path, f"question_{q_id}")

    # Normalizing the scores for individual questions so that they add up to 100 points.
    normalizer = lambda question: float(question["score"]) / total_score * 100
    for question_id, question_data in questions.items():
        questions[question_id]["score"] = normalizer(question_data)

    context.bot_data["courses"][course_id]["tests"][test_to_update_id] = {
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
        InlineKeyboardButton(
            text=f"↩️ К меню теста", callback_data=f"edit_test_{test_to_update_id}"
        )
    ]

    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await update.message.reply_text(
        text=f"Получены YAML данные: {parsed_yaml}", reply_markup=keyboard
    )
    return TEST_MANAGEMENT

