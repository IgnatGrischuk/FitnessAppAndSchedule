from datetime import datetime, timedelta

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import (
    JWTError,
    jwt,
)
from passlib.hash import bcrypt
from pydantic import ValidationError
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from source.database import Session, get_session
from source.settings import settings
from source.sport_app import models
from source import tables


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='api/auth/sign-in/')


def get_current_staff(token: str = Depends(oauth2_scheme)) -> models.Staff:
    return AuthService.verify_token(token)


def validate_admin_access(staff_member: models.Staff = Depends(get_current_staff)) -> models.Staff:
    if staff_member.role != str(tables.Roles.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return staff_member


def validate_operator_access(staff_member: models.Staff = Depends(get_current_staff)) -> models.Staff:
    try:
        validate_admin_access(staff_member)
        return staff_member
    except HTTPException:
        pass
    if staff_member.role != str(tables.Roles.operator):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return staff_member


class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.verify(plain_password, hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hash(password)

    @staticmethod
    def verify_token(token: str) -> models.Staff:
        exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate credentials',
            headers={'WWW-Authenticate': 'Bearer'},
        )
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except JWTError:
            raise exception from None

        user_data = payload.get('user')

        try:
            user = models.Staff.parse_obj(user_data)
        except ValidationError:
            raise exception from None

        return user

    @staticmethod
    def create_token(user: tables.Staff) -> models.Token:
        user_data = models.Staff.from_orm(user)
        user_data.role = str(user_data.role)
        now = datetime.utcnow()
        payload = {
            'iat': now,
            'nbf': now,
            'exp': now + timedelta(seconds=settings.jwt_expires_s),
            'sub': str(user_data.id),
            'user': user_data.dict(),
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        return models.Token(access_token=token)

    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    def register_new_staff(
        self,
        user_data: models.StaffCreate,
    ) -> models.Staff:
        user = tables.Staff(
            email=user_data.email,
            username=user_data.username,
            password_hash=self.hash_password(user_data.password),
            role=tables.Roles.operator
        )
        self.session.add(user)
        self.session.commit()
        return user

    def authenticate_staff(
        self,
        username: str,
        password: str,
    ) -> models.Token:
        exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
            headers={'WWW-Authenticate': 'Bearer'},
        )

        user = (
            self.session
            .query(tables.Staff)
            .filter_by(username=username)
            .scalar()
        )

        if not user:
            raise exception
        if not self.verify_password(password, user.password_hash):
            raise exception

        return self.create_token(user)

    def get_all_staff(self) -> list[models.Staff]:
        staff = (
            self.session
            .query(tables.Staff)
            .all()
        )
        return staff

    def _get_staff(
        self,
        staff_id: int,
    ) -> tables.Staff:
        staff = (
            self.session
            .query(tables.Staff)
            .where(tables.Staff.id == staff_id)
            .scalar()
        )
        if not staff:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return staff

    def delete_staff(
        self,
        staff_id: int
    ):
        staff = self._get_staff(staff_id)
        try:
            self.session.execute(delete(tables.Staff).where(tables.Staff.id == staff_id))
            self.session.commit()
        except IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT)
