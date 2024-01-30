# main.py
#   
#-> python3 main.py -t="FMIN_TEST_BOT_TOKEN" -p="fmin_data"
#
import argparse
import os
import sys
import logging
from telegram import Update
from telegram.ext import (
    PicklePersistence,
    ApplicationBuilder,
    MessageHandler,
    filters
)
from handlers.handlers import mode_conv, unknown

logging.getLogger("httpx").setLevel(logging.WARNING)


def _main(token_name: str, persistence_file_path: str):
    token = os.environ[token_name]

    persistence = PicklePersistence(filepath=persistence_file_path, update_interval=1)
    application = ApplicationBuilder().token(token).persistence(persistence).build()

    application.add_handler(mode_conv)
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='fmin Bot')
    parser.add_argument('-t', '--tokenname', help='Name of venv variable with Token')
    parser.add_argument('-p', '--persistance', help='Path to persistance file')
    args = vars(parser.parse_args())
    token_name = args['tokenname']
    persistence_file_path = args['persistance']
    _main(
        token_name=token_name,
        persistence_file_path=persistence_file_path
    )

