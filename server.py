"""Набор асинхронных корутин для работы с сервером."""
import asyncio
import datetime
import time
import gui
from async_timeout import timeout as async_timeout
from anyio import create_task_group
from auntification import authorize
from utils import (
    reconnect,
    open_connection,
    read_and_print_from_socket,
    change_timeout_to_connection_error,
    write_to_socket,
)


@change_timeout_to_connection_error
async def ping_server(watchdog_queue, host: str, port: str, logger, timeout: float = 0.3, interval: float = 0.3):
    """Корутина для отправки пустого сообщения раз в <interval> секунд и запись в watchdog_queue. В случае превышения <timeout> вызывается ConnectionError."""
    async with open_connection(host, port, logger) as (_, writer):
        while True:
            async with async_timeout(timeout) as cm:
                if writer.is_closing():
                    await writer.wait_closed()
                    raise ConnectionError

                await submit_message(
                    writer,
                    '',
                    logger,
                )
                watchdog_queue.put_nowait('Message sent')
            await asyncio.sleep(interval)


@change_timeout_to_connection_error
async def watch_for_connection(watchdog_queue, logger, timeout: float = 1.5):
    """Асинхронная корутина, которая опрашивает очередь watchdog_queue и ожидает сообщения минимум раз в <timeout>."""
    while True:
        async with async_timeout(timeout) as cm:
            message = await watchdog_queue.get()
            logger.debug(f'[{time.time()}] Connection is alive. {message}')


async def submit_message(writer, message: str, logger):
    """Асинхронная функция для отправки сообщения в чат."""
    await write_to_socket(
        writer,
        '{}\n\n'.format(message.replace("\n", "\\n")),
        logger,
    )


async def send_msgs(sending_queue, status_queue, watchdog_queue, host: str, port: str, logger, token_file_path: str):
    """Асинхронная функция для отправки сообщений из очереди sending_queue в чат."""
    while True:
        status_queue.put_nowait(gui.NicknameReceived('Неизвестно'))
        status_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
        async with open_connection(host, port, logger) as (reader, writer):
            status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            watchdog_queue.put_nowait('Prompt before auth')
            username = await authorize(
                reader,
                writer,
                logger,
                token_file_path,
            )
            watchdog_queue.put_nowait('Authorization done')
            status_queue.put_nowait(gui.NicknameReceived(username))
            status_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
            while True:
                if writer.is_closing():
                    await writer.wait_closed()
                    break
                
                message = await sending_queue.get()
                await submit_message(
                    writer,
                    message,
                    logger,
                )
                watchdog_queue.put_nowait('Message sent')
        status_queue.put_nowait(gui.SendingConnectionStateChanged.CLOSED)


async def generate_msgs(messages_queue, messages_history_queue, status_queue, watchdog_queue, host: str, port: str, logger):
    """Асинхронная функция для чтения сообщений из чата и наполнения очередей messages_queue и messages_history_queue."""
    while True:
        status_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
        async with open_connection(host, port, logger) as (reader, _):
            status_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
            while not reader.at_eof():
                text_from_chat = await read_and_print_from_socket(reader, logger)
                date_string = datetime.datetime.now().strftime('%d.%m.%y %H:%M')
                message = f'[{date_string}] {text_from_chat}'
                messages_history_queue.put_nowait(message)
                messages_queue.put_nowait(message)
                watchdog_queue.put_nowait('New message in chat')
                await asyncio.sleep(1)
            
        status_queue.put_nowait(gui.ReadConnectionStateChanged.CLOSED)


@reconnect
async def handle_connection(args, messages_queue, messages_history_queue, status_updates_queue, watchdog_queue, sending_queue, logger, watchdog_logger, token_file_path: str):
    """Группа задач для работы с сервером."""
    async with create_task_group() as tg:
        tg.start_soon(
            ping_server,
            watchdog_queue,
            args.host,
            args.write_port,
            watchdog_logger,
        )

        tg.start_soon(
            generate_msgs,
            messages_queue,
            messages_history_queue,
            status_updates_queue,
            watchdog_queue,
            args.host,
            args.read_port,
            logger,
        )

        tg.start_soon(
            send_msgs,
            sending_queue,
            status_updates_queue,
            watchdog_queue,
            args.host,
            args.write_port,
            logger,
            token_file_path,
        )

        tg.start_soon(
            watch_for_connection,
            watchdog_queue,
            watchdog_logger,
        )
