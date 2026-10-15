# В данном проекте зависимости (сессия БД) импортируются напрямую из db.session
# Этот файл оставлен для расширения (например, зависимости авторизации)
from app.services.subscription_service.db.session import get_db_session