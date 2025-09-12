from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from forest_ensys.database.base_class import Base


class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    process_electricity = relationship("ProcessElectricity", back_populates="user")
    process_heat = relationship("ProcessHeat", back_populates="user")
    model = relationship("Model", back_populates="user")
