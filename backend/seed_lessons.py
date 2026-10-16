python
from app import app
from models import db, Course, Lesson

LESSON_DATA = {
    "Python Programming": [
        (
            "Introduction to Python",
            "Python is a beginner-friendly programming language. "
            "It is widely used in automation, web development, and data science.\n\n"
            "Example:\nprint('Hello, Learnova!')",
        ),
        (
            "Variables and Data Types",
            "Variables store values. Common Python data types include "
            "integers, floats, strings, and booleans.\n\n"
            "Example:\nname = 'Roshini'\nage = 20\nprint(name, age)",
        ),
        (
            "Conditions and Loops",
            "Use if and else to make decisions. Use for and while loops "
            "to repeat instructions.\n\n"
            "Example:\nfor number in range(1, 6):\n    print(number)",
        ),
    ],
    "Data Science Essentials": [
        (
            "Introduction to Data Science",
            "Data science combines programming, statistics, and domain "
            "knowledge to find useful insights in data.",
        ),
        (
            "Working with Pandas",
            "Pandas helps you organize and analyze tabular data using "
            "Series and DataFrames.\n\n"
            "Example:\nimport pandas as pd\ndf = pd.DataFrame({'score': [80, 90]})\nprint(df)",
        ),
        (
            "Data Visualization",
            "Visualizations such as bar charts and line charts help "
            "communicate patterns, trends, and comparisons.",
        ),
    ],
    "Machine Learning Basics": [
        (
            "What Is Machine Learning?",
            "Machine learning uses data to train models that identify "
            "patterns and make predictions.",
        ),
        (
            "Supervised Learning",
            "Supervised learning trains a model using labeled examples. "
            "Classification and regression are common tasks.",
        ),
        (
            "Model Evaluation",
            "Evaluation measures how well a model performs on unseen data. "
            "Common classification metrics include accuracy, precision, "
            "recall, and F1 score.",
        ),
    ],
    "Web Development": [
        (
            "Introduction to HTML",
            "HTML structures a web page using elements such as headings, "
            "paragraphs, links, and images.",
        ),
        (
            "CSS Styling",
            "CSS controls a website's colors, spacing, layout, typography, "
            "and responsive design.",
        ),
        (
            "JavaScript Basics",
            "JavaScript adds interactivity to websites, including event "
            "handling, form validation, and dynamic page updates.",
        ),
    ],
}


with app.app_context():
    added = 0

    for course_title, lessons in LESSON_DATA.items():
        course = Course.query.filter_by(title=course_title).first()

        if not course:
            print("Course not found:", course_title)
            continue

        for index, (title, content) in enumerate(lessons, start=1):
            existing = Lesson.query.filter_by(
                course_id=course.id,
                title=title,
            ).first()

            if existing:
                continue

            db.session.add(
                Lesson(
                    title=title,
                    content=content,
                    video_url=None,
                    order=index,
                    course_id=course.id,
                )
            )
            added += 1

    db.session.commit()
    print("Lesson seeding complete. New lessons added:", added)
