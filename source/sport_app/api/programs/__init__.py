from fastapi import APIRouter

from source.tables import Category, Placement, Instructor, Program

programs_router = APIRouter(
    prefix='/programs'
)
programs_router.include_router(Category.router)
programs_router.include_router(Placement.router)
programs_router.include_router(Instructor.router)
programs_router.include_router(Program.router)
