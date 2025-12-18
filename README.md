# 🤖 AutoTrading Bot (Microservices Architecture)

Автоматическая торговая система для криптовалютных бирж (ByBit + Binance).
Система построена на микросервисной архитектуре, устойчива к сбоям сети и использует ClickHouse для аналитики больших данных.

## 🏗 Архитектура

Система состоит из 4 логических блоков:

1.  **Eyes (Сбор данных):**
    * `bybit-stats-service`: Собирает тики и свечи с ByBit. Умеет восстанавливать историю (Backfill) после разрывов связи.
    * `binance-stats-service`: Собирает Orderbook (стакан) с Binance для анализа ликвидности.
2.  **Memory (Хранение):**
    * `ClickHouse`: Хранит рыночные данные (свечи, тики, стаканы). Использует Materialized Views.
    * `PostgreSQL`: Хранит историю сделок бота и состояние ордеров.
3.  **Brain (Анализ):**
    * `signal-service`: Анализирует данные из ClickHouse и генерирует сигналы.
4.  **Hands (Исполнение):**
    * `trade-control-service`: Получает сигналы через RabbitMQ, выставляет ордера на ByBit, ставит SL/TP и следит за позициями.

---

## 🚀 Быстрый старт

### Предварительные требования
* Docker & Docker Compose
* Python 3.10+ (для локальной разработки)

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
    ```bash
    docker-compose up -d --build
    ```

---
