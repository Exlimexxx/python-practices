from typing import Protocol


class Command(Protocol):

    def execute(self) -> bool:
        ...

    def undo(self) -> None:
        ...