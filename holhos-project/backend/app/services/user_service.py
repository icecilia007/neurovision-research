from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, LoginResponse

class UserService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_user(self, db: Session, user_data: UserCreate) -> User:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("Email já registrado")

        hashed_password = self.pwd_context.hash(user_data.senha)

        db_user = User(
            full_name=user_data.nome_completo,
            gender=user_data.genero,
            birth_date=user_data.nascimento,
            education_level=user_data.escolaridade,
            email=user_data.email,
            phone=user_data.telefone,
            password_hash=hashed_password
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def get_user_by_id(self, db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Usuário não encontrado")
        return user

    def update_user(self, db: Session, user_id: int, user_update: UserUpdate) -> User:
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            raise ValueError("Usuário não encontrado")

        update_data = user_update.model_dump(exclude_unset=True)
        field_map = {
            'nome_completo': 'full_name',
            'genero': 'gender',
            'nascimento': 'birth_date',
            'escolaridade': 'education_level',
            'telefone': 'phone',
        }

        for field, value in update_data.items():
            setattr(db_user, field_map.get(field, field), value)

        db.commit()
        db.refresh(db_user)
        return db_user

    def delete_user(self, db: Session, user_id: int) -> bool:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Usuário não encontrado")

        db.delete(user)
        db.commit()
        return True

    def list_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def login_user(self, db: Session, email: str, senha: str) -> LoginResponse:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError("Email ou senha incorretos")

        if not self.pwd_context.verify(senha, user.password_hash):
            raise ValueError("Email ou senha incorretos")

        return LoginResponse(
            success=True,
            message="Login realizado com sucesso",
            user_id=user.id,
            nome_completo=user.full_name
        )

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()
