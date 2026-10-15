"""API эндпоинты User Service"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from app.services.user_service.api.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    UserResponse, UserUpdateRequest,
    LocationRequest, LocationResponse,
    UserSettingsResponse, UserSettingsUpdateRequest,
    UserVerifyResponse, UserProfileForFeedResponse
)
from app.services.user_service.api.deps import (
    get_auth_service, get_user_service, get_current_user_id,
    verify_service_key, check_user_ownership
)
from app.services.user_service.core.auth_service import AuthService
from app.services.user_service.core.service import UserService

router = APIRouter(prefix="/api/v1")

# === ПУБЛИЧНЫЕ ЭНДПОИНТЫ ===
@router.post("/auth/register", response_model=TokenResponse, tags=["Auth"])
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    user_data, tokens = await auth_service.register(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        phone=request.phone
    )
    return tokens

@router.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    user_data, tokens = await auth_service.login(
        email=request.email,
        password=request.password
    )
    return tokens

@router.post("/auth/refresh", response_model=TokenResponse, tags=["Auth"])
async def refresh_token(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    try:
        tokens = await auth_service.refresh_tokens(request.refresh_token)
        return tokens
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["Auth"])
async def logout(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    await auth_service.logout(request.refresh_token)
    return None

# === ЗАЩИЩЁННЫЕ ЭНДПОИНТЫ ===
@router.get("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def get_user_profile(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    _: bool = Depends(check_user_ownership),
    user_service: UserService = Depends(get_user_service)
):
    profile = await user_service.get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return profile["user"]

@router.put("/users/{user_id}", response_model=UserResponse, tags=["Users"])
async def update_user_profile(
    user_id: int,
    request: UserUpdateRequest,
    current_user_id: int = Depends(get_current_user_id),
    _: bool = Depends(check_user_ownership),
    user_service: UserService = Depends(get_user_service)
):
    updated = await user_service.update_user_profile(
        user_id=user_id,
        full_name=request.full_name,
        phone=request.phone
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return updated

@router.put("/users/{user_id}/location", response_model=LocationResponse, tags=["Users"])
async def update_user_location(
    user_id: int,
    request: LocationRequest,
    current_user_id: int = Depends(get_current_user_id),
    _: bool = Depends(check_user_ownership),
    user_service: UserService = Depends(get_user_service)
):
    location = await user_service.update_user_location(
        user_id=user_id,
        latitude=request.latitude,
        longitude=request.longitude,
        accuracy=request.accuracy
    )
    return location

@router.get("/users/{user_id}/settings", response_model=UserSettingsResponse, tags=["Users"])
async def get_user_settings(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    _: bool = Depends(check_user_ownership),
    user_service: UserService = Depends(get_user_service)
):
    settings = await user_service.get_user_settings(user_id)
    if not settings:
        settings = await user_service.update_user_settings(user_id)
    return settings

# ЕДИНСТВЕННЫЙ эндпоинт обновления настроек (с main_organization_id)
@router.put("/users/{user_id}/settings", response_model=UserSettingsResponse, tags=["Users"])
async def update_user_settings(
    user_id: int,
    request: UserSettingsUpdateRequest,
    current_user_id: int = Depends(get_current_user_id),
    _: bool = Depends(check_user_ownership),
    user_service: UserService = Depends(get_user_service)
):
    updated = await user_service.update_user_settings(
        user_id=user_id,
        search_radius_km=request.search_radius_km,
        show_only_subscriptions=request.show_only_subscriptions,
        notifications_enabled=request.notifications_enabled,
        language=request.language,
        theme=request.theme,
        main_organization_id=request.main_organization_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return updated

# === SERVICE-TO-SERVICE ЭНДПОИНТЫ ===
@router.get("/users/verify/{user_id}", response_model=UserVerifyResponse, tags=["Internal"])
async def verify_user_exists(
    user_id: int,
    _: bool = Depends(verify_service_key),
    user_service: UserService = Depends(get_user_service)
):
    exists = await user_service.verify_user_exists(user_id)
    return UserVerifyResponse(user_id=user_id, exists=exists, is_active=exists)

@router.get("/users/{user_id}/profile", response_model=UserProfileForFeedResponse, tags=["Internal"])
async def get_user_profile_for_feed(
    user_id: int,
    _: bool = Depends(verify_service_key),
    user_service: UserService = Depends(get_user_service)
):
    profile = await user_service.get_user_for_feed(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Пользователь не найден или неактивен")
    return profile

@router.get("/users/{user_id}/location", response_model=LocationResponse, tags=["Internal"])
async def get_user_location_for_feed(
    user_id: int,
    _: bool = Depends(verify_service_key),
    user_service: UserService = Depends(get_user_service)
):
    location = await user_service.get_user_location(user_id)
    if not location:
        return LocationResponse(id=0, user_id=user_id, latitude=None, longitude=None, accuracy=None, updated_at=None)
    return location

# Эндпоинт становления организатором (добавлен)
@router.post("/users/{user_id}/become-organizer", response_model=UserResponse, tags=["Users"])
async def become_organizer(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    _: bool = Depends(check_user_ownership),
    user_service: UserService = Depends(get_user_service)
):
    try:
        updated_user = await user_service.become_organizer(user_id, current_user_id)
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))