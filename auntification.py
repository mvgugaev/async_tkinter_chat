import aiofiles
from utils import (
    open_connection,
    close_connection,
    convert_json_string_to_object,
    write_to_socket,
    read_and_print_from_socket,
)


class UserStateReceived:
    """Состояние пользователя в процессе регистрации."""

    def __init__(self, status, nickname):
        self.status = status
        self.nickname = nickname


class RegisterReceived:
    """Данные для регистрации."""

    def __init__(self, status: bool, nickname, token):
        self.status = status
        self.nickname = nickname
        self.token = token


class InvalidToken(Exception):
    pass


async def authorize(reader, writer, logger, token_file, token=None):
    await read_and_print_from_socket(reader, logger)
    if not token:
        async with aiofiles.open(token_file, mode='r') as token_file:
            token = await token_file.read()

    await write_to_socket(writer, f'{token.rstrip()}\n', logger)
    json_response = await read_and_print_from_socket(reader, logger)
    response = convert_json_string_to_object(json_response)
    if not response:
        logger.debug(
            'Неизвестный токен. Проверьте его или зарегистрируйте заново.',
        )
        raise InvalidToken()

    await read_and_print_from_socket(reader, logger)
    return response['nickname']


async def register(
    host: str,
    port: str,
    name: str,
    token_file_name: str,
    register_response_queue,
    status_updates_queue,
    logger,
):
    async with open_connection(host, port, logger) as (reader, writer):
        await read_and_print_from_socket(reader, logger)
        await write_to_socket(writer, '\n', logger)
        await read_and_print_from_socket(reader, logger)

        await write_to_socket(
            writer,
            '{}\n'.format(name.replace("\n", "\\n")),
            logger,
        )

        json_response = await read_and_print_from_socket(reader, logger)
        response = convert_json_string_to_object(json_response)
        if not response:
            logger.debug('Не удалось получить токен. Повторите попытку.')
            await close_connection(writer, logger)
            return False

        hash, nickname = response['account_hash'], response['nickname']  # noqa: E501

        async with aiofiles.open(token_file_name, mode='w') as token_file:
            await token_file.write(hash)

        register_response_queue.put_nowait(
            RegisterReceived(
                True,
                nickname,
                hash,
            )
        )

        status_updates_queue.put_nowait(
            UserStateReceived(
                nickname,
                'активен',
            )
        )
