## 4 Установка и запуск комплекса

Перед запуском контейнеров необходимо установить и настроить систему контейнеризации Docker. Для этого нужно выполнить следующие шаги:

Установить пакеты docker и docker-compose из репозиториев ОС:

sudo dnf install docker docker-compose

Убедиться, что установка завершена без ошибок.

Включить автоматический запуск службы Docker при загрузке ОС:

sudo systemctl enable --now docker.service

Проверить работоспособность среды запуска контейнеров командой:

sudo docker run hello-world

Ожидаемый результат – информационное сообщение об успешной работе Docker.

### 4.1 Развёртывание программного окружения

Для обработки входящих HTTP(S)-запросов, терминации TLS-соединений и маршрутизации трафика между контейнерами используется сервис Traefik.

#### 4.1.1 Установка среды контейнеризации Docker

Для установки сервиса Traefik необходимо подготовить файл docker-compose.yaml со следующим содержанием:

version: '3'

services:

reverse-proxy:

image: traefik:v3.3.2

restart: always

command:

- --api.insecure=true

- --providers.docker

- --entrypoints.websecure.address=:443

- --entrypoints.web.address=:80

- --entryPoints.web.http.redirections.entryPoint.to=websecure

- --entryPoints.web.http.redirections.entryPoint.scheme=https

- --certificatesresolvers.le.acme.email=<LE info email>

- --certificatesresolvers.le.acme.storage=/acme.json

- --certificatesresolvers.le.acme.tlschallenge=true

- --api

- --providers.file.filename=/opt/traefik/traefik.yml

- --providers.docker.exposedByDefault=false

- --providers.docker.network=traefik_default

ports:

- "80:80"

- "443:443"

volumes:

- /var/run/docker.sock:/var/run/docker.sock

- /var/acme.json:/acme.json

- /opt/devstg.rosa.ru/traefik:/opt/traefik

labels:

- "traefik.enable=true"

- "traefik.http.routers.traefik.rule=Host(`<TRAEFIK\ DASHBOARD URL>`)"

- "traefik.http.routers.traefik.service=api@internal"

- "traefik.http.routers.traefik.middlewares=admin"

- "traefik.http.routers.traefik.tls.certresolver=le"

- "traefik.http.routers.traefik.entrypoints=websecure"

- "traefik.http.middlewares.admin.basicauth.users=<ADMIN USER>:<HASHED PASS>"

- "traefik.http.middlewares.compress.compress=true"

где необходимо заменить следующие переменные:

<LE info email> — адрес электронной почты для получения уведомлений от файла хранения данных Let's Encrypt;

<TRAEFIK DASHBOARD URL> — адрес веб-интерфейса Traefik;

<ADMIN USER> — логин администратора;

<HASHED PASS> — хеш пароля (формирование описано в официальной документации: https://doc.traefik.io/traefik/middlewares/http/basicauth/).

#### 4.1.2 Развёртывание маршрутизатора входящих запросов Traefik

Далее необходимо подготовить файлы на сервере для работы сервиса Traefik:

Создать служебный файл для хранения данных Let's Encrypt:

sudo touch /var/acme.json

sudo chmod 600 /var/acme.json

Создать структуру директорий /opt/devstg.rosa.ru/traefik/ssl/ и разместить в ней TLS-сертификат и закрытый ключ. Структура новой директории представлена ниже (рисунок 1 ).

Рисунок 1 – Пример структуры директории /opt/devstg.rosa.ru/traefik/ssl/

Создать конфигурационный файл /opt/devstg.rosa.ru/traefik/traefik.yml:

tls:

certificates:

- certFile: /opt/traefik/ssl/cert.pem

keyFile: /opt/traefik/ssl/key.pem

stores:

- default

Подробности о работе с TLS-сертификатами приведены в официальной документации разработчиков сервиса: https://doc.traefik.io/traefik/https/tls/

##### 4.1.2.1 Подготовка конфигурационных файлов

Затем необходимо запустить сервис Traefik из директории с файлом docker-compose.yaml:

sudo docker compose up -d --force-recreate

Следует убедиться, что запуск завершён без ошибок. Проверить статус контейнера можно командой:

sudo docker ps

После запуска сервиса Traefik нужно зайти в его дашборд по адресу <TRAEFIK DASHBOARD URL> и убедиться в доступности веб-интерфейса маршрутизатора.

##### 4.1.2.2 Создание вспомогательных файлов

Для установки СУБД PostgreSQL и ее первоначальной настройки для работы с Комплексом требуется выполнить следующие шаги:

Установить PostgreSQL с помощью команды:

sudo apt install postgresql

Получить последнюю версию СУБД с помощью следующих команд:

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ `lsb_release -cs`-pgdg\ main" >> /etc/apt/sources.list.d/pgdg.list'

wget -q https://www.postgresql.org/media/keys/ACCC4CF8.asc\ -O - | sudo apt-key add -

sudo apt-get install postgresql

Создать базу данных для Комплекса:

createdb wbii_stat

Подключиться к СУБД:

sudo su

psql

Создать отдельного пользователя и его пароль:

CREATE USER wbii WITH PASSWORD 'указать_сложный_пароль';

GRANT ALL PRIVILEGES ON DATABASE wbii_stat TO wbii;

где в первой строке необходимо задать пароль для пользователя.

Пароль должен состоять минимум из 12 символов, включать строчные и прописные латинские буквы, цифры, знаки препинания и специальные символы. Пробелы использовать запрещено.

##### 4.1.2.3 Запуск сервиса

Для обеспечения долговременного хранения данных необходимо создать тома Docker (Docker volume), в которых будут размещаться:

журналы работы (logs);

файлы приложения (app);

темы оформления интерфейса (themes);

исходный код и конфигурации (code).

Том Docker volume представляет собой область на диске хост-системы, которая может быть подключена к одному или нескольким контейнерам. Данные, размещённые в Docker volume, не теряются при пересоздании контейнера, что делает его основным инструментом для хранения постоянной информации.

Создание томов осуществляется следующими командами:

sudo docker volume create storage_logs

sudo docker volume create storage_app

sudo docker volume create themes

sudo docker volume create code

Далее следует убедиться в успешном создании томов Docker с помощью команды:

docker volume ls

Данная команда выведет список всех созданных Docker-томов. В результате в списке должны появиться тома с именами:

storage_logs;

storage_app;

themes;

code.

#### 4.1.3 Установка и подготовка PostgreSQL

Запуск Комплекса осуществляется с использованием системы CI/CD, настроенной в инфраструктуре GitLab, размещённой по адресу: https://git.rosa.ru/

Установка Портала разработчика выполняется следующими командами:

git checkout <название_ветки>

git pull

php artisan winter:up

где необходимо заменить параметр <название_ветки>:

ветки с именами rc_ХХ автоматически ассоциируются с тестовым контуром;

ветка release предназначена для развертывания в промышленной среде.

#### 4.1.4 Подготовка постоянного хранилища

### 4.2 Установка Комплекса

В штатном режиме работа Комплекса начинается автоматически при загрузке операционной системы. В случае необходимости запуска вручную требуется выполнить команды:

systemctl start postgresql

systemctl start apache2

Для запуска отдельных компонентов Комплекса вручную следует использовать следующие команды:

report/moralprep/index.php

report/statusrelative/index.php

report/whitespots/index.php

report/neuroschedule/index.php

### 4.3 Запуск Комплекса

Для начала работы с Комплексом администратору или пользователю необходимо:

открыть веб-браузер и перейти по адресу: https://developer.rosa.ru/;

перейти в раздел "Установить" для выбора подходящей ОС;

запустить процедуру установки программного окружения и компонентов Комплекса;

пройти процедуру аутентификации.

После прохождения процедуры аутентификации будет получен полный доступ к интерфейсу и функциям Комплекса.

#### 4.3.1 Загрузка через командную строку

Настоящий раздел содержит рекомендации по тонкой настройке ОС для обеспечения стабильной и безопасной работы Комплекса в производственной среде. Описанные меры включают оптимизацию параметров ядра, конфигурацию сетевой подсистемы, настройку изоляции и безопасности контейнеров, шифрование передаваемых данных, управление доступом через брандмауэр, а также организацию логирования.

Соблюдение приведённых ниже рекомендаций позволяет повысить отказоустойчивость Комплекса, минимизировать сетевые задержки, обеспечить надёжную защиту данных и упростить диагностику при эксплуатации.

#### 4.3.2 Вход в комплекс