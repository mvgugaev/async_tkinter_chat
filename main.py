"""Главный модуль асинхронного чата с интерфейсом."""
import asyncio
import logging
import aiofiles
from pathlib import Path
from tkinter import messagebox
import gui
from utils import get_parser
from server import handle_connection
from auntification import InvalidToken
from anyio import create_task_group

TOKEN_FILE_PATH = 'token.txt'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('reader')
watchdog_logger = logging.getLogger('watchdog')

logger.propagate = False

messages_queue = asyncio.Queue()
messages_history_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()
watchdog_queue = asyncio.Queue()


def parse_arguments():
    """Функция обработки аргументов командной строки."""
    parser = get_parser(
        'Async app to read tcp chat.',
        'config.conf',
    )
    parser.add_arg(
        '-ho',
        '--host',
        help='Server HOST',
    )
    parser.add_arg(
        '-rp',
        '--read_port',
        help='Server PORT to read messages',
    )
    parser.add_arg(
        '-wp',
        '--write_port',
        help='Server PORT to write messages',
    )
    parser.add_arg(
        '-hi',
        '--history',
        help='File to store messages',
    )
    return parser.parse_args()


async def save_messages(filepath: str, messages_history_queue):
    """Асинхронная функция для сохранения сообщений в файл истории."""
    while True:
        async with aiofiles.open(Path(filepath), mode='a') as history_file:
            history_message = await messages_history_queue.get()
            await history_file.write(f'{history_message}\n')


def load_history(filepath: str, messages_queue) -> None:
    """Функция для загрузки истории в очередь messages_queue."""
    if Path(filepath).is_file():
        with open(Path(filepath), mode='r') as history_file:
            for message in history_file:
                messages_queue.put_nowait(message.rstrip())


async def run_application():
    """Асинхронная функция для запуска чата."""
    args = parse_arguments()
    load_history(
        args.history,
        messages_queue,
    )
    try:
        async with create_task_group() as tg:
            tg.start_soon(
                gui.draw,
                messages_queue,
                sending_queue,
                status_updates_queue,
            )

            tg.start_soon(
                handle_connection,
                args,
                messages_queue,
                messages_history_queue,
                status_updates_queue,
                watchdog_queue,
                sending_queue,
                logger,
                watchdog_logger,
                TOKEN_FILE_PATH,
            )

            tg.start_soon(
                save_messages,
                args.history,
                messages_history_queue,
            )

    except InvalidToken:
        messagebox.showinfo(
            'Неверный токен',
            'Проверьте токен, сервер его не узнал.',
        )


def main():
    """Функция для запуска логики приложения."""
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_application())
    except (KeyboardInterrupt, gui.TkAppClosed):
        logger.debug('Приложение закрыто.')


if __name__ == '__main__':
    main()
