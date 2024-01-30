from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Document

import os
import json
import logging
import traceback
import csv
from operator import itemgetter
from handlers.states import *

# Function to get titles for HWs and Tests
def get_titles(course_data):
    values_hw_titles = []
    for _, hw_data in course_data["HWs"].items():
        values_hw_titles.append("HW. " + hw_data['title'])
    values_test_titles = []
    for test_id, test_data in course_data["tests"].items():
        if not test_data['title'].startswith("Опросник"):
            values_test_titles.append("Test. " + test_data['title'])
    return values_hw_titles, values_test_titles

# Function to prepare data for the CSV
def get_statement_body(course_data):
    values_hw_titles, values_test_titles = get_titles(course_data)

    num_hws = len(values_hw_titles)
    num_tests = len(values_test_titles)

    prefix = ["Дерзнувший знать", "🤖Тесты", "🤖ДЗ", "🔥 Позиция"]
    headers = prefix + values_hw_titles + values_test_titles

    rows = [headers]

    students = course_data["students"]
    students.sort(key=itemgetter('name'))

    ratings = {}
    for student in students:
        row = [student["name"]]
        student_id = student["id"]

        # Placeholder for test and HW averages (you need to implement the logic)
        test_avg = ""  # Calculate test average
        hw_avg = ""    # Calculate HW average
        position = ""  # Calculate position

        row.extend([test_avg, hw_avg, position])

        # Add HW grades
        hws = []
        for _, hw_data in course_data["HWs"].items():
            if student_id in hw_data["scores"].keys():
                row.append(round(hw_data["scores"][student_id], 2))
            else:
                row.append(0)
            
            hws.append(float(row[-1]))
        

        # Add Test grades
        tests = []
        for test_id, test_data in course_data["tests"].items():
            if test_data['title'].startswith("Опросник"):
                continue

            if student_id in test_data["scores"].keys():
                total_score = 0
                for q_id, q_score in test_data["scores"][student_id].items():
                    if q_score:
                        total_score += float(q_score)
                row.append(round(total_score, 2))
            else:
                row.append(0)
            
            tests.append(float(row[-1]))
        
        row[1] = round(sum(tests)/len(tests), 2) if len(tests) > 0 else 0
        row[2] = round(sum(hws)/len(hws), 2) if len(hws) > 0 else 0

        ratings[student["name"]] = 0.15*row[1] + 0.35*row[2]

        rows.append(row)
    
    # Sort students based on ratings and assign positions
    sorted_students = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
    positions = {name: i+1 for i, (name, _) in enumerate(sorted_students)}

    # Fill in the position for each student
    for row in rows[1:]:
        row[3] = positions[row[0]]

    return rows

# Function to write data to CSV
def write_to_csv(course_data, csv_filename):
    rows = get_statement_body(course_data)
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerows(rows)

# Function to send CSV file to user
def send_csv_to_user(csv_filename, chat_id, bot_token):
    bot = Bot(token=bot_token)
    try:
        with open(csv_filename, 'rb') as file:
            bot.send_document(chat_id=chat_id, document=file, filename=csv_filename)
    except TelegramError as e:
        print(f"Error sending document: {e}")

async def send_csv_to_user(context: ContextTypes.DEFAULT_TYPE, chat_id, csv_filename):
    try:
        # Open the CSV file to send
        with open(csv_filename, 'rb') as file:
            # Create a custom keyboard or inline keyboard if needed
            # buttons = [
            #     InlineKeyboardButton(
            #     text=f"🔙 К меню курса", callback_data = context.chat_data["current_course_id"]
            # )
            # ]
            # keyboard = InlineKeyboardMarkup([[button] for button in buttons])

            # Send the document
            await context.bot.send_document(
                chat_id=chat_id,
                document=file,
                caption="Присылаю новую ведомость.",
                # reply_markup=keyboard
            )
    except Exception as e:
        logging.error(f"Error sending CSV file: {e}")


async def update_statement(update, context):
    course_id = context.chat_data["current_course_id"]
    course_data = context.bot_data["courses"][course_id]
    chat_id = update.effective_chat.id

    csv_filename = "statement.csv"
    write_to_csv(course_data, csv_filename)
    
    await send_csv_to_user(context, chat_id, csv_filename)