from sqlalchemy import Column, Integer, String, ForeignKey
from core.database import Base


class WorkType(Base):
    __tablename__ = "work_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)


class Status(Base):
    __tablename__ = "statuses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    mobile = Column(String(20), nullable=False)
    salary = Column(Integer, nullable=True)

    work_type_id = Column(Integer, ForeignKey("work_types.id"))
    status_id = Column(Integer, ForeignKey("statuses.id"))
    shift_id = Column(Integer, ForeignKey("shifts.id"))