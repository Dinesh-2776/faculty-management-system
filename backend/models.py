from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    faculty = relationship("Faculty", back_populates="department")


class Faculty(Base):
    __tablename__ = "faculty"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    phone = Column(String(20))
    designation = Column(String(60), nullable=False)
    joining_date = Column(Date)
    max_hours_per_week = Column(Integer, default=16)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    department = relationship("Department", back_populates="faculty")
    courses = relationship("Course", back_populates="faculty")
    leaves = relationship("LeaveRequest", back_populates="faculty", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    title = Column(String(150), nullable=False)
    credits = Column(Integer, default=3)
    hours_per_week = Column(Integer, default=3)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)

    faculty = relationship("Faculty", back_populates="courses")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, autoincrement=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(Text)
    status = Column(Enum("Pending", "Approved", "Rejected"), default="Pending")

    faculty = relationship("Faculty", back_populates="leaves")
