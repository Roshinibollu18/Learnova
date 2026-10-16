
from app import app
from models import db, Course

courses = [
    {
        "title": "Python Programming",
        "description": "Learn Python fundamentals, variables, loops, functions, and object-oriented programming.",
        "category": "Programming",
        "instructor": "Learnova Team",
        "image_url": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4",
        "duration": "6 hours",
    },
    {
        "title": "Data Science Essentials",
        "description": "Explore data analysis, data cleaning, visualization, NumPy, and Pandas.",
        "category": "Data Science",
        "instructor": "Learnova Team",
        "image_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71",
        "duration": "8 hours",
    },
    {
        "title": "Machine Learning Basics",
        "description": "Understand supervised learning, model training, evaluation, and prediction.",
        "category": "Artificial Intelligence",
        "instructor": "Learnova Team",
        "image_url": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e",
        "duration": "10 hours",
    },
    {
        "title": "Web Development",
        "description": "Learn HTML, CSS, JavaScript, and the fundamentals of building websites.",
        "category": "Web Development",
        "instructor": "Learnova Team",
        "image_url": "https://images.unsplash.com/photo-1498050108023-c5249f4df085",
        "duration": "7 hours",
    },
]

with app.app_context():
    db.create_all()

    for course_data in courses:
        existing = Course.query.filter_by(
            title=course_data["title"]
        ).first()

        if existing:
            print(f"Already exists: {course_data['title']}")
        else:
            db.session.add(Course(**course_data))
            print(f"Added: {course_data['title']}")

    db.session.commit()

    print("Database:", app.config["SQLALCHEMY_DATABASE_URI"])
    print("Total courses:", Course.query.count())
