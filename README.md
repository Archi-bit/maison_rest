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
`DEBUG=True` можно использовать при запуске `runserver` без Docker. По умолчанию
Django использует `False`, и Compose всегда запускает Backend с `DEBUG=False`.
`ALLOWED_HOSTS` — список разрешённых хостов через запятую, без схемы и порта.
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
docker compose --env-file backend/.env logs --tail=100 backend db nginx
```

Всегда передавайте `--env-file backend/.env`: Compose использует его для настроек
PostgreSQL, а Backend получает окружение из этого же файла. В контейнере Backend
`DB_HOST` и `DB_PORT` переопределены на `db:5432`. На хосте публикуется только порт
Nginx. Значение `HTTP_BIND` по умолчанию — `127.0.0.1:80`.

Backend ждёт готовности PostgreSQL, применяет миграции, выполняет `collectstatic`
и запускает Gunicorn. Nginx проксирует запросы к Gunicorn, раздаёт `/static/` из
тома `static_files` и `/media/` из тома `media_files`. Локальный адрес —
`http://127.0.0.1`. Тома доступны Nginx только для чтения.

Данные PostgreSQL сохраняются в именованном томе `postgres_data`.
Обычная остановка сохраняет данные:

```bash
docker compose --env-file backend/.env down
```

Не добавляйте `-v`, если хотите сохранить базу. `DB_NAME`, `DB_USER` и `DB_PASSWORD`
инициализируют PostgreSQL при первом запуске с пустым томом. Правка `.env` сама по
себе не меняет пользователей или пароли в уже созданной базе.

## Развёртывание на Ubuntu Server (AWS EC2)

1. На подготовленном сервере установите Git (`sudo apt update` и
   `sudo apt install git`), затем установите Docker Engine и Compose Plugin из
   официального apt-репозитория по [инструкции Docker][docker-ubuntu]. Проверьте
   `docker version` и `docker compose version`. Если пользователь работает с
   Docker через `sudo`, используйте `sudo docker` в командах ниже.
2. В [группе безопасности EC2][ec2-security-group] разрешите SSH (`22/TCP`)
   с административного IP и HTTP (`80/TCP`) с адресов, которым нужен пробный
   доступ. До настройки HTTPS используйте HTTP для проверки на тестовых данных.
3. Клонируйте из GitHub **репозиторий учебного проекта**:

   ```bash
   git clone 'URL_УЧЕБНОГО_РЕПОЗИТОРИЯ' maison
   cd maison
   cp backend/.env.example backend/.env
   chmod 600 backend/.env
   ```

4. Заполните `backend/.env` на сервере:

   | Переменная | Значение |
   | --- | --- |
   | `SECRET_KEY` | Новый случайный ключ для сервера |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | Реальный публичный IP EC2 без `http://` и порта. Добавьте `127.0.0.1` для проверок с самого сервера |
   | `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Имя базы, пользователь и новый случайный пароль PostgreSQL |
   | `CORS_ALLOWED_ORIGINS` | Адреса frontend со схемой и портом через запятую. Если frontend ещё нет, оставьте пустым |
   | `HTTP_BIND` | `0.0.0.0:80` для внешнего доступа |

5. Из корня проекта выполните команды из разделов «Запуск через Docker Compose»
   и «Проверки и команды Django». С компьютера с разрешённым доступом откройте
   `http://<IP-EC2>/api/v1/health/`. Страница `/admin/login/` должна открываться
   со стилями Django. Маршрут `/media/` отдаёт существующие файлы из `media_files`.
   У модели `Dish` пока нет поля изображения, поэтому загрузки через каталог нет.

Для перезапуска Backend и обновления версии используйте команды из корня проекта:

```bash
# Перезапуск текущей версии
docker compose --env-file backend/.env restart backend

# Обновление. Сделайте резервную копию PostgreSQL и медиа перед обновлением.
git pull --ff-only
docker compose --env-file backend/.env config --quiet
docker compose --env-file backend/.env up --build -d
docker compose --env-file backend/.env exec nginx nginx -t
docker compose --env-file backend/.env restart nginx
docker compose --env-file backend/.env logs --tail=100 backend db nginx
```

При изменении `.env` примените `docker compose --env-file backend/.env up -d`.

[docker-ubuntu]: https://docs.docker.com/engine/install/ubuntu/
[ec2-security-group]: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/security-group-rules-reference.html

## HTTPS на тестовом EC2

Тестовые адреса — `https://maison-rest.duckdns.org/api/v1/health/` и
`https://maison-rest.duckdns.org/api/swagger/`. Для HTTPS запускайте Compose с
`-f docker-compose.yml -f docker-compose.https.yml` из `/home/ubuntu/maison-test`.
Задайте в серверном `backend/.env` `HTTPS_BIND=0.0.0.0:443`, добавьте
`maison-rest.duckdns.org` в `ALLOWED_HOSTS` и задайте
`CSRF_TRUSTED_ORIGINS=https://maison-rest.duckdns.org`. Включите `HTTPS_ENABLED=True`
для безопасных cookie и доверия заголовку схемы от Nginx.

При первой настройке проверьте DNS и HTTP снаружи EC2. Установите `certbot` из
репозитория Ubuntu и создайте `/var/www/maison-acme`, `/etc/letsencrypt` и
`/etc/maison-test/nginx`. Запустите Nginx с обоими файлами Compose. До выпуска
сертификата каталог `/etc/maison-test/nginx` должен быть пуст. Выпустите сертификат
через `sudo certbot certonly --webroot -w /var/www/maison-acme -d maison-rest.duckdns.org`.
Установите `deploy/nginx/https.conf` в `/etc/maison-test/nginx/`, затем выполните
`nginx -t` и `nginx -s reload` в контейнере `nginx`. После внешней проверки HTTPS
установите туда же `deploy/nginx/redirect.conf` и повторите проверку и перезагрузку.
На порту 80 маршрут `/.well-known/acme-challenge/` остаётся доступен для продления.

Установите `deploy/reload-nginx.sh` с правами `0755` в
`/etc/letsencrypt/renewal-hooks/deploy/maison-test-nginx`. Для тестового проекта
Compose используется имя `maison-test`. Включите `sudo systemctl enable --now certbot.timer`
и проверьте продление командой
`sudo certbot renew --cert-name maison-rest.duckdns.org --dry-run --run-deploy-hooks`.

После остановки и нового запуска EC2 автоматически назначенный IPv4 может измениться.
Если нужен автоматический DuckDNS, используйте однократный сервис systemd с таймером
при загрузке и каждые пять минут. Храните токен в отдельном файле `root:root` с правами
`0600` и передавайте сервису через `LoadCredential`. Скрипт может получать текущий
публичный IPv4 через IMDSv2 и отправлять его по HTTPS в [DuckDNS API][duckdns-api].
В журнал записывайте только результат `OK` или ошибку. Токен и URL запроса не должны
попадать в журнал, аргументы процесса или Git.

[duckdns-api]: https://www.duckdns.org/spec.jsp

## Проверки и команды Django

```bash
docker compose --env-file backend/.env exec backend python manage.py check
docker compose --env-file backend/.env exec backend python manage.py test
docker compose --env-file backend/.env exec backend python manage.py migrate
docker compose --env-file backend/.env exec backend python manage.py collectstatic --noinput
docker compose --env-file backend/.env exec backend python manage.py createsuperuser
docker compose --env-file backend/.env exec backend python manage.py shell -c 'from django.db import connection; connection.ensure_connection(); print(connection.vendor)'
docker compose --env-file backend/.env exec nginx nginx -t
curl -f http://127.0.0.1/health/
curl -f -H 'Accept: application/json' http://127.0.0.1/api/v1/health/
```

Оба проверочных URL возвращают `{"status": "ok", "project": "MAISON Restaurant"}`.
Они проверяют HTTP-маршрутизацию, а не состояние базы; подключение проверяет
отдельная команда `connection.ensure_connection()` выше.

Админка доступна на `/admin/`, вход для интерфейса DRF — на `/api-auth/login/`.
Для будущих API по умолчанию включены `SessionAuthentication`, `BasicAuthentication`
и доступ только аутентифицированным пользователям (`IsAuthenticated`). Проверочный
маршрут `/api/v1/health/` открыт всем и поддерживает GET и OPTIONS.
Базовый адрес REST API при запуске через Compose — `http://127.0.0.1/api/v1/`.
Без Docker `runserver` по умолчанию использует порт `8000`.
Маршруты `catalog`, `cart` и `staff` подключены в `backend/config/urls.py`.
Каталог пока содержит только модель `Dish`: API категорий и блюд ещё не реализован.
Гостевая корзина доступна без авторизации по адресу
`/api/v1/cart/` (`GET` — итоги, `POST` — создание или получение корзины).

Swagger UI доступен по `/api/swagger/`, схема OpenAPI — по `/api/schema/`.
Схема описывает API сотрудников и методы корзины, включая заголовок `X-Cart-Token`.
Файлы интерфейса собирает `collectstatic` и раздаёт Nginx, поэтому для Swagger
не нужен внешний CDN.

## Сотрудники

Уполномоченный администратор создаёт пользователя в Django Admin и назначает ему
один профиль `EmployeeProfile`. Роли — `owner` (владелец), `admin` (администратор)
и `waiter` (официант). Доступ к API сотрудников требует активной учётной записи
Django с профилем. Доступ к самой админке регулируют отдельные разрешения Django.

| Метод и URL | Что передать | Успешный ответ |
| --- | --- | --- |
| `POST /api/v1/staff/login/` | JSON с полями `username` и `password` | `access` и `refresh` |
| `POST /api/v1/staff/token/refresh/` | JSON с полем `refresh` | Новый `access` |
| `GET /api/v1/staff/me/` | Заголовок `Authorization: Bearer <access>` | `id` профиля, `first_name`, `last_name`, `username` и `role` |

Срок действия access-токена — 5 минут, refresh-токена — 24 часа. Чтобы проверить
профиль в Swagger UI, получите токены через `login`, нажмите **Authorize** и вставьте
значение `access` в поле `jwtAuth`.

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

`dish_id` должен быть положительным целым числом.
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
При удалении блюда его позиции удаляются из всех корзин. Повторное добавление
удалённого блюда возвращает `400`, изменение или удаление исчезнувшей позиции — `404`.

## Проверка CORS

В `backend/.env` задайте разрешённые адреса frontend, например:

```dotenv
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Схема, хост и порт должны совпадать с Origin браузера. После изменения окружения
перезапустите Backend с новыми значениями. CORS действует для `/api/`; стандартные
заголовки, `Content-Type` и `X-Cart-Token` разрешены, а `X-Cart-Token` открыт для чтения
через `response.headers.get("X-Cart-Token")`. Поддерживаются `GET`, `POST`, `PATCH`,
`DELETE` и предварительные `OPTIONS`; доступность операции определяет маршрут.

При запущенном Backend проверьте предварительный запрос (для `DELETE` замените
значение `PATCH`):

```bash
curl -i -X OPTIONS http://127.0.0.1/api/v1/cart/items/1/ \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: PATCH' \
  -H 'Access-Control-Request-Headers: content-type,x-cart-token'
```

Ожидаются `200`, `Access-Control-Allow-Origin: http://localhost:5173`, `PATCH` в
`Access-Control-Allow-Methods`, `content-type` и `x-cart-token` в
`Access-Control-Allow-Headers`. `OPTIONS` не создаёт и не изменяет корзины.
Повторите с `Origin: https://unknown.example`: разрешающего заголовка
`Access-Control-Allow-Origin` быть не должно.

Для проверки реального ответа создайте корзину:

```bash
curl -i -X POST http://127.0.0.1/api/v1/cart/ \
  -H 'Origin: http://localhost:5173'
curl -i http://127.0.0.1/api/v1/cart/ \
  -H 'Origin: http://localhost:5173' \
  -H 'X-Cart-Token: <токен из предыдущего ответа>'
```

Ожидаются соответственно `201` и `200`, `X-Cart-Token` и
`Access-Control-Expose-Headers: X-Cart-Token`. CORS управляет доступом браузера
к ответам; доступ к конкретной корзине по-прежнему определяется её токеном.

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
Для раздачи статики через локальный `runserver` задайте `DEBUG=True` в своём окружении.

## Структура

- `backend/config/` — настройки, маршрутизация, ASGI/WSGI, проверочные представления.
- `backend/apps/` — `cart` с моделями, сервисами и API гостевой корзины,
  минимальная модель `catalog.Dish` и заготовки остальных приложений.
- `backend/tests/` — проверки базовых маршрутов.
- `backend/Dockerfile`, `docker-compose.yml`, `nginx/` — запуск Django, PostgreSQL и Nginx по HTTP.
- `docs/architecture.md` — архитектура и распределение задач.

JWT, API каталога и frontend пока не настроены.
