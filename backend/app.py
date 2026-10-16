
import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Course, Lesson, Enrollment, LessonProgress

app = Flask(__name__)

# Use the existing database. Do not delete it.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(INSTANCE_DIR, "learnova.db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite:///" + DATABASE_PATH.replace("\\", "/")
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = os.environ.get(
    "JWT_SECRET_KEY",
    "learnova-development-secret-change-before-deployment",
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=2)

CORS(app)
db.init_app(app)
jwt = JWTManager(app)


def get_current_user():
    identity = get_jwt_identity()
    if identity is None:
        return None
    return db.session.get(User, int(identity))


def require_role(role):
    user = get_current_user()

    if not user:
        return None, (jsonify({"message": "User not found."}), 404)

    if user.role != role:
        return None, (
            jsonify({"message": f"{role.title()} access required."}),
            403,
        )

    return user, None


def course_to_dict(course):
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "category": course.category,
        "instructor": course.instructor,
        "image_url": course.image_url,
        "duration": course.duration,
    }


def lesson_to_dict(lesson, completed=False):
    return {
        "id": lesson.id,
        "title": lesson.title,
        "content": lesson.content,
        "video_url": lesson.video_url,
        "order": lesson.order,
        "completed": completed,
    }


def get_enrollment(student_id, course_id):
    return Enrollment.query.filter_by(
        student_id=student_id,
        course_id=course_id,
    ).first()


def course_progress(student_id, course_id):
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    total = len(lessons)

    if total == 0:
        return {
            "total_lessons": 0,
            "completed_lessons": 0,
            "progress": 0,
        }

    lesson_ids = [lesson.id for lesson in lessons]

    completed = LessonProgress.query.filter(
        LessonProgress.student_id == student_id,
        LessonProgress.lesson_id.in_(lesson_ids),
        LessonProgress.completed.is_(True),
    ).count()

    return {
        "total_lessons": total,
        "completed_lessons": completed,
        "progress": round(completed / total * 100),
    }


@app.get("/")
def home():
    return jsonify({"message": "Welcome to Learnova API"})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


# ---------------- AUTHENTICATION ----------------

@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name or not email or not isinstance(password, str):
        return jsonify({
            "message": "Name, email, and password are required."
        }), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"message": "Enter a valid email address."}), 400

    if len(password) < 8:
        return jsonify({
            "message": "Password must be at least 8 characters."
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({
            "message": "This email is already registered."
        }), 409

    # Public registration always creates a student account.
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role="student",
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Registration successful.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    }), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    expected_role = data.get("expected_role")

    if expected_role not in ("admin", "student"):
        return jsonify({
            "message": "Please choose Admin Login or Student Login."
        }), 400

    user = User.query.filter_by(email=email).first()

    if (
        not user
        or not isinstance(password, str)
        or not check_password_hash(user.password_hash, password)
    ):
        return jsonify({"message": "Invalid email or password."}), 401

    if user.role != expected_role:
        return jsonify({
            "message": (
                f"This account is not registered as a {expected_role}. "
                "Please use the correct login page."
            )
        }), 403

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role},
    )

    return jsonify({
        "message": "Login successful.",
        "access_token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
        },
    })


@app.get("/api/me")
@jwt_required()
def me():
    user = get_current_user()

    if not user:
        return jsonify({"message": "User not found."}), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
    })


# ---------------- COURSE CATALOG ----------------

@app.get("/api/courses")
def get_courses():
    courses = Course.query.order_by(Course.id.asc()).all()
    result = []

    for course in courses:
        item = course_to_dict(course)
        item["lesson_count"] = Lesson.query.filter_by(
            course_id=course.id
        ).count()
        result.append(item)

    return jsonify(result)

# Paste these routes in the SAME Flask module/file that currently defines
# GET /api/courses. Existing imports/helpers in your app should include:
# request, jsonify, jwt_required, db, User, Course, Lesson, Enrollment, LessonProgress,
# get_current_user(), and course_to_dict().

@app.put("/api/courses/<int:course_id>")
@jwt_required()
def update_course(course_id):
    user = get_current_user()

    if not user:
        return jsonify({"message": "User not found."}), 404
    if user.role != "admin":
        return jsonify({"message": "Admin access required."}), 403

    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"message": "Course not found."}), 404

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", course.title) or "").strip()
    if not title:
        return jsonify({"message": "Course title is required."}), 400

    course.title = title
    course.description = str(data.get("description", course.description or "") or "").strip()
    course.category = str(data.get("category", course.category or "General") or "General").strip()
    course.instructor = str(data.get("instructor", course.instructor or "") or "").strip()
    course.image_url = str(data.get("image_url", course.image_url or "") or "").strip()
    course.duration = str(data.get("duration", course.duration or "") or "").strip()

    db.session.commit()
    return jsonify({
        "message": "Course updated successfully.",
        "course": course_to_dict(course),
    }), 200


@app.delete("/api/courses/<int:course_id>")
@jwt_required()
def delete_course(course_id):
    user = get_current_user()

    if not user:
        return jsonify({"message": "User not found."}), 404
    if user.role != "admin":
        return jsonify({"message": "Admin access required."}), 403

    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({"message": "Course not found."}), 404

    # Remove student progress for this course's lessons before deleting the lessons.
    lesson_ids = [
        lesson.id for lesson in Lesson.query.filter_by(course_id=course.id).all()
    ]
    if lesson_ids:
        LessonProgress.query.filter(
            LessonProgress.lesson_id.in_(lesson_ids)
        ).delete(synchronize_session=False)

    # Remove enrollments and lessons linked to this course.
    Enrollment.query.filter_by(course_id=course.id).delete(
        synchronize_session=False
    )
    Lesson.query.filter_by(course_id=course.id).delete(
        synchronize_session=False
    )

    db.session.delete(course)
    db.session.commit()

    return jsonify({"message": "Course and its related lessons and progress were deleted."}), 200


# ---------------- ADMIN COURSE MANAGEMENT ----------------

@app.post("/api/courses")
@jwt_required()
def create_course():
    user, error = require_role("admin")

    if error:
        return error

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()

    if not title:
        return jsonify({"message": "Course title is required."}), 400

    course = Course(
        title=title,
        description=str(data.get("description", "")).strip(),
        category=str(data.get("category", "General")).strip(),
        instructor=str(data.get("instructor", user.name)).strip(),
        image_url=str(data.get("image_url", "")).strip(),
        duration=str(data.get("duration", "")).strip(),
    )

    db.session.add(course)
    db.session.commit()

    return jsonify({
        "message": "Course created successfully.",
        "course": course_to_dict(course),
    }), 201


@app.post("/api/courses/<int:course_id>/lessons")
@jwt_required()
def create_lesson(course_id):
    user, error = require_role("admin")

    if error:
        return error

    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({"message": "Course not found."}), 404

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    content = str(data.get("content", "")).strip()
    video_url = str(data.get("video_url", "")).strip()

    if not title or not content:
        return jsonify({
            "message": "Lesson title and content are required."
        }), 400

    try:
        lesson_order = int(
            data.get("order")
            or (Lesson.query.filter_by(course_id=course_id).count() + 1)
        )
    except (TypeError, ValueError):
        return jsonify({
            "message": "Lesson order must be a number."
        }), 400

    lesson = Lesson(
        title=title,
        content=content,
        video_url=video_url,
        order=lesson_order,
        course_id=course_id,
    )

    db.session.add(lesson)
    db.session.commit()

    return jsonify({
        "message": "Lesson created successfully.",
        "lesson": lesson_to_dict(lesson),
    }), 201


# ---------------- STUDENT ENROLLMENT ----------------

@app.post("/api/courses/<int:course_id>/enroll")
@jwt_required()
def enroll_in_course(course_id):
    user, error = require_role("student")

    if error:
        return error

    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({"message": "Course not found."}), 404

    if get_enrollment(user.id, course_id):
        return jsonify({
            "message": "You are already enrolled in this course."
        })

    enrollment = Enrollment(
        student_id=user.id,
        course_id=course_id,
    )

    db.session.add(enrollment)
    db.session.commit()

    return jsonify({
        "message": "Successfully enrolled in the course.",
        "course_id": course_id,
    }), 201


@app.get("/api/my-courses")
@jwt_required()
def get_my_courses():
    user, error = require_role("student")

    if error:
        return error

    enrollments = Enrollment.query.filter_by(
        student_id=user.id
    ).order_by(Enrollment.id.desc()).all()

    result = []

    for enrollment in enrollments:
        course = db.session.get(Course, enrollment.course_id)

        if course:
            item = course_to_dict(course)
            item.update(course_progress(user.id, course.id))
            result.append(item)

    return jsonify(result)


# ---------------- LESSON ACCESS ----------------

@app.get("/api/courses/<int:course_id>/lessons")
@jwt_required()
def get_course_lessons(course_id):
    user = get_current_user()

    if not user:
        return jsonify({"message": "User not found."}), 404

    course = db.session.get(Course, course_id)

    if not course:
        return jsonify({"message": "Course not found."}), 404

    if user.role == "student" and not get_enrollment(
        user.id, course_id
    ):
        return jsonify({
            "message": "Enroll in this course to access its lessons."
        }), 403

    lessons = Lesson.query.filter_by(
        course_id=course_id
    ).order_by(Lesson.order.asc(), Lesson.id.asc()).all()

    results = []

    for lesson in lessons:
        progress = LessonProgress.query.filter_by(
            student_id=user.id,
            lesson_id=lesson.id,
        ).first()

        results.append(
            lesson_to_dict(
                lesson,
                completed=bool(progress and progress.completed),
            )
        )

    return jsonify({
        "course": course_to_dict(course),
        "lessons": results,
        "progress": (
            course_progress(user.id, course_id)
            if user.role == "student"
            else {
                "total_lessons": len(lessons),
                "completed_lessons": 0,
                "progress": 0,
            }
        ),
    })

@app.put("/api/lessons/<int:lesson_id>")
@jwt_required()
def update_lesson(lesson_id):
    user = get_current_user()

    if not user:
        return jsonify({"message": "User not found."}), 404

    if user.role != "admin":
        return jsonify({"message": "Admin access required."}), 403

    lesson = db.session.get(Lesson, lesson_id)

    if not lesson:
        return jsonify({"message": "Lesson not found."}), 404

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", lesson.title)).strip()
    content = str(data.get("content", lesson.content)).strip()
    video_url = str(
        data.get("video_url", lesson.video_url or "")
    ).strip()

    if not title or not content:
        return jsonify({
            "message": "Lesson title and content are required."
        }), 400

    try:
        lesson_order = int(
            data.get("order") or lesson.order or 1
        )
    except (TypeError, ValueError):
        return jsonify({
            "message": "Lesson order must be a number."
        }), 400

    lesson.title = title
    lesson.content = content
    lesson.video_url = video_url
    lesson.order = lesson_order

    db.session.commit()

    return jsonify({
        "message": "Lesson updated successfully.",
        "lesson": lesson_to_dict(lesson),
    }), 200
@app.post("/api/lessons/<int:lesson_id>/complete")
@jwt_required()
def complete_lesson(lesson_id):
    user, error = require_role("student")

    if error:
        return error

    lesson = db.session.get(Lesson, lesson_id)

    if not lesson:
        return jsonify({"message": "Lesson not found."}), 404

    if not get_enrollment(user.id, lesson.course_id):
        return jsonify({
            "message": "Enroll in the course before completing lessons."
        }), 403

    progress = LessonProgress.query.filter_by(
        student_id=user.id,
        lesson_id=lesson.id,
    ).first()

    if not progress:
        progress = LessonProgress(
            student_id=user.id,
            lesson_id=lesson.id,
            completed=True,
            completed_at=datetime.utcnow(),
        )
        db.session.add(progress)
    else:
        progress.completed = True
        progress.completed_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "message": "Lesson marked as completed.",
        "course_id": lesson.course_id,
        **course_progress(user.id, lesson.course_id),
    })


# ---------------- STUDENT DASHBOARD ----------------

@app.get("/api/dashboard")
@jwt_required()
def student_dashboard():
    user, error = require_role("student")

    if error:
        return error

    enrollments = Enrollment.query.filter_by(
        student_id=user.id
    ).all()

    course_data = []

    for enrollment in enrollments:
        course = db.session.get(Course, enrollment.course_id)

        if course:
            item = course_to_dict(course)
            item.update(course_progress(user.id, course.id))
            course_data.append(item)

    completed_courses = sum(
        1 for course in course_data
        if course["total_lessons"] > 0
        and course["progress"] == 100
    )

    return jsonify({
        "student": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
        "total_enrolled": len(course_data),
        "completed_courses": completed_courses,
        "courses": course_data,
    })


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
