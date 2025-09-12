from typing import Optional, Union, Dict, Any

from sqlalchemy.orm import Session

from forest_ensys.core import security
from forest_ensys.crud.base import CRUDBase
from forest_ensys.model import User
from forest_ensys.schemas import UserCreate, UserUpdate


# noinspection PyMethodMayBeStatic,PyArgumentList
class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        db_obj = User(
            username=obj_in.username,
            hashed_password=security.get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
    ) -> User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data["password"]:
            hashed_password = security.get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def authenticate(self, db: Session, *, username: str, password: str):
        user_obj = self.get_by_username(db, username=username)
        if not user_obj:
            return None
        if not security.verify_password(
            plain_password=password, hashed_password=user_obj.hashed_password
        ):
            return None
        return user_obj


user = CRUDUser(User)
