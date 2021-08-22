import asyncio
import logging
import datetime
import aiofiles
from pathlib import Path
import gui
from utils import (
    get_parser,
    open_connection,
    read_and_print_from_socket,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('reader')

loop = asyncio.get_event_loop()

messages_queue = asyncio.Queue()
messages_history_queue = asyncio.Queue()
sending_queue = asyncio.Queue()
status_updates_queue = asyncio.Queue()


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


async def save_messages(filepath, messages_history_queue):
    while True:
        async with aiofiles.open(Path(filepath), mode='a') as history_file:
            history_message = await messages_history_queue.get()
            await history_file.write(f'{history_message}\n')


def load_history(filepath, messages_queue):
    with open(Path(filepath), mode='r') as history_file:
        for message in history_file:
            messages_queue.put_nowait(message.rstrip())


async def generate_msgs(messages_queue, messages_history_queue, status_queue, host: str, port: str):
    while True:
        status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
        async with open_connection(host, port, logger) as (reader, _):
            status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            while not reader.at_eof():
                text_from_chat = await read_and_print_from_socket(reader, logger)
                date_string = datetime.datetime.now().strftime("%d.%m.%y %H:%M")
                message = f'[{date_string}] {text_from_chat}'
                messages_history_queue.put_nowait(message)
                messages_queue.put_nowait(message)
                await asyncio.sleep(1)
            
        status_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


async def main():
    args = parse_arguments()
    load_history(
        args.history,
        messages_queue,
    )
    await asyncio.gather(
        gui.draw(
            messages_queue, 
            sending_queue, 
            status_updates_queue,
        ),
        generate_msgs(
            messages_queue,
            messages_history_queue,
            status_updates_queue,
            args.host,
            args.read_port,
        ),
        save_messages(
            args.history,
            messages_history_queue,
        )
    )

loop.run_until_complete(main())
