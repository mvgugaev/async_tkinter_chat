"""Набор функций для авторизации в чате."""
import aiofiles
from utils import (
    convert_json_string_to_object, 
    write_to_socket, 
    read_and_print_from_socket,
)

class InvalidToken(Exception):
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
