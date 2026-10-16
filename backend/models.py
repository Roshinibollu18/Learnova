
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    courses_created = db.relationship("Course", back_populates="creator")
    enrollments = db.relationship(
        "Enrollment", back_populates="student",
        cascade="all, delete-orphan"
    )


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    instructor = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500))
    duration = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=utc_now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    creator = db.relationship("User", back_populates="courses_created")
    lessons = db.relationship(
        "Lesson", back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lesson.order"
    )
    enrollments = db.relationship(
        "Enrollment", back_populates="course",
        cascade="all, delete-orphan"
    )


class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(500))
    order = db.Column(db.Integer, nullable=False, default=1)
    course_id = db.Column(
        db.Integer, db.ForeignKey("courses.id"), nullable=False
    )

    course = db.relationship("Course", back_populates="lessons")
    progress_records = db.relationship(
        "LessonProgress", back_populates="lesson",
        cascade="all, delete-orphan"
    )


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    course_id = db.Column(
        db.Integer, db.ForeignKey("courses.id"), nullable=False
    )
    enrolled_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    student = db.relationship("User", back_populates="enrollments")
    course = db.relationship("Course", back_populates="enrollments")

    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", name="unique_enrollment"),
    )


class LessonProgress(db.Model):
    __tablename__ = "lesson_progress"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    lesson_id = db.Column(
        db.Integer, db.ForeignKey("lessons.id"), nullable=False
    )
    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime(timezone=True))

    lesson = db.relationship("Lesson", back_populates="progress_records")

    __table_args__ = (
        db.UniqueConstraint("student_id", "lesson_id", name="unique_lesson_progress"),
    )
