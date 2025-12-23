# 🤖 AutoTrading Bot

**AutoTradingBot** — это асинхронная микросервисная система для алгоритмической торговли на криптовалютных биржах (ByBit). Система построена на базе Python 3.12, использует Docker для контейнеризации, RabbitMQ для обмена сообщениями и ClickHouse для аналитики больших данных.

## 🏗 Архитектура

Проект состоит из независимых микросервисов, объединенных в единую сеть:

1.  **Signal Service (Brain)** 🧠
    * Анализирует рыночные данные из ClickHouse.
    * Реализует стратегию (Тренд + Объемы + Свечной анализ).
    * Генерирует сигналы (`OPEN_LONG`, `CLOSE_LONG`) и отправляет их в RabbitMQ.
2.  **Trade Control Service (Hands)** 🦾
    * Слушает очередь сигналов из RabbitMQ.
    * Исполняет ордера на бирже **ByBit**.
    * Управляет рисками: Stop Loss, Take Profit, Trailing Stop.
    * Ведет учет сделок в PostgreSQL.
    * Отправляет ежедневные отчеты о балансе.
3.  **Stats Services (Eyes)** 👀
    * `bybit-stats-service`: Собирает тики и свечи с ByBit в реальном времени.
    * `binance-stats-service`: Собирает данные (стаканы) с Binance для арбитража/аналитики.
4.  **Notification Service (Voice)** 🔔
    * Слушает события в RabbitMQ и отправляет красивые HTML-уведомления в Telegram.
5.  **Storage (Memory)** 💾
    * **ClickHouse:** Хранит "сырые" данные (свечи, тики) для быстрого анализа.
    * **PostgreSQL:** Хранит состояние активных ордеров и историю торговли.

---

## 🛠 Технический стек

* **Язык:** Python 3.12
* **Фреймворки:** FastAPI, SQLAlchemy (Async), Aio_pika, Pydantic v2
* **Базы данных:** PostgreSQL, ClickHouse
* **Брокер сообщений:** RabbitMQ
* **Инфраструктура:** Docker, Docker Compose
* **Тестирование:** Pytest, Asyncio

---

## 🚀 Установка и запуск

### 1. Предварительные требования
* Установленный **Docker** и **Docker Compose**.
* API ключи от биржи ByBit (Testnet или Mainnet).
* Токен Telegram бота (от @BotFather).

### Установка

1.  **Клонировать репозиторий:**
    ```bash
    git clone [https://github.com/your-repo/AutoTradingBot.git](https://github.com/your-repo/AutoTradingBot.git)
    cd AutoTradingBot
    ```

2.  **Настроить окружение:**

    Создайте файл `.env` на основе примера:
    ```bash
    cp .env.example .env
    ```
    *Обязательно укажите свои API ключи ByBit!*

3.  **Запуск:** 

    Сборка и запуск всех контейнеров в фоновом режиме:
    ```bash
    docker-compose up -d --build
    ```

    Посмотреть логи конкретного сервиса (например, трейдера):

    ```bash
    docker logs -f trade_control
    ```
    (Для выхода из логов нажмите Ctrl+C)

    Остановить работу:

    ```bash
    docker compose down
    ```

---

## 🧪 Тестирование

Проект покрыт unit-тестами. Тесты запускаются внутри контейнеров, используя временную базу данных sqlite в оперативной памяти (чтобы не засорять реальную БД).

1. **Запуск тестов стратегии (Signal Service):**

    ```bash
    docker exec -it signal_service pytest /app/tests -v
    ```

2. **Запуск тестов торговли (Trade Control):**

    ```bash
    docker exec -it trade_control pytest /app/tests -v
    ```

---

## 🔔 Уведомления

Бот отправляет следующие типы уведомлений в Telegram:

* 🤖 **SYSTEM ONLINE/OFFLINE:** Статус включения и выключения бота.

* 🚀 **OPEN LONG:** Открытие новой позиции по сигналу.

* 🔔 **POSITION CLOSED:** Закрытие сделки (по TP или SL).

* ☕ **MORNING REPORT:** Ежедневный отчет (баланс, количество сделок) в 09:00.

* ⚠️ **CRITICAL ERROR:** Оповещение о сбоях API или ошибках исполнения ордеров.

---

## 📂 Структура проекта

```Plaintext
AutoTradingBot/
├── docker-compose.yml       # Оркестрация контейнеров
├── .env                     # Конфигурация
├── signal-service/          # Сервис генерации сигналов
│   ├── app/
│   │   ├── services/strategy.py  # Логика стратегии
│   │   └── ...
│   └── tests/               # Тесты стратегии
├── trade-control-service/   # Сервис исполнения сделок
│   ├── app/
│   │   ├── services/trader.py    # Логика торговли и трейлинга
│   │   └── ...
│   └── tests/               # Тесты трейдера и БД
├── notification-service/    # Сервис отправки уведомлений
├── bybit-stats-service/     # Сбор данных с ByBit
└── binance-stats-service/   # Сбор данных с Binance
```

---