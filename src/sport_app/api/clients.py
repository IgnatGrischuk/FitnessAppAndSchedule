import datetime
from typing import Union

from fastapi import (
    APIRouter,
    Depends,
    status,
)

from ..models import Client, CreateClient, ClientUpdate, ClientMinimum, Staff
from ..services import ClientService
from ..services.auth import validate_admin_access, validate_operator_access


router = APIRouter(
    prefix='/client',
    tags=['clients']
)


@router.get(
    '/',
    response_model=Union[list[Client], list[ClientMinimum]]
)
def get_clients(
    staff_member: Staff = Depends(validate_operator_access),
    client_service: ClientService = Depends(),
):
    return client_service.get_many(staff_member)


@router.get(
    '/{client_id}',
    response_model=Client,
    dependencies=[Depends(validate_operator_access)],
)
def get_client(
    client_id: int,
    client_service: ClientService = Depends(),
):
    return client_service.get_client(client_id)


@router.delete(
    '/{client_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_admin_access)],
)
def delete_client(
    client_id: int,
    client_service: ClientService = Depends(),
):
    client_service.delete_client(client_id)


@router.post(
    '/',
    response_model=Client,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(validate_admin_access)],
)
def create_client(
    client_data: CreateClient,
    client_service: ClientService = Depends(),
):
    return client_service.create_client(client_data)


@router.put(
    '/{client_id}',
    response_model=Client,
    dependencies=[Depends(validate_admin_access)],
)
def update_client(
    client_id: int,
    client_data: ClientUpdate,
    client_service: ClientService = Depends(),
):
    return client_service.update_client(client_id, client_data)


@router.post(
    '/{client_id}/book',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_operator_access)],
)
def book_client(
    client_id: int,
    program: int,
    date: datetime.datetime,
    client_service: ClientService = Depends(),
):
    client_service.book_client(client_id, program, date)


@router.delete(
    '/{client_id}/book',
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_operator_access)],
)
def remove_client_booking(
    client_id: int,
    program: int,
    date: datetime.datetime,
    client_service: ClientService = Depends(),
):
    client_service.remove_client_booking(client_id, program, date)
