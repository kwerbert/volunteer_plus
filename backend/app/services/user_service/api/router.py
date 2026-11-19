"""API эндпоинты User Service"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.services.user_service.api.deps import (
    get_auth_service,
    get_current_user_id,
    get_user_service,
    require_same_user,
    verify_service_key,
)
from app.services.user_service.api.schemas import (
    LocationRequest,
    LocationResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileForFeedResponse,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdateRequest,
    UserUpdateRequest,
    UserVerifyResponse,
)

router = APIRouter(prefix="/api/v1")


# === ПУБЛИЧНЫЕ ЭНДПОИНТЫ ===


@router.post(
    "/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterRequest,
    auth_service=Depends(get_auth_service),
):
    """Регистрация нового пользователя"""
    try:
        user_data, tokens = await auth_service.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            phone=request.phone,
        )
        return tokens
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service=Depends(get_auth_service),
):
    try:
        user_data, tokens = await auth_service.login(
            request.email,
            request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return tokens


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshRequest,
    auth_service=Depends(get_auth_service),
):
    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return tokens


@router.post("/auth/logout")
async def logout(
    request: RefreshRequest,
    auth_service=Depends(get_auth_service),
):
    """Выход из системы"""
    success = await auth_service.logout(request.refresh_token)
    return {"success": success}


# === ЗАЩИЩЁННЫЕ ЭНДПОИНТЫ ===


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    user_id: int = Depends(get_current_user_id),
    user_service=Depends(get_user_service),
):
    profile = await user_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return profile["user"]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, user_service=Depends(get_user_service)):
    profile = await user_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return profile["user"]


@router.get("/users/{user_id}/profile")
async def get_user_full_profile(
    user_id: int,
    user_service=Depends(get_user_service),
):
    """Полный профиль: user + settings + location (вложенно).
    Без response_model: структура вложенная, отдельной схемы под неё нет."""
    profile = await user_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return profile


@router.patch("/users/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    user_service=Depends(get_user_service),
):
    """Обновление профиля текущего пользователя"""
    updated = await user_service.update_user_profile(
        user_id=user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return updated


@router.patch("/users/{user_id}/location", response_model=LocationResponse)
async def update_location(
    user_id: int,
    request: LocationRequest,
    _: int = Depends(require_same_user),
    user_service=Depends(get_user_service),
):
    """Обновление геолокации пользователя"""
    location = await user_service.update_user_location(
        user_id=user_id,
        latitude=request.latitude,
        longitude=request.longitude,
        accuracy=request.accuracy,
    )
    if not location:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return location


@router.get("/users/{user_id}/settings", response_model=UserSettingsResponse)
async def get_settings(
    user_id: int,
    user_service=Depends(get_user_service),
):
    """Получение настроек пользователя"""
    settings = await user_service.get_user_settings(user_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Настройки не найдены")
    return settings


@router.patch("/users/{user_id}/settings", response_model=UserSettingsResponse)
async def update_settings(
    user_id: int,
    request: UserSettingsUpdateRequest,
    _: int = Depends(require_same_user),
    user_service=Depends(get_user_service),
):
    """Обновление настроек пользователя"""
    settings = await user_service.update_user_settings(
        user_id=user_id,
        update_data=request.model_dump(exclude_unset=True),
    )
    if not settings:
        raise HTTPException(status_code=404, detail="Настройки не найдены")
    return settings


# === SERVICE-TO-SERVICE ЭНДПОИНТЫ ===


@router.get("/users/verify/{user_id}", response_model=UserVerifyResponse)
async def verify_user(
    user_id: int,
    _: None = Depends(verify_service_key),
    user_service=Depends(get_user_service),
):
    """Проверка существования пользователя (внутренний API)"""
    exists = await user_service.verify_user_exists(user_id)
    return UserVerifyResponse(exists=exists, is_active=exists)


@router.get("/users/{user_id}/feed-profile", response_model=UserProfileForFeedResponse)
async def get_user_for_feed(
    user_id: int,
    _: None = Depends(verify_service_key),
    user_service=Depends(get_user_service),
):
    """Получение данных пользователя для Feed Service"""
    profile = await user_service.get_user_for_feed(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return profile


@router.get("/users/{user_id}/location", response_model=LocationResponse)
async def get_user_location(
    user_id: int,
    _: None = Depends(verify_service_key),
    user_service=Depends(get_user_service),
):
    """Получение геолокации пользователя (внутренний API)"""
    location = await user_service.get_user_location(user_id)
    if not location:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return location
