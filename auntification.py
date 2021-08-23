"""Набор функций для авторизации в чате."""
import aiofiles
from utils import (
    open_connection,
    close_connection,
    convert_json_string_to_object, 
    write_to_socket, 
    read_and_print_from_socket,
)


class UserStateReceived:
    """Класс состояния пользователя в процессе регистрации."""

    def __init__(self, status, nickname):
        self.status = status
        self.nickname = nickname


class RegisterReceived:
    """Класс с данными регистрации."""

    def __init__(self, status: bool, nickname, token):
        self.status = status
        self.nickname = nickname
        self.token = token


class InvalidToken(Exception):
    """Исключение некорректного токена пользователя."""
    pass


async def authorize(reader, writer, logger, token_file, token = None):
    """Асинхронная функция для авторизации в чате."""
    await read_and_print_from_socket(reader, logger)
    if not token:
        async with aiofiles.open(token_file, mode='r') as token_file:
            token = await token_file.read()

    await write_to_socket(writer, f'{token.rstrip()}\n', logger)
    response = await read_and_print_from_socket(reader, logger)
    json_response = convert_json_string_to_object(response)
    if not json_response:
        logger.debug('Неизвестный токен. Проверьте его или зарегистрируйте заново.')
        raise InvalidToken()
    
    await read_and_print_from_socket(reader, logger)
    return json_response['nickname']


async def register(host: str, port: str, name: str, token_file_name: str, register_response_queue, status_updates_queue, logger):
    """Асинхронная функция для регистрации в чате."""
    async with open_connection(host, port, logger) as (reader, writer):
        await read_and_print_from_socket(reader, logger)
        await write_to_socket(writer, '\n', logger)
        await read_and_print_from_socket(reader, logger)
            
        await write_to_socket(
            writer, 
            '{}\n'.format(name.replace("\n", "\\n")), 
            logger,
        )

        response = await read_and_print_from_socket(reader, logger)
        json_response = convert_json_string_to_object(response)
        if not json_response:
            logger.debug('Не удалось получить токен. Повторите попытку.')
            await close_connection(writer, logger)
            return False

        hash, nuckname = json_response['account_hash'], json_response['nickname']

        async with aiofiles.open(token_file_name, mode='w') as token_file:
            await token_file.write(hash)

        register_response_queue.put_nowait(
            RegisterReceived(
                True,
                nuckname,
                hash,
            )
        )

        status_updates_queue.put_nowait(
            UserStateReceived(
                nuckname,
                'активен',
            )
        )
