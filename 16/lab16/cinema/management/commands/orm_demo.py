"""Команда вывода обязательных ORM-запросов и демонстрации проблемы N+1."""

from django.core.management.base import BaseCommand

from cinema.orm_demo import run_orm_demo


class Command(BaseCommand):
    """Печатает результаты ORM-запросов в консоль."""

    help = "Демонстрирует all/filter/exclude/get/order_by/count/exists/aggregate/annotate."

    def handle(self, *args, **options) -> None:
        for line in run_orm_demo():
            self.stdout.write(line)
