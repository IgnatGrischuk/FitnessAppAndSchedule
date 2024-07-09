import datetime
from typing import NamedTuple, Optional, Union
from collections.abc import Iterable

from fastapi import (
    Depends,
    HTTPException,
    status
)
from dateutil import relativedelta as rd
from sqlalchemy.orm import Session
from sqlalchemy import delete, tuple_, select

from source.database import get_session

from source.sport_app import models
from source import tables
from source import utils


class SchemaService:
    def __init__(
        self,
        session: Session = Depends(get_session)
    ):
        self.session = session

    def _get_schema(
        self,
        schema_id: int,
    ) -> tables.ScheduleSchema:
        schema = (
            self.session
            .query(tables.ScheduleSchema)
            .filter(tables.ScheduleSchema.id == schema_id)
            .scalar()
        )
        if not schema:
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return schema

    @property
    def active_schema(self) -> Optional[tables.ScheduleSchema]:
        schema = (
            self.session
            .query(tables.ScheduleSchema)
            .filter(tables.ScheduleSchema.active)
            .scalar()
        )
        return schema

    @property
    def next_week_schema(self) -> Optional[tables.ScheduleSchema]:
        schema = (
            self.session
            .query(tables.ScheduleSchema)
            .where(tables.ScheduleSchema.to_be_active_from.isnot(None))
            .scalar()
        )
        return schema

    def get_many_schemas(self) -> list[tables.ScheduleSchema]:
        schemas = (
            self.session
            .query(tables.ScheduleSchema)
            .all()
        )
        return schemas

    def create_schema(
        self,
        schema_data: models.SchemaCreate,
    ) -> tables.ScheduleSchema:
        base_schema = self._get_schema(schema_data.base_schema) if schema_data.base_schema else None
        schema = tables.ScheduleSchema(
            name=schema_data.name
        )
        active_schema = self.active_schema
        if not active_schema:
            schema.active = True
        self.session.add(schema)
        if base_schema:
            schema.records = base_schema.records
        self.session.commit()
        return schema

    def delete_schema(
        self,
        schema_id: int
    ):
        schema = self._get_schema(schema_id)
        if schema.active or schema.to_be_active_from:
            raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                                detail="Запрещается удаление активной схемы")
        self.session.execute(delete(tables.ScheduleSchema).filter_by(id=schema_id))
        self.session.commit()

    def _compare_schemas(
        self,
        schema: tables.ScheduleSchema,
        other_schema: tables.ScheduleSchema,
        next_week=False,
    ):
        """
        Генерирует список занятий, которые отсутствуют в schema, но присутствуют в target_schema,
        передает список на снятие бронирования
        """
        records = set(other_schema.records) - set(schema.records)
        self._remove_booking(records, next_week=next_week)

    def _remove_booking(
        self,
        records: Union[Iterable[tables.SchemaRecord], Iterable[int]],
        next_week=False
    ):
        """
        Снимает бронирование (запись) клиентов с предстоящих занятий (но отмененных), соответствующим переданным records
        :param next_week: снимет на следующей неделе
        """
        if isinstance(next(iter(records), None), int):
            records = (
                self.session
                .query(tables.SchemaRecord)
                .where(tables.SchemaRecord.id.in_(records))
                .all()
            )
        interval = rd.relativedelta(days=7) if next_week else rd.relativedelta()
        obj_to_remove = [(r.program, r.date + interval)
                         for r in records
                         if r.date+interval > utils.now()]
        self._remove_booked_rows(obj_to_remove)

    def _remove_booked_rows(self, rows: list[tuple[int, datetime.datetime]]):
        """
        Removes rows from BookedClasses
        :param rows: int - id тренировочной программы, datetime.datetime - дата занятия
        """
        B = tables.BookedClasses
        self.session.execute(
            delete(B)
            .where(tuple_(B.program, B.date).in_(rows))
        )
        self.session.flush()

    def update_schema(
        self,
        schema_id: int,
        data: models.SchemaUpdate,
    ) -> tables.ScheduleSchema:
        target_schema = self._get_schema(schema_id)
        active_schema = self.active_schema
        next_week_schema = self.next_week_schema

        # активация схемы
        if data.active:
            self._compare_schemas(target_schema, active_schema)
            if not next_week_schema:
                self._compare_schemas(target_schema, active_schema, next_week=True)
            # если активируется схема, которая запланирована на следующую неделю
            elif target_schema.id == next_week_schema.id:
                target_schema.to_be_active_from = None
            active_schema.active = False
            target_schema.active = True

        # деактивация схемы
        if data.active is False:
            if target_schema.id == active_schema.id:
                raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                                    detail="Не допускается деактивация схемы")
        if data.activate_next_week is False and target_schema.id == next_week_schema.id:
            self._compare_schemas(active_schema, target_schema, next_week=True)
            target_schema.to_be_active_from = None

        # установка схемы на следующую неделю
        if data.activate_next_week:
            if target_schema.active:
                raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                                    detail="Схема уже активна")
            if next_week_schema:
                self._compare_schemas(target_schema, next_week_schema, next_week=True)
                next_week_schema.to_be_active_from = None
            target_schema.to_be_active_from = utils.next_mo()

        for field, value in data:
            if value:
                setattr(target_schema, field, value)
        self.session.commit()
        return target_schema

    def get_schema_records(
        self,
        schema_id: int
    ) -> list[models.SchemaRecord]:
        schedule_schema = self._get_schema(schema_id)
        return [record.to_model() for record in schedule_schema.records]

    def include_records_in_schema(
        self,
        schema_id: int,
        records_to_include: Iterable[int],
    ) -> list[int]:
        schema = self._get_schema(schema_id)
        records = set((r.id for r in schema.records))
        records.update(records_to_include)
        new_records = (
            self.session
            .query(tables.SchemaRecord)
            .filter(tables.SchemaRecord.id.in_(records))
            .all()
        )
        schema.records = new_records
        self.session.commit()
        return [r.id for r in new_records]

    def exclude_records_from_schema_(
        self,
        schema_id: int,
        records_to_exclude: list[int],
        force_delete: bool = False,
    ):
        """
        Выполняет контроль над тем, чтобы клиенты не были записаны на занятия, которые были исключены
        из активных схем (отменены) и у которых дата проведения не наступила. Такое состояние возникает, когда клиенты
        успели записаться на занятие, которое впоследствии было исключено из расписания, что требует удаления
        соответствующих строк из базы данных, поскольку по ним формируется отчет о посещаемости той или иной трен. программы.
        """
        schema = self._get_schema(schema_id)

        if schema.active:
            self._remove_booking(records_to_exclude)
            if not self.next_week_schema:
                self._remove_booking(records_to_exclude, next_week=True)
        elif schema.to_be_active_from:
            self._remove_booking(records_to_exclude, next_week=True)

        table = tables.schedule_schema_record
        self.session.execute(
            delete(table)
            .where(table.columns.schema_record.in_(records_to_exclude))
            .where(table.columns.schedule_schema == schema_id)
        )

        if force_delete:
            for record in records_to_exclude:
                rows = self.session.query(table).where(table.c.schema_record == record).all()
                if not rows:
                    self.session.execute(delete(tables.SchemaRecord).where(tables.SchemaRecord.id == record))

        self.session.flush()

    def exclude_records_from_schema(
        self,
        schema_id: int,
        records_to_exclude: list[int],
        force_delete: bool,
    ):
        self.exclude_records_from_schema_(schema_id, records_to_exclude, force_delete)
        self.session.commit()
