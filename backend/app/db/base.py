"""Единый declarative Base для всех микросервисов.

Все модели импортируют Base отсюда, чтобы Alembic видел
все таблицы в одном MetaData и мог генерировать миграции.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
