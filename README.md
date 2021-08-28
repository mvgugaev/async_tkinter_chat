# Async chat application with interface
Асинхронный чат с возможностью регистрации и интерфейсом. Развернуть проект:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Регистрация
```
python3 register.py
```
Базовые настройки можно изменить в файле config.conf. Токен пользователя сохраняется в файле token.txt и используется в чате.

### Чат
```
python3 main.py
```

### flake8 check
```
flake8 .
```