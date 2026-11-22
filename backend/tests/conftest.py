# pytest tests/test_event_s.py tests/test_user_s.py tests/test_feed_s.py tests/test_analytics_s.py tests/test_chat_s.py tests/test_org_s.py tests/test_subs_s.py tests/test_notif_s.py -v
import pytest


@pytest.fixture(scope="session", autouse=True)
def clear_all_settings_cache():
    try:
        from app.services.analytics_service.config import (
            get_settings as analytics_get_settings,
        )

        analytics_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    try:
        from app.services.feed_service.config import get_settings as feed_get_settings

        feed_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    try:
        from app.services.subscription_service.config import (
            get_settings as sub_get_settings,
        )

        sub_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    try:
        from app.services.organization_service.config import (
            get_settings as org_get_settings,
        )

        org_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass
    try:
        from app.services.user_service.config import get_settings as user_get_settings

        user_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass

    yield
    try:
        from app.services.analytics_service.config import (
            get_settings as analytics_get_settings,
        )

        analytics_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass

    try:
        from app.services.user_service.config import get_settings as user_get_settings

        user_get_settings.cache_clear()
    except (ImportError, AttributeError):
        pass


def collect_route_paths(app) -> list[str]:
    return list(app.openapi().get("paths", {}).keys())
