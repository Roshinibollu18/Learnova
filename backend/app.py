import os
import requests
from dotenv import load_dotenv
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
load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), ".env")
)

app = Flask(__name__)

# Use the existing database. Do not delete it.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
load_dotenv(os.path.join(BASE_DIR, ".env"))
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

    # Add sample courses only if the database is empty
    if Course.query.count() == 0:
        starter_courses = [
            Course(
                title="Python Programming",
                description="Learn Python basics, variables, loops, and functions.",
                category="Programming",
                instructor="Learnova Team",
                image_url="",
                duration="4 weeks",
            ),
            Course(
                title="Data Science Essentials",
                description="Learn data analysis and data visualization.",
                category="Data Science",
                instructor="Learnova Team",
                image_url="",
                duration="5 weeks",
            ),
            Course(
                title="Machine Learning Basics",
                description="Explore machine learning concepts and algorithms.",
                category="Machine Learning",
                instructor="Learnova Team",
                image_url="",
                duration="6 weeks",
            ),
            Course(
                title="Web Development",
                description="Learn HTML, CSS, and JavaScript fundamentals.",
                category="Web Development",
                instructor="Learnova Team",
                image_url="",
                duration="4 weeks",
            ),
            Course(
                title="Artificial Intelligence",
                description="Explore AI concepts and practical applications.",
                category="Artificial Intelligence",
                instructor="Learnova Team",
                image_url="",
                duration="5 weeks",
            ),
        ]

        db.session.add_all(starter_courses)
        db.session.commit()

@app.post("/api/chat")
@jwt_required()
def ai_chat():
    # --------------------------------------------------
    # 1. Read and validate the request
    # --------------------------------------------------
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:
        return jsonify({
            "message": (
                "Gemini API key is missing. "
                "Check the backend .env file."
            )
        }), 500

    data = request.get_json(silent=True) or {}

    question = str(
        data.get("message")
        or data.get("question")
        or data.get("prompt")
        or ""
    ).strip()

    history = data.get("history", [])

    if not question:
        return jsonify({
            "message": "Please enter a question."
        }), 400

    if len(question) > 2000:
        return jsonify({
            "message": (
                "Please keep your question under "
                "2000 characters."
            )
        }), 400

    # --------------------------------------------------
    # 2. Identify the logged-in user
    # --------------------------------------------------
    user = get_current_user()

    if not user:
        return jsonify({
            "message": (
                "Your login session may have expired. "
                "Please log in again."
            )
        }), 401

    # --------------------------------------------------
    # 3. Collect verified student learning progress
    # --------------------------------------------------
    student_context = (
        "Personal student learning information "
        "has not been provided."
    )

    role = str(
        getattr(user, "role", "")
    ).lower()

    if role == "student":
        try:
            enrolled_records = []

            enrollments = Enrollment.query.filter_by(
                student_id=user.id
            ).all()

            for enrollment in enrollments:
                course = db.session.get(
                    Course,
                    enrollment.course_id
                )

                if course is None:
                    continue

                lessons = Lesson.query.filter_by(
                    course_id=course.id
                ).order_by(
                    Lesson.order.asc()
                ).all()

                completed_titles = []
                unfinished_titles = []

                for lesson in lessons:
                    progress_record = (
                        LessonProgress.query.filter_by(
                            student_id=user.id,
                            lesson_id=lesson.id
                        ).first()
                    )

                    if (
                        progress_record
                        and progress_record.completed
                    ):
                        completed_titles.append(
                            lesson.title
                        )
                    else:
                        unfinished_titles.append(
                            lesson.title
                        )

                total_lessons = len(lessons)
                completed_count = len(
                    completed_titles
                )

                percentage = (
                    round(
                        completed_count
                        / total_lessons
                        * 100
                    )
                    if total_lessons > 0
                    else 0
                )

                enrolled_records.append({
                    "course": course.title,
                    "total_lessons": total_lessons,
                    "completed_lessons": completed_count,
                    "progress_percent": percentage,
                    "completed_lesson_titles": (
                        completed_titles[:20]
                    ),
                    "unfinished_lessons": (
                        unfinished_titles[:20]
                    )
                })

            student_context = (
                f"Student name: {user.name}\n"
                f"Enrolled course records: "
                f"{enrolled_records}"
            )

            if not enrolled_records:
                student_context += (
                    "\nNo enrolled courses were found "
                    "for this student."
                )

        except Exception as error:
            # A progress-query problem should not prevent
            # the tutor from answering general questions.
            print(
                "Student progress lookup failed:",
                str(error)
            )

            student_context = (
                "Student progress could not be retrieved "
                "from the database for this request. "
                "Do not invent personal progress."
            )

    elif role == "admin":
        student_context = (
            "The logged-in user is an administrator. "
            "No personal student progress is provided."
        )

    # --------------------------------------------------
    # 4. Set the tutor's instructions
    # --------------------------------------------------
    system_prompt = f"""
You are Learnova AI Tutor, a friendly, patient,
knowledgeable learning assistant for students.

YOUR MAIN PURPOSE:
Help students understand concepts, study effectively,
solve learning problems, practise skills, and improve.

TOPICS YOU CAN HELP WITH:
- Python, Java, JavaScript, C, C++, SQL and programming
- HTML, CSS, React, Flask and web development
- Data structures and algorithms
- Artificial intelligence and machine learning
- Data science, NumPy, Pandas and data analysis
- Mathematics, science and academic concepts
- Databases, software engineering and computer science
- Project explanations, debugging and interview preparation
- Study plans, revision strategies and practice questions
- Other general educational and knowledge questions

HOW TO ANSWER:
1. Answer the student's actual question directly.
2. Use clear, student-friendly language.
3. Give examples, code or step-by-step explanations
   when they would make the answer more useful.
4. Explain technical terms in simple words.
5. If the student asks a follow-up, use the conversation
   history to understand what they mean.
6. If a question is ambiguous, state your assumption
   or ask a brief follow-up question.
7. Never claim that you executed code or checked a live
   system unless that actually happened.
8. Be honest when you are uncertain.
9. Do not invent sources, facts or student information.
10. Keep answers useful and reasonably concise, but give
    more detail when the student requests it.

PERSONAL LEARNING PROGRESS:
Use only the verified student context below for claims
about the logged-in student's enrollments, lessons,
and completion percentages.
If progress data is missing, say that it is unavailable.
Never guess or fabricate a student's progress.
Use the unfinished lesson list to recommend what to study
next when the student asks.

VERIFIED STUDENT CONTEXT:
{student_context}
"""

    # --------------------------------------------------
    # 5. Convert chat history into Gemini format
    # --------------------------------------------------
    contents = []

    if isinstance(history, list):
        for item in history[-10:]:
            if not isinstance(item, dict):
                continue

            raw_role = str(
                item.get("role")
                or item.get("sender")
                or ""
            ).lower()

            if raw_role in (
                "assistant",
                "ai",
                "bot",
                "model"
            ):
                gemini_role = "model"

            elif raw_role in (
                "user",
                "student",
                "human"
            ):
                gemini_role = "user"

            else:
                continue

            # Support several common frontend history formats.
            message_text = (
                item.get("text")
                or item.get("content")
                or item.get("message")
                or ""
            )

            if isinstance(message_text, list):
                message_text = " ".join(
                    str(part.get("text", ""))
                    for part in message_text
                    if isinstance(part, dict)
                )

            if not isinstance(message_text, str):
                continue

            message_text = message_text.strip()

            if not message_text:
                continue

            contents.append({
                "role": gemini_role,
                "parts": [{
                    "text": message_text[:3000]
                }]
            })

    # Gemini conversations should begin with a user message.
    while (
        contents
        and contents[0]["role"] != "user"
    ):
        contents.pop(0)

    # Avoid adding the current question twice if the frontend
    # already included it in its history.
    question_already_added = (
        bool(contents)
        and contents[-1]["role"] == "user"
        and contents[-1]["parts"][0]["text"].strip()
        == question
    )

    if not question_already_added:
        contents.append({
            "role": "user",
            "parts": [{"text": question}]
        })

    # --------------------------------------------------
    # 6. Call Gemini with a fallback model
    # --------------------------------------------------
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite"
    ]

    last_error = "No Gemini model returned an answer."

    for model_name in models_to_try:
        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            f"{model_name}:generateContent"
        )

        payload = {
            "systemInstruction": {
                "parts": [{
                    "text": system_prompt
                }]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1200,
                "thinkingConfig": {
                    "thinkingLevel": "low"
                }
            }
        }

        try:
            result = requests.post(
                url,
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=(8, 25)
            )

        except requests.Timeout:
            last_error = (
                f"{model_name} timed out while generating "
                "a response."
            )

            print("Gemini timeout:", last_error)
            continue

        except requests.RequestException as error:
            last_error = (
                f"Connection problem with {model_name}."
            )

            print(
                "Gemini connection error:",
                str(error)
            )
            continue

        # Handle unsuccessful API responses.
        if not result.ok:
            print(
                f"Gemini API error for {model_name}:",
                result.status_code,
                result.text[:1000]
            )

            last_error = (
                f"Gemini returned HTTP "
                f"{result.status_code} for {model_name}."
            )

            # These usually indicate an authentication or
            # request-configuration problem. Retrying other
            # models will not normally correct those problems.
            if result.status_code in (400, 401, 403):
                break

            # Try another model for unavailable-model,
            # quota, rate-limit or temporary server errors.
            continue

        try:
            response_data = result.json()
        except ValueError:
            last_error = (
                "Gemini returned an invalid response."
            )
            continue

        candidates = response_data.get(
            "candidates", []
        )

        reply_parts = []

        if candidates:
            candidate = candidates[0]

            candidate_content = candidate.get(
                "content", {}
            )

            for part in candidate_content.get(
                "parts", []
            ):
                if (
                    isinstance(part, dict)
                    and isinstance(part.get("text"), str)
                ):
                    reply_parts.append(
                        part["text"]
                    )

        reply = "\n".join(
            reply_parts
        ).strip()

        if reply:
            # Return several common response field names so
            # the existing frontend can read the answer.
            return jsonify({
                "reply": reply,
                "answer": reply,
                "response": reply,
                "message": reply
            }), 200

        last_error = (
            f"{model_name} returned no answer text."
        )

        print(
            "Gemini returned no text:",
            str(response_data)[:1000]
        )

    # --------------------------------------------------
    # 7. Return a useful error if every attempt fails
    # --------------------------------------------------
    print(
        "All Gemini attempts failed:",
        last_error
    )

    return jsonify({
        "message": (
            "The AI Tutor could not get a response from "
            "Gemini. Please try again. "
            f"Details: {last_error}"
        )
    }), 502
if __name__ == "__main__":
    app.run(debug=True, port=5000)