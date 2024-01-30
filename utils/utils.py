# utils.py
from telegram import Document
from telegram.ext import ContextTypes
import os
import random
import string
import shutil
import yaml
import logging
import zipfile
from typing import Any
from PIL import Image
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from handlers.states import (
    STUDENT_MENU
)


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i : i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


async def save_document_to_disk(document: Document, file_path: str):
    file = await document.get_file()
    await file.download_to_drive(file_path)


def get_courses_by_teacher(bot_data, teacher_id: int):
    """
    Returns: {course_id: course_data, ...}
    """

    courses = {}
    for course_id, course_data in bot_data["courses"].items():
        if teacher_id in [teacher["id"] for teacher in course_data["teachers"]]:
            courses[course_id] = course_data

    return courses


def get_courses_by_student(bot_data, student_id: int):
    """
    Returns: {course_id: course_data, ...}
    """
    courses = {}
    for course_id, course_data in bot_data["courses"].items():
        for student in course_data["students"]:
            if student["id"] == student_id:
                courses[course_id] = course_data

    return courses


def generate_unique_id(existing_ids: list, k=4):
    while True:
        new_id = "".join(random.choices(string.ascii_letters + string.digits, k=k))

        if new_id not in existing_ids:
            return new_id


def get_student_name_by_id(students, id):
    for student in students:
        if student["id"] == id:
            return student["name"]
    return None


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def split_long_message(long_msg, max_len=None):
    MAX_MESSAGE_LEN = 4095
    if max_len is None:
        max_len = MAX_MESSAGE_LEN
    parts = []
    while len(long_msg) > max_len:
        parts.append(long_msg[:max_len])
        long_msg = long_msg[max_len:]
    if len(long_msg) > 0 and long_msg not in parts:
        parts.append(long_msg)
    return parts


def split_many_buttons(buttons, max_amount=None):
    MAX_BUTTONS_AMOUNT = 100
    if max_amount is None:
        max_amount = MAX_BUTTONS_AMOUNT
    parts = []
    while len(buttons) > max_amount:
        parts.append(buttons[:max_amount])
        buttons = buttons[max_amount:]
    if len(buttons) > 0 and buttons not in parts:
        parts.append(buttons)
    return parts


async def create_directory_if_not_exists(directory_path):
    """
    Создает директорию, если она не существует.
    :param directory_path: Путь к директории, которую нужно создать.
    """
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
        except OSError as e:
            logging.warning(f"Ошибка при создании директории '{directory_path}': {e}")


def add_white_background(
    input_image_path, output_image_path, background_color=(255, 255, 255)
):
    try:
        image = Image.open(input_image_path)

        new_image = Image.new("RGB", image.size, background_color)

        new_image.paste(image, (0, 0), image)

        new_image.save(output_image_path)
    except Exception as e:
        logging.error(f"Ошибка1: {e}")

async def md2png(md_str: str, dir_test: str, filename: str):
    """
    md_str: markdown string
    filename: will be filename.png question.
    """
    full_path_md = "./" + dir_test + "/" + filename + ".md"
    full_path_png = "./" + dir_test + "/" + filename + ".png"
    with open(full_path_md, "w") as file:
        file.write(md_str)

    rights_cmd = f"chmod +x md2png.sh"
    os.system(rights_cmd)
    command = f"./md2png.sh {full_path_md}"
    os.system(command)

def save_message(bot_data, chat_id, message_id) -> None:
    """
    Usage:
    save_message(
        bot_data=context.bot_data,
        chat_id=update.effective_chat.id,
        message_id=message.message_id
    )
    """

    if "chat_messages_to_delete" not in bot_data.keys():
        bot_data["chat_messages_to_delete"] = {chat_id: [message_id]}
    elif chat_id not in bot_data["chat_messages_to_delete"].keys():
        bot_data["chat_messages_to_delete"][chat_id] = [message_id]
    else:
        bot_data["chat_messages_to_delete"][chat_id].append(message_id)


async def delete_messages(context, chat_id) -> None:
    """
    Usage:
    await delete_messages(
        context=context,
        chat_id=update.effective_chat.id
    )
    """
    bot = context.bot
    bot_data = context.bot_data
    if (
        "chat_messages_to_delete" in bot_data.keys()
        and chat_id in bot_data["chat_messages_to_delete"].keys()
    ):
        for msg_id in bot_data["chat_messages_to_delete"][chat_id]:
            deleted = False
            try:
                deleted = await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except:
                pass
            if deleted:
                bot_data["chat_messages_to_delete"][chat_id].remove(msg_id)


async def check_course_existance_student(context, course_id, chat_id, effective_msg_id):
    """
    Checks if course with course_id exists in context.bot_data. If no, sends 
    courses menu to student with student_id.

    Typical usage:
    await check_course_existance_student(
        context=context,
        course_id=context.chat_data["current_course_id"],
        chat_id=update.effective_chat.id,
        effective_msg_id=update.effective_message.message_id
    )
    """
    flag = course_id not in context.bot_data["courses"].keys()
    
    if flag:
        if "current_course_id" in context.chat_data.keys():
            context.chat_data.pop("current_course_id")
        if "current_course_id" in context.user_data.keys():
            context.user_data.pop("current_course_id")
        
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=effective_msg_id
            )
        except:
            pass

        courses = {}
        user_id = context.user_data["current_user"]["id"]
        user_f_name = context.user_data["current_user"]["name"]
        for course_id, course_data in context.bot_data["courses"].items():
            if user_id in [student["id"] for student in course_data["students"]]:
                courses[course_id] = course_data

        if len(courses.keys()) == 0:
            # new student
            text = f"🤖 Добро пожаловать, {user_f_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"🙇🏼‍ Присоединиться к курсу", callback_data="join_course"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            #await update.message.reply_text(text=text, reply_markup=keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
        else:
            text = f"🖖🏻 Привет, {user_f_name}"
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
            #await update.message.reply_text(text=text, reply_markup=keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
    
    return flag


async def check_course_membership(context, chat_id, course_id, effective_msg_id):
    """
    Checks if current user (context.user_data["current_user"]["id"])
    belongs to course (context.user_data["current_course_id"]).
    If not, sends courses menu.

    Typical usage:
    await check_course_membership(
        context=context,
        chat_id=update.effective_chat.id,
        effective_msg_id=update.effective_message.message_id
    )
    """
    student_id = context.user_data["current_user"]["id"]

    to_courses_menu = False
    if course_id not in context.bot_data["courses"].keys():
        to_courses_menu = True
    else:
        to_courses_menu = True
        for student in context.bot_data["courses"][course_id]["students"]:
            if student["id"] == student_id:
                to_courses_menu = False
                break
    
    if to_courses_menu:
        if "current_course_id" in context.chat_data.keys():
            context.chat_data.pop("current_course_id")
        if "current_course_id" in context.user_data.keys():
            context.user_data.pop("current_course_id")
        
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=effective_msg_id
            )
        except:
            pass

        courses = {}
        user_id = context.user_data["current_user"]["id"]
        user_f_name = context.user_data["current_user"]["name"]
        for course_id, course_data in context.bot_data["courses"].items():
            if user_id in [student["id"] for student in course_data["students"]]:
                courses[course_id] = course_data

        if len(courses.keys()) == 0:
            # new student
            text = f"🤖 Добро пожаловать, {user_f_name}"
            buttons = [
                InlineKeyboardButton(
                    text=f"🙇🏼‍ Присоединиться к курсу", callback_data="join_course"
                )
            ]
            keyboard = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
            #await update.message.reply_text(text=text, reply_markup=keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
        else:
            text = f"🖖🏻 Привет, {user_f_name}"
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
            #await update.message.reply_text(text=text, reply_markup=keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
    
    return to_courses_menu


async def check_student_consistance(context, chat_id, effective_msg_id):
    """
    Typical usage:
    flag = await check_student_consistance(
        context=context,
        chat_id=context.chat_data["chat_id"],
        effective_msg_id=update.effective_message.message_id
    )
    if flag:
        return STUDENT_MENU
    """
    course_id = None
    if "current_course_id" in context.chat_data.keys():
        course_id = context.chat_data["current_course_id"]
    elif "current_course_id" in context.user_data.keys():
        course_id = context.user_data["current_course_id"]

    flag1 = False
    flag2 = False

    if course_id:
        flag1 = await check_course_existance_student(
            context=context,
            course_id=course_id,
            chat_id=chat_id,
            effective_msg_id=effective_msg_id
        )

        if not flag1:
            flag2 = await check_course_membership(
                context=context,
                chat_id=chat_id,
                course_id=course_id,
                effective_msg_id=effective_msg_id
            )
    
    return flag1 or flag2


def recover_entered_students_data(test_data, course_students):
    """
    Returns list of students, who answered 
    at least one question in the test.
    """
    entered_students = []
    for student_id in test_data["answers"].keys():
        for student in course_students:
            if student["id"] == student_id:
                entered_students.append(student)
    
    return entered_students


def create_scores_file(test_data, students, filename):
    title = test_data['title']
    scores = {
        'Test': title
    }

    max_index = max([question_data['index'] for _, question_data in test_data['questions'].items()])
    for student in students:
        student_name = student['name']
        student_scores = [0] * (max_index + 1)
        if student['id'] in test_data['scores'].keys():
            for index in range(max_index + 1):
                q_id = [question_id for question_id, question_data in test_data['questions'].items() if question_data['index'] == index][0]
                if q_id in test_data['scores'][student['id']].keys():
                    student_scores[index] = test_data['scores'][student['id']][q_id]                    
        scores[student_name] = student_scores

    with open(filename, 'w', encoding="utf-8") as outfile:
        yaml.dump(scores,
                  outfile,
                  sort_keys=False,
                  allow_unicode=True
                )
    return scores

def create_scores_file_hw(hw_data, students, filename):
    title = hw_data['title']
    scores = {
        'HW': title
    }

    for student in students:
        if student['id'] in hw_data['scores'].keys():
            if hw_data['scores'][student['id']]:
                scores[student['name']] = hw_data['scores'][student['id']]
            else:
                scores[student['name']] = 0
        else:
            scores[student['name']] = 0

    with open(filename, 'w', encoding="utf-8") as outfile:
        yaml.dump(scores,
                  outfile,
                  sort_keys=False,
                  allow_unicode=True
                )
    return scores


async def prepare_hw_solutions(context, course_id, hw_id, filename: str) -> bool:
    hw_data = context.bot_data['courses'][course_id]['HWs'][hw_id]
    f_name_ids = hw_data['students']
    free_space = shutil.disk_usage('/').free  # in bytes
    one_hundred_Mb = 1e8  # 100 Mb = 1e8 bytes
    if free_space <= one_hundred_Mb:
        return False
    tmp_dir = f'tmp_dir_HW_sols_{hw_id}'
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.mkdir(tmp_dir)
    try:
        for st_id, doc_id in f_name_ids.items():
            file = await context.bot.get_file(doc_id)
            ext = file.file_path.split('.')[-1].lower()
            st_name = get_student_name_by_id(
                students=context.bot_data['courses'][course_id]['students'],
                id=st_id
            ).strip().replace(' ', '_')
            await file.download_to_drive(os.path.join(tmp_dir, f"{st_name}.{ext}"))
            size = os.path.getsize(os.path.join(tmp_dir, f"{st_name}.{ext}"))
            free_space -= size
            if free_space <= one_hundred_Mb:
                shutil.rmtree(tmp_dir)
                return False

        # Создаем архив
        archive_path = f"{filename}.zip"
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(tmp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, tmp_dir)
                    zipf.write(file_path, arcname=arcname)

        for file in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, file)
            os.remove(file_path)
        os.rmdir(tmp_dir)
        return True
    except Exception as e:
        logging.warning(e)
        return False
    finally:
        if os.path.isdir(tmp_dir):
            for file in os.listdir(tmp_dir):
                file_path = os.path.join(tmp_dir, file)
                os.remove(file_path)
            os.rmdir(tmp_dir)