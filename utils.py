import json
import asyncio
from pathlib import Path
import configargparse
from contextlib import asynccontextmanager


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