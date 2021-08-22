import asyncio
import logging
import datetime
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
    return parser.parse_args()


async def generate_msgs(messages_queue, host: str, port: str):
    while True:
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
        async with open_connection(host, port, logger) as (reader, _):
            status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            while not reader.at_eof():
                text_from_chat = await read_and_print_from_socket(reader, logger)
                date_string = datetime.datetime.now().strftime("%d.%m.%y %H:%M")
                messages_queue.put_nowait(f'[{date_string}] {text_from_chat}')
                await asyncio.sleep(1)
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


async def main():
    args = parse_arguments()
    await asyncio.gather(
        gui.draw(messages_queue, sending_queue, status_updates_queue),
        generate_msgs(
            messages_queue,
            args.host,
            args.read_port,
        ),
    )



loop.run_until_complete(main())