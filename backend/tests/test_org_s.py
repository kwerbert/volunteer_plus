import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем локальные компоненты сервиса
from app.services.organization_service.main import app
from app.services.organization_service.db.models import Base, Organization, Category  # ← явный импорт моделей!
from app.services.organization_service.db.session import get_db_session  # ← та же, что в роутере

# === ТЕСТОВАЯ БД ===
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_org.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
# ИСПРАВЛЕНО: переименовано, чтобы pytest не собирал это как тест
session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# === ФИКСТУРЫ ===
@pytest.fixture(scope="function")
async def test_db():
    """Создаёт тестовую БД перед каждым тестом"""
    async with test_engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    # Используем новое имя
    async with session_factory() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(test_db):
    """Тестовый HTTP клиент с переопределённой БД"""
    async def override_get_db():
        yield test_db
    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def test_category(test_db):
    """Фикстура: создаёт тестовую категорию для организаций"""
    category = Category(id=1, name="Test Category")
    test_db.add(category)
    await test_db.commit()
    await test_db.refresh(category)
    return category

# Тесты (без изменений, но теперь будут работать)
@pytest.mark.asyncio
async def test_create_organization(client, test_category):
    """Тест создания организации"""
    payload = {
        "name": "Test Org",
        "description": "A test organization",
        "category_id": 1
    }
    response = await client.post("/api/v1/organizations", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["name"] == "Test Org"
    assert data["is_verified"] == False
    assert data["rating"] == 0.0

@pytest.mark.asyncio
async def test_search_organizations(client, test_category):
    """Тест поиска организаций"""
    await client.post("/api/v1/organizations", json={
        "name": "Searchable Org",
        "description": "Test"
    })
    response = await client.get("/api/v1/organizations?verified=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(org["name"] == "Searchable Org" for org in data)

@pytest.mark.asyncio
async def test_verify_organization(client, test_category):
    """Тест верификации организации"""
    create_resp = await client.post("/api/v1/organizations", json={
        "name": "Verify Me",
        "description": "Test"
    })
    org_id = create_resp.json()["id"]
    response = await client.post(f"/api/v1/organizations/{org_id}/verify", json={"verified": True})
    assert response.status_code == 200
    data = response.json()
    assert data["is_verified"] == True
    assert data["rating"] > 0.0

@pytest.mark.asyncio
async def test_unique_name_constraint(client, test_category):
    """Тест уникальности названия"""
    await client.post("/api/v1/organizations", json={
        "name": "Unique Name",
        "description": "Test"
    })
    response = await client.post("/api/v1/organizations", json={
        "name": "Unique Name",
        "description": "Test 2"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

# pytest tests/test_org_s.py -v