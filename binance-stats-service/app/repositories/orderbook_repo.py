from app.core.config import settings


class OrderbookRepository:
    """
    Репозиторий для работы с таблицей orderbooks в ClickHouse.
    """

    def __init__(self, client):
        self.client = client
        self.table = f"{settings.CLICKHOUSE_DB}.orderbooks"

    def insert_orderbooks(self, data: list):
        """
        Вставляет пачку слепков стакана.
        """
        try:
            self.client.insert(
                self.table,
                data,
                column_names=[
                    "timestamp",
                    "symbol",
                    "bids_price",
                    "bids_qty",
                    "asks_price",
                    "asks_qty",
                ],
            )
        except Exception as e:
            print(f"Ошибка репозитория (Insert Orderbooks): {e}")
            raise e
