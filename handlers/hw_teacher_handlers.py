from telegram.ext import ContextTypes

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document
import logging
import os
import yaml
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from handlers.states import *
from utils.utils import (
    save_message,
    delete_messages,
    build_menu,
    get_student_name_by_id,
    generate_unique_id,
    create_scores_file_hw,
    save_document_to_disk,
    prepare_hw_solutions
)

from datetime import datetime, timedelta
import pytz


async def hws_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered hws_management handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("hw_"):
        current_hw_id = callback_data[len("hw_") :]
        context.chat_data["current_hw_id"] = current_hw_id

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            ),
            InlineKeyboardButton(
                text=f"🔼 Загрузить оценки",
                callback_data=f"upload_scores_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"⬇️ Скачать решения",
                callback_data=f"download_solutions_{current_hw_id}"
            )
        ]
        text = f"🏠 Домашка: {current_hw_data['title']}\n"\
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"\
            f"Загрузило {len(students_ids)} студентов\n"
        
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT

    elif callback_data == "add_hw":
        text = f"🔉 Введите название ДЗ:"
        buttons = [InlineKeyboardButton(text=f"Отмена", callback_data=f"cancel")]
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
        return ADD_HW_TITLE

    elif callback_data == "back_to_course":
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
        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=2))
        text = (
            f"🔈 Название: {current_course_data['title']}\n"
            f"🆔 Код: {current_course_data['code']}\n"
            f"🔗 Ссылка: {current_course_data['link']}\n"
            f"🚼 Студентов: {len(current_course_data['students'])}\n"
            f"🛎️ Статус: {current_course_data['status']}\n"
        )
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MANAGEMENT


async def hw_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered hw_management handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("hw_"):
        student_id = int(callback_data[len("hw_") :])
        current_hw_id = context.chat_data["current_hw_id"]
        current_course_id = context.chat_data["current_course_id"]

        hw_title = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id][
            "title"
        ]
        student_name = [
            student["name"]
            for student in context.bot_data["courses"][current_course_id]["students"]
            if student["id"] == student_id
        ]

        hw_data = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id]
        is_graded = False
        score = None
        if (
            student_id in hw_data["scores"].keys()
            and hw_data["scores"][student_id] is not None
        ):
            is_graded = True
            score = hw_data["scores"][student_id]

        text = f"📚 Домашка: {hw_title}\n" f"🧑🏻‍🎓 Студент: {student_name}\n"

        if is_graded:
            text += f"💯 Оценка: {score}\n"

        file_id = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id][
            "students"
        ][student_id]

        buttons = [
            InlineKeyboardButton(
                text=f"Назад к домашке", callback_data=f"back_to_hw_{student_id}"
            )
        ]
        # если не проверено, добавить кнопочку "Проверить"
        if not is_graded:
            buttons.append(
                InlineKeyboardButton(
                    text=f"🖍️ Оценить", callback_data=f"grade_{student_id}"
                )
            )

        buttons.append(
            InlineKeyboardButton(
                text=f"💬 Комментировать",
                callback_data=f"comment_{student_id}"
            )
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        try:
            # Отправляем файл пользователю
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            # DELETE -- отправляем файл
            message = await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_id,
                caption=text,
                reply_markup=keyboard,
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке файла: {e}")

        return HW_INFO

    elif callback_data.startswith("edit_deadline_"):
        hw_id = callback_data[len("edit_deadline_"):]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        text = f"🕰️ Текущий дедлайн: {str(hw_data['deadline']).split('+')[0]}\n"\
                f"⌨️ Введите новый дедлайн в формате '23:59 15.09.2023':\n"

        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return EDIT_HW_DEADLINE

    elif callback_data.startswith("edit_title_"):
        hw_id = callback_data[len("edit_title_"):]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        text = f"🔉 Текущее название: {hw_data['title']}\n"\
                f"⌨️ Введите новое название:\n"
        
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data, 
            chat_id=context.chat_data["chat_id"],
            message_id=message.message_id
        )
        return EDIT_HW_TITLE

    elif callback_data.startswith("remove_"):
        hw_id = callback_data[len("remove_"):]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        text = f"🔉 Задание: {hw_data['title']}\n"\
                f"Вы уверены, что хотите удалить задание? Отменить это действие будет невозможно!\n"
        
        buttons = [
            InlineKeyboardButton(
                text=f"↩✅ Да",
                callback_data=f"yes"
            ),
            InlineKeyboardButton(
                text=f"❌ Отмена",
                callback_data=f"cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        return REMOVE_HW

    elif callback_data == "back_to_hws":
        current_course_id = context.chat_data["current_course_id"]
        hws = context.bot_data["courses"][current_course_id]["HWs"]
        buttons = [
            InlineKeyboardButton(
                text=f"📚 {hw_data['title']}", callback_data=f"hw_{hw_id}"
            )
            for hw_id, hw_data in hws.items()
        ]
        buttons.append(
            InlineKeyboardButton(text=f"Добавить ДЗ", callback_data=f"add_hw")
        )
        buttons.append(
            InlineKeyboardButton(text=f"К меню курса", callback_data=f"back_to_course")
        )
        course_title = context.bot_data["courses"][current_course_id]["title"]
        text = f"📖 Курс: {course_title}\n"

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return HWS_MANAGEMENT

    elif callback_data.startswith("upload_scores_"):
        hw_id = callback_data[len("upload_scores_"):]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        filename = f'hw_{hw_id}_scores.yml'
        scores = create_scores_file_hw(
            hw_data=hw_data,
            students=context.bot_data['courses'][course_id]['students'],
            filename=filename
        )

        text = f'ДЗ: {hw_data["title"]}\n'
        for student_name, student_score in scores.items():
            if student_name != 'Test' and student_name != 'HW':
                text += f'{student_name}: {student_score}\n'
        
        text += f'Загрузите файл такого же формата\n'

        buttons = [
            InlineKeyboardButton(
                text='Назад', callback_data=f'cancel_{hw_id}'
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

        return UPLOAD_SCORES_HW

    elif callback_data.startswith("download_solutions_"):
        hw_id = callback_data[len("download_solutions_"):]

        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        status = await prepare_hw_solutions(
            context=context,
            course_id=course_id,
            hw_id=hw_id,
            filename=f'HW_{hw_id}_solutions'
        )

        await delete_messages(
            context=context,
            chat_id=update.effective_chat.id
        )

        if status:
            text = f"HW: {hw_data['title']}\n"
            buttons = [
                InlineKeyboardButton(
                    text=f"✅ ok",
                    callback_data=f"ok_status_ok_{hw_id}"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            message = await context.bot.send_document(
                chat_id=update.effective_chat.id, 
                document=open(f'HW_{hw_id}_solutions.zip' , 'rb'), 
                caption=text,
                reply_markup=keyboard
            )
            os.remove(f'HW_{hw_id}_solutions.zip')
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
        else:
            text = f"❌ Недостаточно места\n"
            buttons = [
                InlineKeyboardButton(
                    text=f"✅ ok",
                    callback_data=f"ok_status_kok_{hw_id}"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
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
        return DOWNLOAD_HW_SOLUTIONS


async def download_hw_solutions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered download_hw_solutions handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    current_hw_id = None
    if callback_data.startswith("ok_status_ok_"):
        current_hw_id = callback_data[len("ok_status_ok_") :]
    elif callback_data.startswith("ok_status_kok_"):
        current_hw_id = callback_data[len("ok_status_kok_") :]
    
    assert current_hw_id is not None, 'current_hw_id is None'

    context.chat_data["current_hw_id"] = current_hw_id

    current_course_id = context.chat_data["current_course_id"]
    current_course_data = context.bot_data["courses"][current_course_id]
    current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
        current_hw_id
    ]

    students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
    students = {}
    for student in current_course_data["students"]:
        if student["id"] in students_ids:
            students[student["id"]] = student["name"]
    buttons = [
        InlineKeyboardButton(
            text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
        )
        for student_id, student_name in students.items()
    ]
    buttons += [
        InlineKeyboardButton(
            text=f"⏰ Изменить дедлайн",
            callback_data=f"edit_deadline_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"💬 Изменить название",
            callback_data=f"edit_title_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"💥 Удалить задание",
            callback_data=f"remove_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"↩️ Назад",
            callback_data=f"back_to_hws"
        ),
        InlineKeyboardButton(
            text=f"🔼 Загрузить оценки",
            callback_data=f"upload_scores_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"⬇️ Скачать решения",
            callback_data=f"download_solutions_{current_hw_id}"
        )
    ]
    text = f"🏠 Домашка: {current_hw_data['title']}\n"\
        f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"\
        f"Загрузило {len(students_ids)} студентов\n"
        
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    # DELETE -- за этим сообщением может следовать отправка файлов

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
    return HW_MANAGEMENT


async def upload_scores_hw_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered upload_scores_hw_document handler")

    if update.message and update.message.document:
        document = update.message.document
        file_extension = document.file_name.split('.')[-1].lower()
        hw_id = context.chat_data['current_hw_id']
        buttons = [
            InlineKeyboardButton(
                text='Назад', callback_data=f'cancel_{hw_id}'
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
            return UPLOAD_SCORES_HW

        temp_file_path = f"new_scores_hw_{hw_id}.yml"
        await save_document_to_disk(document, temp_file_path)
        try:
            with open(temp_file_path, 'r') as file:
                yaml_content = yaml.load(file, Loader=Loader)

            if isinstance(yaml_content, dict):
                for key, value in yaml_content.items():
                    if key == 'Test' or key == 'HW':
                        continue
                    try:
                        float(value)
                    except ValueError:
                        # оценка не число. Коллапс!
                        text = f'❌ Файл не соответствует формату. Пара \'{key}\' : \'{value}\' не удовлетворяет формату.\n'\
                                f'❗️Файл должен содержать словарь, ключи которого -- имена студентов (строки),'\
                                f'а значения -- оценки (float). Исключением является только пара с ключом \'HW\', значение по этому ключу должно быть строкой.'\
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
                        return UPLOAD_SCORES_HW
            else:
                text = f'❌ Файл не соответствует формату. Файл должен содержать словарь, ключи которого -- имена студентов (строки),'\
                        f'а значения -- оценки (float). Исключением является только пара с ключом \'HW\', значение по этому ключу должно быть строкой.'\
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
                return UPLOAD_SCORES_HW
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
            return UPLOAD_SCORES_HW
    
    if os.path.exists(temp_file_path):
        os.remove(temp_file_path)
    course_id = context.chat_data["current_course_id"]
    course_data = context.bot_data['courses'][course_id]
    hw_id = context.chat_data["current_hw_id"]
    hw_data = course_data['HWs'][hw_id]
    scores_id = {}
    for student_name, student_score in yaml_content.items():
        if student_name == 'Test' or student_name == 'HW':
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
            return UPLOAD_SCORES_HW
        
        scores_id[student_id] = student_score
    
    for student_id, score in scores_id.items():
        context.bot_data['courses'][course_id]['HWs'][hw_id]['scores'][student_id] = score
    new_scores_name = {}

    course_data = context.bot_data['courses'][course_id]
    hw_data = course_data['HWs'][hw_id]
    
    for student_id, student_score in hw_data['scores'].items():
        student_name = "Unknown"
        for student in course_data['students']:
            if student_id == student['id']:
                student_name = student['name']
                break
        
        new_scores_name[student_name] = student_score
    
    text = f'LP: {hw_data["title"]}\n'\
            f'Текущие оценки:\n'
    
    for name, score in new_scores_name.items():
        text += f'{name}: {score}\n'
    
    buttons = [
        InlineKeyboardButton(
            text=f'✅Ok', callback_data=f'ok_{hw_id}'
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

    return UPLOADING_SCORES_HW

async def upload_scores_hw_bttn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered upload_scores_hw_bttn handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    current_hw_id = context.chat_data['current_hw_id']
    current_course_id = context.chat_data["current_course_id"]
    current_course_data = context.bot_data["courses"][current_course_id]
    current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
        current_hw_id
    ]

    students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
    students = {}
    for student in current_course_data["students"]:
        if student["id"] in students_ids:
            students[student["id"]] = student["name"]
    buttons = [
        InlineKeyboardButton(
            text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
        )
        for student_id, student_name in students.items()
    ]
    buttons += [
        InlineKeyboardButton(
            text=f"⏰ Изменить дедлайн",
            callback_data=f"edit_deadline_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"💬 Изменить название",
            callback_data=f"edit_title_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"💥 Удалить задание",
            callback_data=f"remove_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"↩️ Назад",
            callback_data=f"back_to_hws"
        ),
        InlineKeyboardButton(
            text=f"🔼 Загрузить оценки",
            callback_data=f"upload_scores_{current_hw_id}"
        )
    ]
    text = f"🏠 Домашка: {current_hw_data['title']}\n"\
        f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"\
        f"Загрузило {len(students_ids)} студентов\n"
        
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    # DELETE -- за этим сообщением может следовать отправка файлов
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
    return HW_MANAGEMENT

async def uploading_scores_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered uploading_scores_hw handler")

    await update.callback_query.answer()
    callback_data = update.callback_query.data

    current_hw_id = context.chat_data['current_hw_id']
    current_course_id = context.chat_data["current_course_id"]
    current_course_data = context.bot_data["courses"][current_course_id]
    current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
        current_hw_id
    ]

    students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
    students = {}
    for student in current_course_data["students"]:
        if student["id"] in students_ids:
            students[student["id"]] = student["name"]
    buttons = [
        InlineKeyboardButton(
            text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
        )
        for student_id, student_name in students.items()
    ]
    buttons += [
        InlineKeyboardButton(
            text=f"⏰ Изменить дедлайн",
            callback_data=f"edit_deadline_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"💬 Изменить название",
            callback_data=f"edit_title_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"💥 Удалить задание",
            callback_data=f"remove_{current_hw_id}"
        ),
        InlineKeyboardButton(
            text=f"↩️ Назад",
            callback_data=f"back_to_hws"
        ),
        InlineKeyboardButton(
            text=f"🔼 Загрузить оценки",
            callback_data=f"upload_scores_{current_hw_id}"
        )
    ]
    text = f"🏠 Домашка: {current_hw_data['title']}\n"\
        f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"\
        f"Загрузило {len(students_ids)} студентов\n"
        
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    # DELETE -- за этим сообщением может следовать отправка файлов
    message = await update.callback_query.edit_message_text(
        text=text, reply_markup=keyboard
    )
    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
    )
    return HW_MANAGEMENT

async def remove_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered remove_hw handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "yes":
        hw_id = context.chat_data.pop("current_hw_id")
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]

        if hw_id in course_data["HWs"].keys():
            context.bot_data["courses"][course_id]["HWs"].pop(hw_id)

        hws = context.bot_data["courses"][course_id]["HWs"]
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
        text = f"📖 Курс: {course_data['title']}\n"
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return HWS_MANAGEMENT

    elif callback_data == "cancel":
        current_hw_id = context.chat_data["current_hw_id"]

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        text = (
            f"🏠 Домашка: {current_hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"
            f"Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT

async def edit_hw_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_hw_title handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        new_hw_title = update.message.text

    if callback_data == "...":
        # entered new title
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        context.chat_data[f"new_hw_title_{hw_id}"] = new_hw_title

        text = f"▶️ Прежнее название: {hw_data['title']}\n"\
                f"🆕 Новое название: {new_hw_title}\n"
        
        buttons = [
            InlineKeyboardButton(
                text=f"✅ Сохранить",
                callback_data=f"save"
            ),
            InlineKeyboardButton(
                text=f"❌ Отмена",
                callback_data=f"cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(
            context=context,
            chat_id=context.chat_data["chat_id"]
        )
        message = await context.bot.send_message(
            chat_id=context.chat_data["chat_id"],
            text=text,
            reply_markup=keyboard
        )
        return SAVE_HW_TITLE

    elif callback_data == "cancel":
        # Cancel button
        current_hw_id = context.chat_data["current_hw_id"]

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        text = (
            f"🏠 Домашка: {current_hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"
            f"Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT

async def save_hw_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered save_hw_title handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "save":
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        new_title = context.chat_data.pop(f"new_hw_title_{hw_id}")
        context.bot_data["courses"][course_id]["HWs"][hw_id]["title"] = new_title

        current_hw_id = context.chat_data["current_hw_id"]

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        text = (
            f"🏠 Домашка: {current_hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"
            f"Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT
    
    elif callback_data == "cancel":
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        text = f"🔉 Текущее название: {hw_data['title']}\n"\
                f"⌨️ Введите новое название:\n"
        
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(
            context=context,
            chat_id=context.chat_data["chat_id"]
        )
        await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        return EDIT_HW_TITLE

async def edit_hw_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered edit_hw_deadline handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        hw_deadline_str = update.message.text

    if callback_data == "...":
        # entered new deadline
        try:
            str_format = "%H:%M %d.%m.%Y"
            moscow_tz = pytz.timezone("Europe/Moscow")
            deadline = datetime.strptime(hw_deadline_str, str_format)
            deadline = moscow_tz.localize(deadline)
        except:
            text = (
                f"Введенные время и дата не соответствуют формату."
                "Пожалуйста, введите дедлайн в формате '23:59 15.09.2023' ещё раз:"
            )
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
            return EDIT_HW_DEADLINE

        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        #context.bot_data["courses"][course_id]["HWs"][hw_id]["deadline"] = deadline

        context.chat_data[f"new_deadline_{hw_id}"] = deadline

        text = f"🏠 Задание: {hw_data['title']}\n"\
                f"▶️ Прежний дедлайн: {str(hw_data['deadline']).split('+')[0]}\n"\
                f"🆕 Новый дедлайн: {str(deadline).split('+')[0]}\n"
        
        buttons = [
            InlineKeyboardButton(
                text=f"✅ Сохранить",
                callback_data=f"save"
            ),
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        
        await delete_messages(
            context=context,
            chat_id=context.chat_data["chat_id"]
        )
        message = await context.bot.send_message(
            chat_id=context.chat_data["chat_id"],
            text=text, 
            reply_markup=keyboard
        )
        return SAVE_HW_DEADLINE
    
    elif callback_data == "cancel":
        # Cancel button
        current_hw_id = context.chat_data["current_hw_id"]

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        text = (
            f"🏠 Домашка: {current_hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"
            f"Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT

async def save_hw_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered save_hw_deadline handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "save":
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]

        new_deadline = context.chat_data.pop(f"new_deadline_{hw_id}")

        context.bot_data["courses"][course_id]["HWs"][hw_id]["deadline"] = new_deadline

        current_hw_id = context.chat_data["current_hw_id"]

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        text = (
            f"🏠 Домашка: {current_hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"
            f"Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT

    elif callback_data == "cancel":
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        course_data = context.bot_data["courses"][course_id]
        hw_data = course_data["HWs"][hw_id]
        text = f"🕰️ Текущий дедлайн: {hw_data['deadline']}\n"\
                f"⌨️ Введите новый дедлайн в формате '23:59 15.09.2023':\n"

        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Отмена",
                callback_data=f"cancel"
            )
        ]

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return EDIT_HW_DEADLINE

async def hw_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered hw_info handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("back_to_hw_"):
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]
        students_ids = context.bot_data["courses"][course_id]["HWs"][hw_id][
            "students"
        ].keys()
        students = {}
        for student in context.bot_data["courses"][course_id]["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"🧑🏻‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
        text = (
            f"🏠 Домашка: {hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(hw_data['deadline']).split('+')[0]}\n"
            f"🧳 Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE -- за этим сообщением может следовать отправка файлов
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT
    
    elif callback_data.startswith("grade_"):
        student_id = int(callback_data[len("grade_") :])

        context.chat_data["hw_to_grade_student_id"] = student_id

        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]

        hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        text = (
            f"📚 Домашка: {hw_data['title']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"Введите оценку:\n"
        )
        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"hw_{student_id}")
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE если введено сообщение
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_GRADE

    elif callback_data.startswith("comment_"):
        student_id = int(callback_data[len("comment_"):])

        context.chat_data["comment_student_id"] = student_id

        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]

        hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        text = (
            f"📚 Домашка: {hw_data['title']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"Введите файл или отправьте текстовое сообщение в качестве комментария\n"
        )

        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"cancel_{student_id}"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data, 
            chat_id=context.chat_data["chat_id"],
            message_id=message.message_id
        )
        return COMMENT_HW_REQUEST

async def comment_hw_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered comment_hw_request handler")

    student_id = context.chat_data.pop("comment_student_id", None)

    if update.message:
        # sent comment
        if update.message.text:
            # text comment
            comment = update.message.text
            #===========================================#
            context.chat_data["comment_info"] = {
                "is_doc": False,
                "is_photo": False,
                "comment": comment
            }
            #===========================================#
            
            hw_id = context.chat_data["current_hw_id"]
            course_id = context.chat_data["current_course_id"]

            hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
            student_name = get_student_name_by_id(
                students=context.bot_data["courses"][course_id]["students"], id=student_id
            )
            text = (
                f"📚 Домашка: {hw_data['title']}\n"
                f"🧑🏻‍🎓 Студент: {student_name}\n"
                f"💬 Комментарий: {comment}\n"
            )
            buttons = [
                InlineKeyboardButton(
                    text=f"✅ Отправить",
                    callback_data=f"send_{student_id}"
                ),
                InlineKeyboardButton(
                    text=f"↩️ Назад",
                    callback_data=f"cancel_{student_id}"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

            await delete_messages(context=context, chat_id=update.effective_chat.id)
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
            return SEND_HW_COMMENT

        elif update.message.document or update.message.photo:
            # document/photo comment
            is_doc = False
            is_photo = False
            if update.message.document:
                document = update.message.document
                is_doc = True

            if update.message.photo:
                document = update.message.photo[-1]
                is_photo = True
            
            file_id = document.file_id
            #============================================#
            context.chat_data["comment_info"] = {
                "is_doc": is_doc,
                "is_photo": is_photo,
                "comment": file_id
            }
            #============================================#

            hw_id = context.chat_data["current_hw_id"]
            course_id = context.chat_data["current_course_id"]

            hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
            student_name = get_student_name_by_id(
                students=context.bot_data["courses"][course_id]["students"], id=student_id
            )
            text = (
                f"📚 Домашка: {hw_data['title']}\n"
                f"🧑🏻‍🎓 Студент: {student_name}\n"
                f"💬 Комментарий: в файле\n"
            )
            buttons = [
                InlineKeyboardButton(
                    text=f"✅ Отправить",
                    callback_data=f"send_{student_id}"
                ),
                InlineKeyboardButton(
                    text=f"↩️ Назад",
                    callback_data=f"cancel_{student_id}"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

            await delete_messages(context=context, chat_id=update.effective_chat.id)
            # DELETE если введено сообщение
            if is_doc:
                message = await context.bot.send_document(
                    chat_id=update.effective_chat.id, 
                    document=document, 
                    caption=text,
                    reply_markup=keyboard
                )
            elif is_photo:
                message = await context.bot.send_photo(
                    chat_id=update.effective_chat.id, 
                    photo=document, 
                    caption=text,
                    reply_markup=keyboard
                )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
            return SEND_HW_COMMENT
    elif update.callback_query:
        # cancel button
        callback_data = update.callback_query.data
        student_id = int(callback_data[len("cancel_"):])
        current_hw_id = context.chat_data["current_hw_id"]
        current_course_id = context.chat_data["current_course_id"]

        hw_title = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id][
            "title"
        ]
        student_name = [
            student["name"]
            for student in context.bot_data["courses"][current_course_id]["students"]
            if student["id"] == student_id
        ]

        hw_data = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id]
        is_graded = False
        score = None
        if (
            student_id in hw_data["scores"].keys()
            and hw_data["scores"][student_id] is not None
        ):
            is_graded = True
            score = hw_data["scores"][student_id]

        text = f"📚 Домашка: {hw_title}\n" f"🧑🏻‍🎓 Студент: {student_name}\n"

        if is_graded:
            text += f"💯 Оценка: {score}\n"

        file_id = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id][
            "students"
        ][student_id]

        buttons = [
            InlineKeyboardButton(
                text=f"Назад к домашке", callback_data=f"back_to_hw_{student_id}"
            )
        ]
        # если не проверено, добавить кнопочку "Проверить"
        if not is_graded:
            buttons.append(
                InlineKeyboardButton(
                    text=f"🖍️ Оценить", callback_data=f"grade_{student_id}"
                )
            )

        buttons.append(
            InlineKeyboardButton(
                text=f"💬 Комментировать",
                callback_data=f"comment_{student_id}"
            )
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        try:
            # Отправляем файл пользователю
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            # DELETE -- отправляем файл
            message = await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_id,
                caption=text,
                reply_markup=keyboard,
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке файла: {e}")

        return HW_INFO

async def send_hw_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered send_hw_comment handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("send_"):
        student_id = int(callback_data[len("send_"):])
        course_id = context.chat_data["current_course_id"]
        hw_id = context.chat_data["current_hw_id"]
        hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]

        comment_data = context.chat_data.pop("comment_info", None)

        if not comment_data:
            logging.warning(f"❌ The 'comment_info' field is missing in the bot_data dictionary.")
            comment_data = {
                "is_doc": False,
                "is_photo": False,
                "comment": ""
            }
        
        if "comments" not in hw_data.keys():
            context.bot_data["courses"][course_id]["HWs"][hw_id]["comments"] = {}
        context.bot_data["courses"][course_id]["HWs"][hw_id]["comments"][student_id] =\
            {
                "is_doc": int(comment_data["is_doc"]),
                "is_photo": int(comment_data["is_photo"]),
                "comment": comment_data["comment"]
            }
        current_hw_id = context.chat_data["current_hw_id"]
        current_course_id = context.chat_data["current_course_id"]

        hw_title = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id][
            "title"
        ]

        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )

        is_graded = False
        score = None
        if (
            student_id in hw_data["scores"].keys()
            and hw_data["scores"][student_id] is not None
        ):
            is_graded = True
            score = hw_data["scores"][student_id]

        text = f"📚 Домашка: {hw_title}\n" f"🧑🏻‍🎓 Студент: {student_name}\n"

        if is_graded:
            text += f"💯 Оценка: {score}\n"

        file_id = context.bot_data["courses"][current_course_id]["HWs"][current_hw_id][
            "students"
        ][student_id]

        buttons = [
            InlineKeyboardButton(
                text=f"Назад к домашке", callback_data=f"back_to_hw_{student_id}"
            )
        ]
        # если не проверено, добавить кнопочку "Проверить"
        if not is_graded:
            buttons.append(
                InlineKeyboardButton(
                    text=f"🖍️ Оценить", callback_data=f"grade_{student_id}"
                )
            )

        buttons.append(
            InlineKeyboardButton(
                text=f"💬 Комментировать",
                callback_data=f"comment_{student_id}"
            )
        )

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        try:
            # Отправляем файл пользователю
            await delete_messages(context=context, chat_id=update.effective_chat.id)
            # DELETE -- отправляем файл
            message = await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file_id,
                caption=text,
                reply_markup=keyboard,
            )
            save_message(
                bot_data=context.bot_data,
                chat_id=update.effective_chat.id,
                message_id=message.message_id,
            )
        except Exception as e:
            logging.error(f"Ошибка при отправке файла: {e}")

        return HW_INFO
    elif callback_data.startswith("cancel_"):
        _ = context.chat_data.pop("comment_file_info", None)

        student_id = int(callback_data[len("cancel_"):])

        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]

        hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        text = (
            f"📚 Домашка: {hw_data['title']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"Введите файл или отправьте текстовое сообщение в качестве комментария\n"
        )

        buttons = [
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"cancel_{student_id}"
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))

        await delete_messages(context=context, chat_id=update.effective_chat.id)
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text,
            reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data, 
            chat_id=context.chat_data["chat_id"],
            message_id=message.message_id
        )
        return COMMENT_HW_REQUEST

async def hw_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered hw_grade handler")
    score = update.message.text
    student_id = context.chat_data["hw_to_grade_student_id"]
    hw_id = context.chat_data["current_hw_id"]
    course_id = context.chat_data["current_course_id"]
    hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
    student_name = get_student_name_by_id(
        students=context.bot_data["courses"][course_id]["students"], id=student_id
    )
    try:
        score = float(score)
    except:
        text = (
            f"⛔️ Оценка должна быть числом!\n"
            f"📚 Домашка: {hw_data['title']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"Введите оценку:\n"
        )
        buttons = [
            InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"hw_{student_id}")
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE если введено сообщение
        message = await update.message.reply_text(text=text, reply_markup=keyboard)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_GRADE

    text = (
        f"📚 Домашка: {hw_data['title']}\n"
        f"🧑🏻‍🎓 Студент: {student_name}\n"
        f"💯 Оценка: {score}\n"
    )
    buttons = [
        InlineKeyboardButton(text=f"✅ Сохранить", callback_data=f"save_{score}"),
        InlineKeyboardButton(text=f"↩️ Отмена", callback_data=f"cancel"),
    ]
    keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
    await delete_messages(context=context, chat_id=update.effective_chat.id)
    # DELETE -- за этим сообщением может следовать файл
    message = await update.message.reply_text(text=text, reply_markup=keyboard)
    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
    )
    return HW_SAVE_GRADE

async def hw_save_grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered hw_save_grade handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data.startswith("save_"):
        score = float(callback_data[len("save_") :])
        student_id = context.chat_data.pop("hw_to_grade_student_id")
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]

        context.bot_data["courses"][course_id]["HWs"][hw_id]["scores"][
            student_id
        ] = score

        current_hw_id = context.chat_data["current_hw_id"]

        current_course_id = context.chat_data["current_course_id"]
        current_course_data = context.bot_data["courses"][current_course_id]
        current_hw_data = context.bot_data["courses"][current_course_id]["HWs"][
            current_hw_id
        ]

        students_ids = current_course_data["HWs"][current_hw_id]["students"].keys()
        students = {}
        for student in current_course_data["students"]:
            if student["id"] in students_ids:
                students[student["id"]] = student["name"]
        buttons = [
            InlineKeyboardButton(
                text=f"👨🏿‍🎓 {student_name}", callback_data=f"hw_{student_id}"
            )
            for student_id, student_name in students.items()
        ]
        buttons += [
            InlineKeyboardButton(
                text=f"⏰ Изменить дедлайн",
                callback_data=f"edit_deadline_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💬 Изменить название",
                callback_data=f"edit_title_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"💥 Удалить задание",
                callback_data=f"remove_{current_hw_id}"
            ),
            InlineKeyboardButton(
                text=f"↩️ Назад",
                callback_data=f"back_to_hws"
            )
        ]
        text = (
            f"🏠 Домашка: {current_hw_data['title']}\n"
            f"🕰️ Дедлайн: {str(current_hw_data['deadline']).split('+')[0]}\n"
            f"Загрузило {len(students_ids)} студентов\n"
        )
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        # DELETE -- за ним может следовать файл
        message = await update.callback_query.edit_message_text(
            text=text, reply_markup=keyboard
        )
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return HW_MANAGEMENT

    elif callback_data == "cancel":
        hw_id = context.chat_data["current_hw_id"]
        course_id = context.chat_data["current_course_id"]

        hw_data = context.bot_data["courses"][course_id]["HWs"][hw_id]
        student_name = get_student_name_by_id(
            students=context.bot_data["courses"][course_id]["students"], id=student_id
        )
        text = (
            f"📚 Домашка: {hw_data['title']}\n"
            f"🧑🏻‍🎓 Студент: {student_name}\n"
            f"Введите оценку:\n"
        )
        buttons = [InlineKeyboardButton(text=f"↩️ Назад", callback_data=f"hw_{hw_id}")]
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
        return HW_GRADE

async def add_hw_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_hw_title handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        hw_title = update.message.text

    if callback_data == "...":
        # entered title
        context.chat_data["new_hw_title"] = hw_title
        text = f"📅 Введите дедлайн в формате '23:59 15.09.2023':"
        buttons = [InlineKeyboardButton(text=f"↩️Отмена", callback_data=f"cancel")]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        # DELETE если введено сообщение
        message = await update.message.reply_text(text=text, reply_markup=keyboard)
        save_message(
            bot_data=context.bot_data,
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
        )
        return ADD_DEADLINE

    elif callback_data == "cancel":
        current_course_id = context.chat_data["current_course_id"]
        hws = context.bot_data["courses"][current_course_id]["HWs"]
        buttons = [
            InlineKeyboardButton(
                text=f"📚 {hw_data['title']}", callback_data=f"hw_{hw_id}"
            )
            for hw_id, hw_data in hws.items()
        ]
        buttons.append(
            InlineKeyboardButton(text=f"Добавить ДЗ", callback_data=f"add_hw")
        )
        buttons.append(
            InlineKeyboardButton(text=f"К меню курса", callback_data=f"back_to_course")
        )
        course_title = context.bot_data["courses"][current_course_id]["title"]
        text = f"📖 Курс: {course_title}\n"

        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return HWS_MANAGEMENT

async def add_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_deadline handler")
    callback_data = "..."
    try:
        await update.callback_query.answer()
        callback_data = update.callback_query.data
    except:
        hw_deadline_str = update.message.text

    if callback_data == "...":
        # entered hw deadline string
        try:
            str_format = "%H:%M %d.%m.%Y"
            moscow_tz = pytz.timezone("Europe/Moscow")
            deadline = datetime.strptime(hw_deadline_str, str_format)
            deadline = moscow_tz.localize(deadline)
        except:
            text = (
                f"Введенные время и дата не соответствуют формату."
                "Пожалуйста, введите дедлайн в формате '23:59 15.09.2023' ещё раз:"
            )
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
            return ADD_DEADLINE

        context.chat_data["hw_to_add"] = {
            "title": context.chat_data["new_hw_title"],
            "deadline": deadline,
        }

        text = (
            f"💬 Название: '{context.chat_data['new_hw_title']}'\n"
            f"📅 Дедлайн: {str(deadline).split('+')[0]}\n"
        )
        buttons = [
            InlineKeyboardButton(text=f"👍 Добавить", callback_data=f"add"),
            InlineKeyboardButton(text=f"↩️ Отмена", callback_data=f"cancel"),
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await delete_messages(context=context, chat_id=update.effective_chat.id)
        await update.message.reply_text(text=text, reply_markup=keyboard)
        return ADD_HW

    elif callback_data == "cancel":
        text = f"🔉 Введите название ДЗ:"
        buttons = [InlineKeyboardButton(text=f"Отмена", callback_data=f"cancel")]
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
        return ADD_HW_TITLE

async def add_hw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.warning(f"🤖 Entered add_hw handler")
    await update.callback_query.answer()
    callback_data = update.callback_query.data

    if callback_data == "add":
        course_id = context.chat_data["current_course_id"]
        hws_ids = context.bot_data["courses"][course_id]["HWs"].keys()
        new_hw_id = generate_unique_id(existing_ids=hws_ids)
        hw_to_add = context.chat_data["hw_to_add"]
        context.chat_data.pop("hw_to_add")

        context.bot_data["courses"][course_id]["HWs"][new_hw_id] = {
            "title": hw_to_add["title"],
            "deadline": hw_to_add["deadline"],
            "students": {},
            "scores": {},
        }
        course_title = context.bot_data["courses"][course_id]["title"]
        text = f"✅ Домашка '{hw_to_add['title']}' добавлена в курс {course_title}"
        buttons = [
            InlineKeyboardButton(
                text=f"↩️ К домашним заданиям", callback_data=str(HWS_MANAGEMENT)
            )
        ]
        keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
        await update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return COURSE_MANAGEMENT

    elif callback_data == "cancel":
        text = f"📅 Введите дедлайн в формате '23:59 15.09.2023':"
        buttons = [InlineKeyboardButton(text=f"↩️ Отмена", callback_data=f"cancel")]
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
        return ADD_DEADLINE
