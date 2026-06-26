from fastapi import APIRouter, HTTPException
from app.dependencies import UserServiceDep, DatabaseDep
from app.schemas.user import UserCreate, UserResponse, UserUpdate, LoginResponse, LoginRequest
from typing import List

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: DatabaseDep,
    user_service: UserServiceDep
):
    try:
        db_user = user_service.create_user(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: DatabaseDep,
    user_service: UserServiceDep
):
    try:
        user = user_service.get_user_by_id(db, user_id)
        return user
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: DatabaseDep,
    user_service: UserServiceDep
):
    try:
        db_user = user_service.update_user(db, user_id, user_update)
        return db_user
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: DatabaseDep,
    user_service: UserServiceDep
):
    try:
        user_service.delete_user(db, user_id)
        return {"message": "Usuário deletado com sucesso"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/", response_model=List[UserResponse])
def list_users(
    db: DatabaseDep,
    user_service: UserServiceDep,
    skip: int = 0,
    limit: int = 100
):
    users = user_service.list_users(db, skip, limit)
    return users

@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    db: DatabaseDep,
    user_service: UserServiceDep
):
    try:
        login_response = user_service.login_user(db, login_data.email, login_data.senha)
        return login_response
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))