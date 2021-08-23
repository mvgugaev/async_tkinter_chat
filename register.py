"""Набор функций для регистрации в чате."""
import logging
import asyncio
import tkinter as tk
from tkinter import messagebox
from anyio import create_task_group
from async_timeout import timeout as async_timeout
from gui import update_tk
from utils import get_parser
from auntification import register, UserStateReceived, RegisterReceived

register_response_queue = asyncio.Queue()
register_request_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()

TOKEN_FILE_NAME = 'token.txt'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('register')


def parse_arguments():
    """Функция обработки аргументов командной строки."""
    parser = get_parser(
        'Async app to register in chat.',
        'config.conf',
    )
    parser.add_arg(
        '-ho', 
        '--host', 
        help='Server HOST',
    )
    parser.add_arg(
        '-wp',
        '--write_port', 
        help='Server PORT to write messages',
    )
    config, _ = parser.parse_known_args()
    return config


async def register_from_queue(host: str, port: str, token_file_name: str, register_request_queue, register_response_queue, status_updates_queue, logger):
    """Асинхронная функция для регистрации пользователя при получении сообщения из очереди."""
    while True:
        username = await register_request_queue.get()
        try:
            async with async_timeout(3) as _:
                await register(
                    host,
                    port,
                    username,
                    token_file_name,
                    register_response_queue,
                    status_updates_queue,
                    logger,
                )
        except asyncio.exceptions.TimeoutError:
            register_response_queue.put_nowait(
                RegisterReceived(False, '', '')
            )
            status_updates_queue.put_nowait(
                UserStateReceived(
                    'не определено',
                    'не активен',
                )
            )


def create_status_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    nickname_label = tk.Label(status_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.pack(side="top", fill=tk.X)

    token_lable = tk.Label(status_frame, height=1, fg='grey', font='arial 10', anchor='w')
    token_lable.pack(side="top", fill=tk.X)

    return (nickname_label, token_lable)


def process_new_register(input_field, register_request_queue):
    text = input_field.get()
    register_request_queue.put_nowait(text)



async def update_status_panel(status_labels, status_updates_queue):
    nickname_label, token_lable = status_labels

    nickname_label['text'] = f'Ник: не определено'
    token_lable['text'] = f'Токен: не активен'

    while True:
        status_message = await status_updates_queue.get()
        nickname_label['text'] = f'Ник: {status_message.nickname}'
        token_lable['text'] = f'Токен: {status_message.status}'


async def update_alerts(register_response_queue):
    while True:
        register_response = await register_response_queue.get()

        if register_response.status:
            messagebox.showinfo(
                'Пользователь зарегистрирован',
                f'Ник: {register_response.nickname}\n' +
                f'Токен: {register_response.token} \n' +
                'Токен записан в файл и готов к использованию в чате.'
            )
        else:
            messagebox.showinfo(
                'Ошибка регистрации',
                'Попробуйте повторить операцию',
            )


async def draw(register_response_queue, register_request_queue, status_updates_queue):
    root = tk.Tk()
    root.title('Регистрация')
    
    root_frame = tk.Frame()
    root_frame.grid()
    root_frame.pack(
        fill="both", 
        expand=True, 
        padx=20, 
        pady=20,
    )

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side='top', fill=tk.X)

    input_field = tk.Entry(input_frame)
    input_field.pack(side='left', fill=tk.X, expand=True, pady=5)

    register_button = tk.Button(
        root_frame, 
        text="Зарегистрировать", 
        width=15, 
        height=3,
    )
    register_button.pack()
    register_button["command"] = lambda: process_new_register(
            input_field, 
            register_request_queue,
    )
    status_labels = create_status_panel(root_frame)
    
    async with create_task_group() as tg:
        tg.start_soon(
            update_tk,
            root_frame,
        )

        tg.start_soon(
            update_status_panel,
            status_labels,
            status_updates_queue,
        )

        tg.start_soon(
            update_alerts,
            register_response_queue,
        )


async def main():
    args = parse_arguments()
    async with create_task_group() as tg:
        tg.start_soon(
            draw,
            register_response_queue,
            register_request_queue,
            status_updates_queue,
        )

        tg.start_soon(
            register_from_queue,
            args.host,
            args.write_port,
            TOKEN_FILE_NAME,
            register_request_queue,
            register_response_queue,
            status_updates_queue,
            logger,
        )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
