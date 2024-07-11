from .programs import *
from .schedules import *
from .clients import *
from .auth import *
from .reports import *
from src.database import as_dict


def program_to_model(self) -> Program:
    nested_models = {
        "category": Category.from_orm(self.category_obj),
        "placement": Category.construct(name=self.placement),
        "instructor": InstructorPublic.from_orm(self.instructor_obj),
    }
    model = as_dict(self)
    model.update(nested_models)
    return Program(**model)


def record_to_model(self) -> SchemaRecord:
    nested_models = {
        "program": self.program_obj.to_model()
    }
    model = as_dict(self)
    model.update(nested_models)
    return SchemaRecord(**model)
