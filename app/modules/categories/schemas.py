from pydantic import BaseModel, ConfigDict

from app.modules.categories.models import CategoryType


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    type: CategoryType
