# MAISON Restaurant

Backend ресторанного приложения: Django 5.2, Django REST Framework и PostgreSQL 16.
Сохранены приложения `catalog`, `cart`, `staff`, `reservations`, `reservation_api`.
Реализованы гостевая корзина с API управления позициями и минимальная модель блюда
(`Dish`: название и цена).

## Переменные окружения

Из корня проекта скопируйте пример, если `backend/.env` ещё не существует:

```bash
cp backend/.env.example backend/.env
```

В `backend/.env` замените `SECRET_KEY` и `DB_PASSWORD` собственными значениями.
Ключ можно сгенерировать командой:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Файл `.env` исключён из Git и Docker-образа. Не публикуйте его.
`DEBUG=True` предназначен для локальной разработки; по умолчанию в настройках
используется `False`. `ALLOWED_HOSTS` — список разрешённых хостов через запятую.
`CORS_ALLOWED_ORIGINS` — разрешённые адреса frontend через запятую, включая схему и
порт, например `http://localhost:5173`. По умолчанию список пуст. Для разрешённых
адресов API принимает заголовок `X-Cart-Token` и позволяет JavaScript прочитать его
из ответа.

## Запуск через Docker Compose

Нужны Docker Engine и Docker Compose. Выполняйте команды из корня проекта:

```bash
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up --build -d
docker compose --env-file backend/.env ps
docker compose --env-file backend/.env logs backend
```

Всегда передавайте `--env-file backend/.env`: Compose использует его для настроек
PostgreSQL, а Backend получает окружение из этого же файла. В контейнере Backend
`DB_HOST` и `DB_PORT` переопределены на `db:5432`. PostgreSQL не публикует порт на хосте.

Backend ждёт успешного healthcheck PostgreSQL, применяет миграции Django и запускает
сервер на `http://127.0.0.1:8000`. В этой конфигурации используется `runserver` для
локальной разработки. Для production нужны отдельная конфигурация и WSGI/ASGI-сервер.

Данные PostgreSQL сохраняются в именованном томе `postgres_data`.
Обычная остановка сохраняет данные:

```bash
docker compose --env-file backend/.env down
```

Не добавляйте `-v`, если хотите сохранить базу. `DB_NAME`, `DB_USER` и `DB_PASSWORD`
инициализируют PostgreSQL при первом запуске с пустым томом. Правка `.env` сама по
себе не меняет пользователей или пароли в уже созданной базе.

## Проверки и команды Django

```bash
docker compose --env-file backend/.env exec backend python manage.py check
docker compose --env-file backend/.env exec backend python manage.py test
docker compose --env-file backend/.env exec backend python manage.py migrate
docker compose --env-file backend/.env exec backend python manage.py createsuperuser
docker compose --env-file backend/.env exec backend python manage.py shell -c 'from django.db import connection; connection.ensure_connection(); print(connection.vendor)'
curl -f http://127.0.0.1:8000/health/
curl -f -H 'Accept: application/json' http://127.0.0.1:8000/api/v1/health/
```

Оба проверочных URL возвращают `{"status": "ok", "project": "MAISON Restaurant"}`.
Они проверяют HTTP-маршрутизацию, а не состояние базы; подключение проверяет
отдельная команда `connection.ensure_connection()` выше.

Админка доступна на `/admin/`, вход для интерфейса DRF — на `/api-auth/login/`.
Для будущих API по умолчанию включены `SessionAuthentication`, `BasicAuthentication`
и доступ только аутентифицированным пользователям (`IsAuthenticated`). Проверочный
маршрут `/api/v1/health/` открыт всем и поддерживает GET и OPTIONS.
Каталог пока не имеет API. Гостевая корзина доступна без авторизации по адресу
`/api/v1/cart/`.

## Гостевая корзина

Первый запрос `POST /api/v1/cart/` без `X-Cart-Token` создаёт пустую корзину
(`201 Created`). Клиент сохраняет UUID из заголовка ответа `X-Cart-Token` и
передаёт его в следующих запросах. Токен даёт доступ к корзине: не публикуйте его.

`GET /api/v1/cart/` с этим заголовком возвращает количество товаров и общую
стоимость, например `{"total_quantity": 3, "total_price": "375.30"}`. Денежное
значение передаётся строкой; расчёт использует `Decimal` и текущие цены блюд.
`POST` с действительным токеном возвращает существующую корзину (`200 OK`).
Успешные ответы содержат `X-Cart-Token` и запрещают кеширование.

Без токена `GET` возвращает `400`. Некорректный или пустой токен возвращает `400`,
неизвестный UUID — `404`; новая корзина при этом не создаётся. `OPTIONS` также не
создаёт корзину.

Для всех операций с позициями обязателен `X-Cart-Token` существующей корзины:

| Метод и URL | JSON запроса | Результат |
| --- | --- | --- |
| `POST /api/v1/cart/items/` | `{"dish_id": 1, "quantity": 2}` | `201` для новой позиции, `200` при увеличении количества существующей |
| `PATCH /api/v1/cart/items/{id}/` | `{"quantity": 3}` | `200`, количество заменяется на указанное |
| `DELETE /api/v1/cart/items/{id}/` | Не требуется | `204`, пустое тело ответа |

`POST` и `PATCH` возвращают позицию в формате
`{"id": 1, "dish_id": 1, "quantity": 3}`. В URL используется `id` позиции, а в
теле `POST` — идентификатор блюда `dish_id`. Для актуальных итогов используйте
прежний `GET /api/v1/cart/`.

Количество обязательно: целое число от 1 до 2147483647. Ошибки входных данных,
включая неизвестное блюдо и переполнение количества при повторном добавлении,
возвращают `400` с ошибками по полям. Несуществующая позиция и позиция чужой
корзины возвращают одинаковую ошибку `404`. Нулевое количество не удаляет товар;
для удаления нужен `DELETE`. Ошибочные запросы не создают корзины или позиции.

В `apps/cart/services.py` доступны создание корзины, проверка и поиск по токену,
получение позиций с блюдами, расчёт суммарного количества и стоимости, добавление,
изменение и удаление позиций. Позиции связаны с `catalog.Dish`; база запрещает
количество меньше 1 и повтор одного блюда в одной корзине. Корзины и позиции
зарегистрированы в Django Admin.
Операции API над позициями обновляют `Cart.updated_at`. Изменения выполняются
в транзакции с блокировкой корзины, включая первое добавление блюда.

## Запуск без Docker

Нужны Python 3.12+ и работающий PostgreSQL 16. Создайте отдельную базу и пользователя
с паролем, укажите их в `backend/.env`. Для локальных тестов с базой Django пользователю
нужно право `CREATEDB`. Настройте `DB_HOST` и `DB_PORT` на адрес вашей базы.
SQLite не используется.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
set -a
source backend/.env
set +a
cd backend
python manage.py check
python manage.py migrate
python manage.py test
python manage.py runserver
```

Django сам не читает `.env`: при запуске без Docker переменные загружаются в shell
командами выше. Используйте собственный доверенный `.env` в совместимом с Bash формате.

## Структура

- `backend/config/` — настройки, маршрутизация, ASGI/WSGI, проверочные представления.
- `backend/apps/` — `cart` с моделями, сервисами и API гостевой корзины,
  минимальная модель `catalog.Dish` и заготовки остальных приложений.
- `backend/tests/` — проверки базовых маршрутов.
- `backend/Dockerfile`, `docker-compose.yml` — локальное окружение Django и PostgreSQL.
- `docs/architecture.md`, `docs/team-responsibilities.md` — архитектура и распределение задач.

JWT, API каталога, frontend и production-развёртывание пока не настроены.
