import json
from anyio import ExceptionGroup
import asyncio
import decorator
from pathlib import Path
from socket import gaierror
import configargparse
from contextlib import asynccontextmanager


@decorator.decorator
async def change_timeout_to_connection_error(task, *args, **kwargs):
    """Декоратор, который переводит asyncio.exceptions.TimeoutError > ConnectionError"""
    try:
        res = await task(*args, **kwargs)
        return res
    except asyncio.exceptions.TimeoutError:
        raise ConnectionError

@decorator.decorator
async def reconnect(task, *args, **kwargs):
    """Декоратор для перезапуска карутины в случае ConnectionError и gaierror."""
    while True:
        try:
            result = await task(*args, **kwargs)
            return result
        except (ConnectionError, gaierror):
            await asyncio.sleep(0.5)
        except ExceptionGroup as ex_group:
            for ex in ex_group.exceptions:
                if not isinstance(ex, (ConnectionError, gaierror)):
                    raise ex

        await asyncio.sleep(0.5)


def convert_json_string_to_object(json_string: str):
    """Конвертация строки в json -> result (None в случае некорректной JSON строки)."""
    try:
        return json.loads(json_string)
    except ValueError:
        return None


async def write_to_socket(writer, message: str, logger):
    """Метод для отправки текста в сокет."""
    writer.write(message.encode())
    logger.debug(message.rstrip())
    await writer.drain()


async def read_and_print_from_socket(reader, logger):
    """Метод для чтения и вывода строки из сокета."""
    string_from_chat = (await reader.readline()).decode().rstrip()
    logger.debug(string_from_chat)
    return string_from_chat


async def close_connection(writer, logger):
    """Закрытие соединения с сокетом."""
    logger.debug('Close the connection')
    writer.close()
    await writer.wait_closed()


def get_parser(description: str, config_file: str):
    """Функция для генерации парсера аргументов командной строки."""
    return configargparse.ArgParser(
        default_config_files=[
            str(Path.cwd() / config_file),
        ],
        description=description,
    )

@asynccontextmanager
async def open_connection(host: str, port: int, logger):
    """Контекстный менеджер для открытия tcp соединения"""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        await close_connection(writer, logger)
