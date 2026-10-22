from datetime import date
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
import agents
from database import engine, get_db, SessionLocal
from seed import seed_if_empty

models.Base.metadata.create_all(bind=engine)
with SessionLocal() as _db:
    seed_if_empty(_db)

app = FastAPI(title="College Faculty Management System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- schemas
class FacultyIn(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    designation: str
    joining_date: Optional[date] = None
    max_hours_per_week: int = 16
    department_id: int


class CourseIn(BaseModel):
    code: str
    title: str
    credits: int = 3
    hours_per_week: int = 3
    faculty_id: Optional[int] = None


class AssignIn(BaseModel):
    faculty_id: Optional[int] = None


class LeaveIn(BaseModel):
    faculty_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None


class StatusIn(BaseModel):
    status: str


class AskIn(BaseModel):
    text: str


# ---------------------------------------------------------------- helpers
def fac_dict(f):
    hrs = sum(c.hours_per_week or 0 for c in f.courses)
    return {"id": f.id, "name": f.name, "email": f.email, "phone": f.phone, "designation": f.designation,
            "joining_date": str(f.joining_date) if f.joining_date else None,
            "max_hours_per_week": f.max_hours_per_week, "department_id": f.department_id,
            "department": f.department.name, "assigned_hours": hrs}


def course_dict(c):
    return {"id": c.id, "code": c.code, "title": c.title, "credits": c.credits,
            "hours_per_week": c.hours_per_week, "faculty_id": c.faculty_id,
            "faculty": c.faculty.name if c.faculty else None}


def leave_dict(l):
    return {"id": l.id, "faculty_id": l.faculty_id, "faculty": l.faculty.name, "start_date": str(l.start_date),
            "end_date": str(l.end_date), "reason": l.reason, "status": l.status}


def commit_or_400(db, msg):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, msg)


# ---------------------------------------------------------------- dashboard + departments
@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    return {
        "faculty": db.query(models.Faculty).count(),
        "departments": db.query(models.Department).count(),
        "courses": db.query(models.Course).count(),
        "unassigned_courses": db.query(models.Course).filter(models.Course.faculty_id.is_(None)).count(),
        "pending_leaves": db.query(models.LeaveRequest).filter(models.LeaveRequest.status == "Pending").count(),
        "workload": agents.tool_workload(db),
    }


@app.get("/api/departments")
def departments(db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name} for d in db.query(models.Department).all()]


# ---------------------------------------------------------------- faculty CRUD
@app.get("/api/faculty")
def list_faculty(db: Session = Depends(get_db)):
    return [fac_dict(f) for f in db.query(models.Faculty).order_by(models.Faculty.name).all()]


@app.post("/api/faculty", status_code=201)
def add_faculty(body: FacultyIn, db: Session = Depends(get_db)):
    f = models.Faculty(**body.model_dump())
    db.add(f)
    commit_or_400(db, "Email already exists or department is invalid")
    db.refresh(f)
    return fac_dict(f)


@app.put("/api/faculty/{fid}")
def update_faculty(fid: int, body: FacultyIn, db: Session = Depends(get_db)):
    f = db.get(models.Faculty, fid)
    if not f:
        raise HTTPException(404, "Faculty not found")
    for k, v in body.model_dump().items():
        setattr(f, k, v)
    commit_or_400(db, "Email already exists or department is invalid")
    db.refresh(f)
    return fac_dict(f)


@app.delete("/api/faculty/{fid}")
def delete_faculty(fid: int, db: Session = Depends(get_db)):
    f = db.get(models.Faculty, fid)
    if not f:
        raise HTTPException(404, "Faculty not found")
    for c in f.courses:  # free their courses instead of deleting them
        c.faculty_id = None
    db.delete(f)
    db.commit()
    return {"deleted": fid}


# ---------------------------------------------------------------- courses
@app.get("/api/courses")
def list_courses(db: Session = Depends(get_db)):
    return [course_dict(c) for c in db.query(models.Course).order_by(models.Course.code).all()]


@app.post("/api/courses", status_code=201)
def add_course(body: CourseIn, db: Session = Depends(get_db)):
    c = models.Course(**body.model_dump())
    db.add(c)
    commit_or_400(db, "Course code already exists")
    db.refresh(c)
    return course_dict(c)


@app.patch("/api/courses/{cid}/assign")
def assign_course(cid: int, body: AssignIn, db: Session = Depends(get_db)):
    c = db.get(models.Course, cid)
    if not c:
        raise HTTPException(404, "Course not found")
    c.faculty_id = body.faculty_id
    db.commit()
    db.refresh(c)
    return course_dict(c)


@app.delete("/api/courses/{cid}")
def delete_course(cid: int, db: Session = Depends(get_db)):
    c = db.get(models.Course, cid)
    if not c:
        raise HTTPException(404, "Course not found")
    db.delete(c)
    db.commit()
    return {"deleted": cid}


# ---------------------------------------------------------------- leaves
@app.get("/api/leaves")
def list_leaves(db: Session = Depends(get_db)):
    return [leave_dict(l) for l in db.query(models.LeaveRequest).order_by(models.LeaveRequest.start_date).all()]


@app.post("/api/leaves", status_code=201)
def add_leave(body: LeaveIn, db: Session = Depends(get_db)):
    if body.end_date < body.start_date:
        raise HTTPException(400, "End date must be on or after the start date")
    l = models.LeaveRequest(**body.model_dump())
    db.add(l)
    commit_or_400(db, "Faculty not found")
    db.refresh(l)
    return leave_dict(l)


@app.patch("/api/leaves/{lid}/status")
def set_leave_status(lid: int, body: StatusIn, db: Session = Depends(get_db)):
    if body.status not in ("Approved", "Rejected", "Pending"):
        raise HTTPException(400, "Status must be Approved, Rejected or Pending")
    l = db.get(models.LeaveRequest, lid)
    if not l:
        raise HTTPException(404, "Leave request not found")
    l.status = body.status
    db.commit()
    db.refresh(l)
    return leave_dict(l)


# ---------------------------------------------------------------- GenAI
@app.post("/api/ai/single")
def ai_single(body: AskIn, db: Session = Depends(get_db)):
    try:
        return agents.run_single_agent(db, body.text)
    except Exception as e:
        raise HTTPException(500, f"AI error: {e}")


@app.post("/api/ai/multi")
def ai_multi(body: AskIn, db: Session = Depends(get_db)):
    try:
        return agents.run_multi_agent(db, body.text)
    except Exception as e:
        raise HTTPException(500, f"AI error: {e}")
