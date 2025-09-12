import re
from typing import Any

from sqlalchemy.orm import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    Base class for all database models
    """

    id: Any
    __name__: str
    __allow_unmapped__ = True

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(self) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", self.__name__).lower()
