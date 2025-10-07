from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from forest_ensys.database.base_class import Base
import pandas as pd
from datetime import datetime

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLAlchemy model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        return db.query(self.model).offset(skip).limit(limit).all()
        
    def get_multi_by_date_range(
        self, db: Session, start_date: datetime = None, end_date: datetime = None
    ) -> Optional[pd.DataFrame]:
        # Basisabfrage
        query = f"""
            SELECT * 
            FROM {self.model.__tablename__}
            WHERE timestamp BETWEEN :start_date AND :end_date
        """
        # Abfrage ausführen
        result = pd.read_sql_query(
            sql=text(query),
            con=db.connection(),
            params={
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        
        return result if not result.empty else None


    def create(
        self, db: Session, *, obj_in: Union[CreateSchemaType, ModelType, dict]
    ) -> ModelType:
        if isinstance(obj_in, self.model):
            db_obj = obj_in
        elif isinstance(obj_in, dict):
            # filter obj_in to only pass fields in model to model's constructor
            data = {
                k: v
                for k, v in obj_in.items()
                if k in self.model.__table__.columns.keys()
            }
            db_obj = self.model(**data)
        else:
            obj_in_data = jsonable_encoder(
                obj_in, include=self.model.__table__.columns.keys()
            )
            db_obj = self.model(**obj_in_data)  # type: ignore
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_multi(
        self, db: Session, *, obj_in: List[Union[CreateSchemaType, ModelType, dict]]
    ) -> List[ModelType]:
        
        def _bulk_set_attr(objs: list, attr: str, value: Any):
            for obj in objs:
                setattr(obj, attr, value)
        if isinstance(obj_in, list) and all(isinstance(obj, self.model) for obj in obj_in):
            db_obj = obj_in
        elif isinstance(obj_in, list) and all(isinstance(obj, dict) for obj in obj_in):
            db_obj = [self.model(**data) for data in obj_in]
        else:
            raise ValueError("Invalid input type")

        db.add_all(db_obj)
        db.commit()
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session) -> Optional[ModelType]:
        return db.query(self.model).delete()

    def remove(self, db: Session, *, id: Any) -> ModelType:
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj
