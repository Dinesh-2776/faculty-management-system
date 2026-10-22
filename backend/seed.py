from datetime import date
import models


def seed_if_empty(db):
    if db.query(models.Department).count() > 0:
        return
    depts = [models.Department(name=n) for n in
             ["Computer Science", "Electronics", "Mechanical", "Mathematics"]]
    db.add_all(depts)
    db.flush()
    d = {x.name: x.id for x in depts}

    fac = [
        models.Faculty(name="Dr. Ananya Rao", email="ananya.rao@college.edu", phone="9800000001",
                       designation="Professor", joining_date=date(2012, 6, 1), max_hours_per_week=14,
                       department_id=d["Computer Science"]),
        models.Faculty(name="Prof. Karthik Nair", email="karthik.nair@college.edu", phone="9800000002",
                       designation="Associate Professor", joining_date=date(2016, 7, 15), max_hours_per_week=16,
                       department_id=d["Computer Science"]),
        models.Faculty(name="Ms. Divya Shetty", email="divya.shetty@college.edu", phone="9800000003",
                       designation="Assistant Professor", joining_date=date(2021, 8, 1), max_hours_per_week=18,
                       department_id=d["Electronics"]),
        models.Faculty(name="Dr. Rahul Verma", email="rahul.verma@college.edu", phone="9800000004",
                       designation="Professor", joining_date=date(2010, 1, 10), max_hours_per_week=14,
                       department_id=d["Mechanical"]),
        models.Faculty(name="Ms. Sneha Iyer", email="sneha.iyer@college.edu", phone="9800000005",
                       designation="Assistant Professor", joining_date=date(2022, 9, 5), max_hours_per_week=18,
                       department_id=d["Mathematics"]),
    ]
    db.add_all(fac)
    db.flush()

    db.add_all([
        models.Course(code="CS301", title="Database Systems", credits=4, hours_per_week=5, faculty_id=fac[0].id),
        models.Course(code="CS302", title="Machine Learning", credits=4, hours_per_week=5, faculty_id=fac[0].id),
        models.Course(code="CS303", title="Web Technologies", credits=3, hours_per_week=4, faculty_id=fac[1].id),
        models.Course(code="CS304", title="Operating Systems", credits=4, hours_per_week=5, faculty_id=fac[1].id),
        models.Course(code="CS305", title="Generative AI", credits=3, hours_per_week=4, faculty_id=fac[1].id),
        models.Course(code="EC201", title="Digital Electronics", credits=4, hours_per_week=5, faculty_id=fac[2].id),
        models.Course(code="ME210", title="Thermodynamics", credits=4, hours_per_week=5, faculty_id=fac[3].id),
        models.Course(code="MA101", title="Linear Algebra", credits=3, hours_per_week=4, faculty_id=fac[4].id),
        models.Course(code="CS306", title="Cloud Computing", credits=3, hours_per_week=4, faculty_id=None),
        models.Course(code="EC202", title="Embedded Systems", credits=3, hours_per_week=4, faculty_id=None),
    ])

    db.add_all([
        models.LeaveRequest(faculty_id=fac[0].id, start_date=date(2026, 10, 27), end_date=date(2026, 10, 30),
                            reason="Attending an AI conference", status="Pending"),
        models.LeaveRequest(faculty_id=fac[2].id, start_date=date(2026, 11, 3), end_date=date(2026, 11, 4),
                            reason="Medical appointment", status="Approved"),
        models.LeaveRequest(faculty_id=fac[1].id, start_date=date(2026, 10, 28), end_date=date(2026, 10, 29),
                            reason="Family function", status="Pending"),
    ])
    db.commit()
