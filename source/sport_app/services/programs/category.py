from typing import (
    Optional
)

from fastapi import (
    Depends,
    HTTPException,
    status
)
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from source.database import get_session

from source.sport_app import models
from source import tables


class CategoryService:
    exception = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail='Категория с таким наименованием уже существует'
    )

    def __init__(
        self,
        session: Session = Depends(get_session)
    ):
        self.session = session

    def get(
        self,
        name: str
    ) -> tables.Category:
        category = self._get(name)
        return category

    def get_many(
        self
    ) -> list[tables.Category]:
        categories = (
            self.session
            .query(tables.Category)
            .all()
        )
        return categories

    def create_category(
        self,
        data: models.Category
    ) -> tables.Category:
        category = tables.Category(
            **data.dict()
        )
        try:
            self.session.add(category)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise CategoryService.exception from None
        return category

    def update_category(
        self,
        name: str,
        data: models.Category
    ) -> tables.Category:

        category = self._get(name)
        for field, value in data:
            setattr(category, field, value)
        self.session.commit()
        return category

    def delete_category(
        self,
        name: str,
    ):
        category = self._get(name)
        try:
            self.session.execute(delete(tables.Category).where(tables.Category.name == name))
            self.session.commit()
        except IntegrityError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Категория используется в программах.")

    def _get(
        self,
        name: str
    ) -> Optional[tables.Category]:
        category = (
            self.session
            .query(tables.Category)
            .filter(tables.Category.name == name)
            .first()
        )
        if not category:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return category
