import copy
from typing import Any
from models import Session, SessionStatus


class SessionTransactionContext:
    """
    Контекстный менеджер для транзакционного изменения данных сеанса.
    При возникновении ошибки внутри блока `with` изменения откатываются.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self._backup_tickets: int = 0
        self._backup_status: SessionStatus = SessionStatus.SCHEDULED

    def __enter__(self) -> Session:
        print(f"\n[TRANSACTION START] Начало транзакции для сеанса #{self.session.id}")
        # Сохраняем состояние объекта
        self._backup_tickets = self.session.sold_tickets
        self._backup_status = self.session.status
        return self.session

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            print(f"[TRANSACTION ROLLBACK] Произошла ошибка: {exc_val}. Изменения отменены!")
            self.session.sold_tickets = self._backup_tickets
            self.session.status = self._backup_status
            # Возвращаем True, чтобы подавить исключение и корректно обработать
            return True
        print(f"[TRANSACTION COMMIT] Транзакция успешно завершена для сеанса #{self.session.id}")
        return False