
import os
import json
import logging
import traceback
from operator import itemgetter

import httplib2
import apiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = "googleapi/credentials.json"
TOKEN_FILE = "googleapi/token.json"


def authentificate():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        SCOPES
    )

    httpAuth = credentials.authorize(httplib2.Http())
    service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)
    return service


def get_format_cells_body(num_hws, num_tests, sheet_id):
    # Merge cells
    format_cells = [
        # merge "Дерзнувший знать" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 0,
                "endColumnIndex": 1
            }
        }},
        # merge "🤖Тесты" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 1,
                "endColumnIndex": 2
            }
        }},
        # merge "🤖ДЗ" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 2,
                "endColumnIndex": 3
            }
        }},
        # merge "🤖Проект" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 3,
                "endColumnIndex": 4
            }
        }},
        # merge "rating" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 4,
                "endColumnIndex": 5
            }
        }},
        # merge "позиция" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 5,
                "endColumnIndex": 6
            }
        }},
        # merge "ДЗ" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 6,
                "endColumnIndex": 6 + num_hws
            }
        }},
        # merge "Тесты" cell
        {'mergeCells': {
            'mergeType': 'MERGE_ALL',
            'range': {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
                "startColumnIndex": 6 + num_hws,
                "endColumnIndex": 6 + num_hws + num_tests
            }
        }},
        # Center cells
        {"repeatCell": {
            "range": {
                "sheetId": sheet_id,
            },
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)",
        }}
    ]
    return format_cells


def format_color(endRowIndex, startColumnIndex, endColumnIndex, sheet_id):
    val = {
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": endRowIndex,
                "startColumnIndex": startColumnIndex,
                "endColumnIndex": endColumnIndex
            },
            "rows": [
            {
                "values": [{
                    "userEnteredFormat": {
                        "backgroundColor": {
                            "red": 193 / 255,
                            "green": 216 / 255,
                            "blue": 1
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment": "MIDDLE",
                    }
                }]
            }
        ],
        "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment)"
    }}
    return val


def get_format_colors_body(num_hws, num_tests, sheet_id):
    """
    body = {"requests": get_format_body(..., ..., ...)}
    """
    format_colors = [
        # Дерзнувший знать
        format_color(
            endRowIndex=2,
            startColumnIndex=0,
            endColumnIndex=1,
            sheet_id=sheet_id
        ),
        # Тесты
        format_color(
            endRowIndex=2,
            startColumnIndex=1,
            endColumnIndex=2,
            sheet_id=sheet_id
        ),
        # Дз
        format_color(
            endRowIndex=2,
            startColumnIndex=2,
            endColumnIndex=3,
            sheet_id=sheet_id
        ),
        # Проект
        format_color(
            endRowIndex=2,
            startColumnIndex=3,
            endColumnIndex=4,
            sheet_id=sheet_id
        ),
        # Рейтинг
        format_color(
            endRowIndex=2,
            startColumnIndex=4,
            endColumnIndex=5,
            sheet_id=sheet_id
        ),
        # Позиция
        format_color(
            endRowIndex=2,
            startColumnIndex=5,
            endColumnIndex=6,
            sheet_id=sheet_id
        ),
        # Домашки (много)
        format_color(
            endRowIndex=1,
            startColumnIndex=6,
            endColumnIndex=6 + num_hws,
            sheet_id=sheet_id
        ),
        # Тесты (много)
        format_color(
            endRowIndex=1,
            startColumnIndex=6 + num_hws,
            endColumnIndex=6 + num_hws + num_tests,
            sheet_id=sheet_id
        )
    ]

    return format_colors


def get_titles(course_data):
    values_hw_titles = []
    for _, hw_data in course_data["HWs"].items():
        values_hw_titles.append(hw_data['title'])
    values_test_titles = []
    for test_id, test_data in course_data["tests"].items():
        if test_id != "DD6M":
            values_test_titles.append(test_data['title'])
    
    return values_hw_titles, values_test_titles


def get_statement_body(course_data):
    values_hw_titles, values_test_titles = get_titles(course_data)

    num_hws = len(values_hw_titles)
    num_tests = len(values_test_titles)

    values = [["Дерзнувший знать", "🤖Тесты", "🤖ДЗ", "🤖Проект", "💥 Рейтинг", "🔥 Позиция"] + \
            ["🏡 ДЗ"] * num_hws + ["🧨 Тесты"] * num_tests
        ]
    
    offset = 6
    values.append([""]*offset + values_hw_titles + values_test_titles)

    students = course_data["students"]
    students.sort(key=itemgetter('name'))
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    oprosnik_test_id = "DD6M"

    student_cnt = 0
    tests_fisrt_col_letter = alphabet[offset + num_hws + 1] # +1 stands for excluding questionarrie
    tests_last_col_letter = alphabet[offset + num_hws + num_tests - 1]

    hws_first_col_letter = alphabet[offset]
    hws_last_col_letter = alphabet[offset + num_hws - 1]
    for student in students:
        raw = [
            student["name"], 
            f"=ROUND(AVERAGE({tests_fisrt_col_letter}{student_cnt + 3}:{tests_last_col_letter}{student_cnt + 3}), 2)",
            f"=ROUND(SUM({hws_first_col_letter}{student_cnt + 3}:{hws_last_col_letter}{student_cnt + 3}) / 'Service'!A2, 2)",
            f"=SUM(Project!B{student_cnt + 3}:E{student_cnt + 3})/20*100", # проект
            f"=ROUND(SUM(0.4 * B{student_cnt + 3} + 0.4 * C{student_cnt + 3} + 0.2 * D{student_cnt + 3}), 2)",
            f"=MATCH(E{student_cnt + 3}, SORT(E$3:E${len(students) + 3}, 1, FALSE), -1)"
        ]
        # WARN! str for json data only!
        #student_id = str(student["id"])
        student_id = student["id"]

        for hw_id, hw_data in course_data["HWs"].items():
            if student_id in hw_data["scores"].keys():
                raw.append(round(hw_data["scores"][student_id], 2))
            else:
                raw.append(0)
        for test_id, test_data in course_data["tests"].items():
            if test_id == oprosnik_test_id:
                continue
            if student_id in test_data["entered_students"]:
                if student_id in test_data["scores"].keys():
                    total_score = 0
                    for q_id, q_score in test_data["scores"][student_id].items():
                        if q_score:
                            total_score += float(q_score)
                    raw.append(round(total_score, 2))
                #else student_id in test_data["answers"].keys():
                else:
                    raw.append(0)
            elif student_id in test_data["scores"].keys():
                total_score = 0
                for q_id, q_score in test_data["scores"][student_id].items():
                    if q_score:
                        total_score += float(q_score)
                raw.append(round(total_score, 2))
            else:
                raw.append(0)
        values.append(raw)
        student_cnt += 1
    return values


def get_clear_body(sheet_id):
    """
    Usage example:
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=get_clear_body(sheet_id)
    ).execute()
    """
    request_body = {
        'requests': [
            {
                'updateCells': {
                    'range': {
                        'sheetId': sheet_id
                    },
                    'fields': 'userEnteredValue'
                }
            },
            {
                'unmergeCells': {
                    'range': {
                        'sheetId': sheet_id
                    }
                }
            }
        ]
    }
    return request_body


async def update_statement(course_data):
    DEBUG = False
    test_spreadsheet_id = "1xNiWYE-sWCaWKv9WRmC5nrZpepTmXGHbB1sAsN5rI_I"
    test_sheet_id = "0"
    try:
        spreadsheet_id = "1_UU-6W8JnJ2Fbi1_sws29L-hfyJGt680jsNWIpFN03c"
        sheet_id = "0"

        if DEBUG:
            spreadsheet_id = test_spreadsheet_id
            sheet_id = test_sheet_id

        service = authentificate()

        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=get_clear_body(sheet_id)
        ).execute()

        values_hw_titles, values_test_titles = get_titles(course_data)
        format_cells = get_format_cells_body(
            num_hws=len(values_hw_titles),
            num_tests=len(values_test_titles),
            sheet_id=sheet_id
        )
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": format_cells}
        ).execute()

        format_colors = get_format_colors_body(
            num_hws=len(values_hw_titles),
            num_tests=len(values_test_titles),
            sheet_id=sheet_id
        )
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": format_colors}
        ).execute()

        values = get_statement_body(course_data)
        resp =  service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body= {
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {
                        "range": "A1:AZ200",
                        "majorDimension": "ROWS",
                        "values": values
                    }
                ]
            }
        ).execute()
    except Exception as ex:
        logging.error(traceback.format_exc())


if __name__ == '__main__':
    try:
        spreadsheet_id = "1_UU-6W8JnJ2Fbi1_sws29L-hfyJGt680jsNWIpFN03c"
        sheet_id = "0"

        service = authentificate()

        with open("data.json", "r") as file:
            data = json.load(file)

        bot_data = data["bot_data"]

        values_hw_titles, values_test_titles = get_titles(bot_data["courses"]["BLM4"])
        format_cells = get_format_cells_body(
            num_hws=len(values_hw_titles),
            num_tests=len(values_test_titles),
            sheet_id=sheet_id
        )
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": format_cells}
        ).execute()

        format_colors = get_format_colors_body(
            num_hws=len(values_hw_titles),
            num_tests=len(values_test_titles),
            sheet_id=sheet_id
        )
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": format_colors}
        ).execute()

        values = get_statement_body(bot_data["courses"]["BLM4"])
        resp = service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body= {
                "valueInputOption": "USER_ENTERED",
                "data": [
                    {
                        "range": "A1:AZ200",
                        "majorDimension": "ROWS",
                        "values": values
                    }
                ]
            }
        ).execute()
    except Exception as ex:
        logging.error(traceback.format_exc())
