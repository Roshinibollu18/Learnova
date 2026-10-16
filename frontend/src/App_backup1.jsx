
import { useCallback, useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:5000";

export default function App() {
  const [page, setPage] = useState("home");
  const [courses, setCourses] = useState([]);
  const [myCourses, setMyCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [progress, setProgress] = useState({});
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem("learnova_user");
      const savedToken = localStorage.getItem("learnova_token");
      return savedUser && savedToken ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
  });

  const [courseForm, setCourseForm] = useState({
    title: "",
    description: "",
    category: "General",
    instructor: "",
    image_url: "",
    duration: "",
  });

  const [lessonForm, setLessonForm] = useState({
    title: "",
    content: "",
    video_url: "",
    order: "",
  });

  // State used when editing an existing lesson
  const [editingLessonId, setEditingLessonId] = useState(null);
  const [editLessonForm, setEditLessonForm] = useState({
    title: "",
    content: "",
    video_url: "",
    order: "",
  });

  const token = localStorage.getItem("learnova_token");

  const apiRequest = useCallback(
    async (path, options = {}) => {
      const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...(options.headers || {}),
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.message || data.error || "Request failed.");
      }

      return data;
    },
    [token]
  );

  const loadCourses = useCallback(async () => {
    try {
      const data = await apiRequest("/api/courses");
      setCourses(Array.isArray(data) ? data : []);
    } catch (error) {
      setMessage(error.message);
    }
  }, [apiRequest]);

  const loadMyCourses = useCallback(async () => {
    if (!user || user.role !== "student") return;

    try {
      const data = await apiRequest("/api/my-courses");
      setMyCourses(Array.isArray(data) ? data : []);
    } catch (error) {
      setMessage(error.message);
    }
  }, [apiRequest, user]);

  useEffect(() => {
    loadCourses();
  }, [loadCourses]);

  useEffect(() => {
    loadMyCourses();
  }, [loadMyCourses]);

  function goTo(nextPage) {
    setPage(nextPage);
    setMessage("");
    setForm({ name: "", email: "", password: "" });
  }

  function handleFormChange(event) {
    const { name, value } = event.target;
    setForm((old) => ({ ...old, [name]: value }));
  }

  async function handleAuth(event) {
    event.preventDefault();
    setMessage("");
    setLoading(true);

    const isSignup = page === "signup";
    const expectedRole = page === "adminLogin" ? "admin" : "student";

    try {
      const data = await apiRequest(
        isSignup ? "/api/register" : "/api/login",
        {
          method: "POST",
          body: JSON.stringify({
            ...form,
            ...(isSignup ? {} : { expected_role: expectedRole }),
          }),
        }
      );

      if (isSignup) {
        setForm({ name: "", email: "", password: "" });
        setPage("studentLogin");
        setMessage("Account created. Please log in.");
        return;
      }

      localStorage.setItem("learnova_token", data.access_token);
      localStorage.setItem("learnova_user", JSON.stringify(data.user));

      setUser(data.user);
      setForm({ name: "", email: "", password: "" });
      setMessage("");
      setPage(data.user.role === "admin" ? "admin" : "dashboard");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("learnova_token");
    localStorage.removeItem("learnova_user");
    setUser(null);
    setMyCourses([]);
    setSelectedCourse(null);
    setLessons([]);
    setPage("home");
    setMessage("");
  }

  async function enroll(course) {
    setMessage("");

    if (!user) {
      goTo("studentLogin");
      return;
    }

    if (user.role !== "student") {
      setMessage("Only students can enroll in courses.");
      return;
    }

    try {
      const data = await apiRequest(
        `/api/courses/${course.id}/enroll`,
        { method: "POST", body: JSON.stringify({}) }
      );

      setMessage(data.message || "Successfully enrolled.");
      await loadMyCourses();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function openLessons(course) {
    setMessage("");

    try {
      const data = await apiRequest(
        `/api/courses/${course.id}/lessons`
      );

      setSelectedCourse(data.course || course);
      setLessons(data.lessons || []);
      setProgress(data.progress || {});
      setPage("lessons");
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function completeLesson(lesson) {
    try {
      const data = await apiRequest(
        `/api/lessons/${lesson.id}/complete`,
        { method: "POST", body: JSON.stringify({}) }
      );

      setLessons((old) =>
        old.map((item) =>
          item.id === lesson.id ? { ...item, completed: true } : item
        )
      );

      setProgress(data);
      setMessage("Lesson marked as completed.");
      await loadMyCourses();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function addCourse(event) {
    event.preventDefault();

    try {
      const data = await apiRequest("/api/courses", {
        method: "POST",
        body: JSON.stringify(courseForm),
      });

      setMessage(data.message || "Course added successfully.");
      setCourseForm({
        title: "",
        description: "",
        category: "General",
        instructor: "",
        image_url: "",
        duration: "",
      });

      await loadCourses();
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function addLesson(event) {
    event.preventDefault();

    if (!selectedCourse) {
      setMessage("Please select a course first.");
      return;
    }

    try {
      const data = await apiRequest(
        `/api/courses/${selectedCourse.id}/lessons`,
        {
          method: "POST",
          body: JSON.stringify({
            ...lessonForm,
            order: lessonForm.order
              ? Number(lessonForm.order)
              : undefined,
          }),
        }
      );

      setMessage(data.message || "Lesson added successfully.");
      setLessonForm({
        title: "",
        content: "",
        video_url: "",
        order: "",
      });

      await loadCourses();

      const refreshed = await apiRequest(
        `/api/courses/${selectedCourse.id}/lessons`
      );

      setLessons(refreshed.lessons || []);
    } catch (error) {
      setMessage(error.message);
    }
  }

  function startEditLesson(lesson) {
    setEditingLessonId(lesson.id);
    setEditLessonForm({
      title: lesson.title || "",
      content: lesson.content || "",
      video_url: lesson.video_url || "",
      order: String(lesson.order ?? ""),
    });
    setMessage("");
  }

  function cancelEditLesson() {
    setEditingLessonId(null);
    setEditLessonForm({
      title: "",
      content: "",
      video_url: "",
      order: "",
    });
  }

  async function saveLessonEdit(event, lesson) {
    event.preventDefault();
    setMessage("");

    try {
      const payload = {
        title: editLessonForm.title.trim(),
        content: editLessonForm.content.trim(),
        video_url: editLessonForm.video_url.trim(),
        order: editLessonForm.order
          ? Number(editLessonForm.order)
          : Number(lesson.order || 1),
      };

      const data = await apiRequest(`/api/lessons/${lesson.id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      const updatedLesson = data.lesson || payload;
      setLessons((oldLessons) =>
        oldLessons.map((item) =>
          item.id === lesson.id ? { ...item, ...updatedLesson } : item
        )
      );
      setEditingLessonId(null);
      setMessage(data.message || "Lesson updated successfully.");
      await loadCourses();
    } catch (error) {
      setMessage(error.message || "Unable to update lesson.");
    }
  }

  const isAuthPage = [
    "adminLogin",
    "studentLogin",
    "signup",
  ].includes(page);

  return (
    <div className="app">
      <header className="navbar">
        <button
          className="logo"
          onClick={() => goTo("home")}
          type="button"
        >
          Learnova<span>.</span>
        </button>

        <nav>
          <button onClick={() => goTo("home")} type="button">
            Home
          </button>

          <button
            onClick={() => {
              goTo("home");
              setTimeout(() => {
                document
                  .getElementById("courses")
                  ?.scrollIntoView({ behavior: "smooth" });
              }, 100);
            }}
            type="button"
          >
            Courses
          </button>

          {user ? (
            <>
              {user.role === "student" && (
                <button
                  onClick={() => goTo("dashboard")}
                  type="button"
                >
                  My Learning
                </button>
              )}

              {user.role === "admin" && (
                <button
                  onClick={() => goTo("admin")}
                  type="button"
                >
                  Admin Dashboard
                </button>
              )}

              <button
                className="nav-signup"
                onClick={logout}
                type="button"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => goTo("studentLogin")}
                type="button"
              >
                Student Login
              </button>

              <button
                onClick={() => goTo("adminLogin")}
                type="button"
              >
                Admin Login
              </button>

              <button
                className="nav-signup"
                onClick={() => goTo("signup")}
                type="button"
              >
                Sign Up
              </button>
            </>
          )}
        </nav>
      </header>

      {message && !isAuthPage && (
        <div className="global-message">
          <span>{message}</span>
          <button
            type="button"
            onClick={() => setMessage("")}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      {page === "home" && (
        <>
          <section className="hero">
            <div className="hero-content">
              <p className="eyebrow">LEARN SOMETHING NEW EVERY DAY</p>

              <h1>
                Your journey to
                <br />
                <span>knowledge starts here.</span>
              </h1>

              <p>
                Explore new skills, learn from structured courses, and
                take the next step toward your goals with Learnova.
              </p>

              <div className="hero-actions">
                <button
                  className="primary-button"
                  onClick={() => goTo("signup")}
                  type="button"
                >
                  Start Learning →
                </button>

                <button
                  className="secondary-button"
                  onClick={() => goTo("studentLogin")}
                  type="button"
                >
                  Student Login
                </button>
              </div>

              <div className="hero-note">
                ✦ Learn at your own pace, grow every day.
              </div>
            </div>

            <div className="hero-art">
              <div className="art-orbit orbit-one"></div>
              <div className="art-orbit orbit-two"></div>
              <div className="art-book">📚</div>

              <div className="floating-card floating-card-one">
                ✦ <span>Keep learning</span>
              </div>

              <div className="floating-card floating-card-two">
                ✓ <span>Track your progress</span>
              </div>

              <div className="art-caption">
                <strong>Small steps.</strong>
                <br />
                Big possibilities.
              </div>
            </div>
          </section>

          <section className="courses-section" id="courses">
            <div className="section-heading">
              <div>
                <p className="eyebrow">EXPLORE AND GROW</p>
                <h2>Popular Courses</h2>
                <p className="section-description">
                  Build practical skills with learning resources designed
                  for your next step.
                </p>
              </div>

              <span className="course-count">
                {courses.length} courses
              </span>
            </div>

            {courses.length === 0 ? (
              <p className="empty-state">
                No courses available yet.
              </p>
            ) : (
              <div className="course-grid">
                {courses.map((course, index) => (
                  <article className="course-card" key={course.id}>
                    {course.image_url ? (
                      <img
                        src={course.image_url}
                        alt={course.title}
                        className="course-image"
                      />
                    ) : (
                      <div
                        className={`course-image course-art art-${index % 4}`}
                      >
                        <span>
                          {["⌘", "◈", "✳", "▱"][index % 4]}
                        </span>
                        <small>{course.category || "LEARNING"}</small>
                      </div>
                    )}

                    <div className="course-info">
                      <span className="course-category">
                        {course.category || "Learning"}
                      </span>

                      <h3>{course.title}</h3>

                      <p>
                        {course.description ||
                          "Build your knowledge with this structured course."}
                      </p>

                      <div className="course-meta">
                        <span>◷ {course.duration || "Self-paced"}</span>
                        <span>{course.lesson_count ?? 0} lessons</span>
                      </div>

                      {user?.role === "student" ? (
                        <button
                          className="course-button"
                          onClick={() => enroll(course)}
                          type="button"
                        >
                          Enroll in course →
                        </button>
                      ) : user?.role === "admin" ? (
                        <button
                          className="course-button"
                          onClick={() => {
                            setSelectedCourse(course);
                            setPage("admin");
                            setMessage("");
                          }}
                          type="button"
                        >
                          Manage lessons →
                        </button>
                      ) : (
                        <button
                          className="course-button"
                          onClick={() => goTo("studentLogin")}
                          type="button"
                        >
                          Login to learn →
                        </button>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="bottom-cta">
            <p className="eyebrow">YOUR NEXT CHAPTER STARTS HERE</p>
            <h2>Curiosity is your superpower.</h2>
            <p>Choose a course and take the first step today.</p>
            <button
              className="primary-button"
              onClick={() => goTo("signup")}
              type="button"
            >
              Create free student account →
            </button>
          </section>
        </>
      )}

      {isAuthPage && (
        <section className="auth-section">
          <div className="auth-decoration">
            <div className="decoration-symbol">
              {page === "adminLogin"
                ? "♜"
                : page === "studentLogin"
                  ? "✦"
                  : "✧"}
            </div>

            <h2>
              {page === "adminLogin"
                ? "Your platform. Your impact."
                : page === "studentLogin"
                  ? "Make learning a habit."
                  : "Start something brilliant."}
            </h2>

            <p>
              {page === "adminLogin"
                ? "Keep your learning community organized and growing."
                : page === "studentLogin"
                  ? "Discover new skills and make progress one lesson at a time."
                  : "A world of new skills is just one step away."}
            </p>

            <div className="decoration-pill">
              ✦ &nbsp; Learn today. Grow tomorrow.
            </div>
          </div>

          <div className="auth-card">
            <div className="auth-icon">
              {page === "adminLogin"
                ? "🛡️"
                : page === "studentLogin"
                  ? "🎓"
                  : "✨"}
            </div>

            <p className="eyebrow">
              {page === "adminLogin"
                ? "LEARNOVA ADMIN PORTAL"
                : page === "studentLogin"
                  ? "WELCOME BACK, LEARNER"
                  : "JOIN THE COMMUNITY"}
            </p>

            <h1>
              {page === "adminLogin"
                ? "Admin Login"
                : page === "studentLogin"
                  ? "Student Login"
                  : "Create your account"}
            </h1>

            <p className="auth-description">
              {page === "adminLogin"
                ? "Sign in to manage courses and lessons."
                : page === "studentLogin"
                  ? "Sign in and continue your learning journey."
                  : "Create a student account to begin learning."}
            </p>

            <form onSubmit={handleAuth}>
              {page === "signup" && (
                <label>
                  Full name
                  <input
                    type="text"
                    name="name"
                    placeholder="Enter your full name"
                    value={form.name}
                    onChange={handleFormChange}
                    autoComplete="name"
                    required
                  />
                </label>
              )}

              <label>
                Email address
                <input
                  type="email"
                  name="email"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={handleFormChange}
                  autoComplete="email"
                  required
                />
              </label>

              <label>
                Password
                <input
                  type="password"
                  name="password"
                  placeholder="Enter your password"
                  value={form.password}
                  onChange={handleFormChange}
                  autoComplete={
                    page === "signup" ? "new-password" : "current-password"
                  }
                  minLength={8}
                  required
                />
              </label>

              {message && (
                <p className="auth-message" role="alert">
                  {message}
                </p>
              )}

              <button
                className="primary-button auth-submit"
                type="submit"
                disabled={loading}
              >
                {loading
                  ? "Please wait..."
                  : page === "signup"
                    ? "Create Student Account"
                    : page === "adminLogin"
                      ? "Login as Admin →"
                      : "Login as Student →"}
              </button>
            </form>

            {page === "signup" ? (
              <p className="auth-switch">
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => goTo("studentLogin")}
                >
                  Student Login
                </button>
              </p>
            ) : page === "studentLogin" ? (
              <p className="auth-switch">
                New to Learnova?{" "}
                <button type="button" onClick={() => goTo("signup")}>
                  Create account
                </button>
              </p>
            ) : (
              <p className="auth-switch">
                Are you a student?{" "}
                <button
                  type="button"
                  onClick={() => goTo("studentLogin")}
                >
                  Student Login
                </button>
              </p>
            )}

            {page !== "signup" && (
              <p className="role-switch">
                Looking for a different portal?{" "}
                <button
                  type="button"
                  onClick={() =>
                    goTo(
                      page === "adminLogin"
                        ? "studentLogin"
                        : "adminLogin"
                    )
                  }
                >
                  {page === "adminLogin" ? "Student Login" : "Admin Login"}
                </button>
              </p>
            )}

            <button
              className="back-home"
              type="button"
              onClick={() => goTo("home")}
            >
              ← Back to Home
            </button>
          </div>
        </section>
      )}

      {page === "dashboard" && user?.role === "student" && (
        <main className="dashboard-section">
          <p className="eyebrow">YOUR LEARNING SPACE</p>
          <h1>Welcome back, {user.name}!</h1>
          <p className="dashboard-subtitle">
            Keep your momentum going. Every lesson is progress.
          </p>

          <div className="stats-grid">
            <div className="stat-card">
              <span>📚</span>
              <p>Enrolled courses</p>
              <strong>{myCourses.length}</strong>
            </div>

            <div className="stat-card">
              <span>✓</span>
              <p>Completed courses</p>
              <strong>
                {
                  myCourses.filter(
                    (course) =>
                      course.progress === 100 && course.total_lessons > 0
                  ).length
                }
              </strong>
            </div>

            <div className="stat-card">
              <span>◴</span>
              <p>Learning progress</p>
              <strong>
                {myCourses.length
                  ? Math.round(
                      myCourses.reduce(
                        (sum, course) => sum + (course.progress || 0),
                        0
                      ) / myCourses.length
                    )
                  : 0}
                %
              </strong>
            </div>
          </div>

          <div className="dashboard-heading">
            <div>
              <p className="eyebrow">YOUR CLASSROOM</p>
              <h2>My Learning</h2>
            </div>

            <button
              className="secondary-button"
              onClick={() => goTo("home")}
              type="button"
            >
              Explore courses
            </button>
          </div>

          {myCourses.length === 0 ? (
            <div className="empty-state panel">
              <h3>Your learning journey starts here</h3>
              <p>
                You haven't enrolled in a course yet. Browse the catalog
                and choose your first course.
              </p>
              <button
                className="primary-button"
                onClick={() => goTo("home")}
                type="button"
              >
                Browse courses →
              </button>
            </div>
          ) : (
            <div className="enrolled-grid">
              {myCourses.map((course) => (
                <article className="enrolled-card" key={course.id}>
                  <span className="course-category">
                    {course.category || "Learning"}
                  </span>
                  <h3>{course.title}</h3>
                  <p>{course.description}</p>

                  <div className="progress-label">
                    <span>
                      {course.completed_lessons || 0} of{" "}
                      {course.total_lessons || 0} lessons
                    </span>
                    <strong>{course.progress || 0}%</strong>
                  </div>

                  <div className="progress-track">
                    <span
                      style={{ width: `${course.progress || 0}%` }}
                    ></span>
                  </div>

                  <button
                    className="course-button"
                    onClick={() => openLessons(course)}
                    type="button"
                  >
                    Open course →
                  </button>
                </article>
              ))}
            </div>
          )}
        </main>
      )}

      {page === "lessons" && user && selectedCourse && (
        <main className="dashboard-section">
          <button
            className="back-home inline-back"
            onClick={() =>
              goTo(user.role === "admin" ? "admin" : "dashboard")
            }
            type="button"
          >
            ← Back to{" "}
            {user.role === "admin" ? "Admin Dashboard" : "My Learning"}
          </button>

          <p className="eyebrow">COURSE CONTENT</p>
          <h1>{selectedCourse.title}</h1>
          <p className="dashboard-subtitle">
            {selectedCourse.description}
          </p>

          {user.role === "student" && (
            <div className="lesson-progress-summary">
              <strong>{progress.progress || 0}% complete</strong>
              <div className="progress-track">
                <span
                  style={{ width: `${progress.progress || 0}%` }}
                ></span>
              </div>
            </div>
          )}

          {lessons.length === 0 ? (
            <div className="empty-state panel">
              <h3>No lessons yet</h3>
              <p>
                The course administrator has not added lessons yet.
              </p>
            </div>
          ) : (
            <div className="lesson-list">
              {lessons.map((lesson, index) => (
                <article className="lesson-card" key={lesson.id}>
                  <div
                    className={`lesson-number ${
                      lesson.completed ? "done" : ""
                    }`}
                  >
                    {lesson.completed
                      ? "✓"
                      : String(index + 1).padStart(2, "0")}
                  </div>

                  <div className="lesson-body">
                    <h3>{lesson.title}</h3>
                    <p>{lesson.content}</p>

                    {lesson.video_url && (
                      <a
                        href={lesson.video_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open lesson video ↗
                      </a>
                    )}

                    {user.role === "admin" && editingLessonId === lesson.id && (
                      <form
                        className="lesson-edit-form"
                        onSubmit={(event) => saveLessonEdit(event, lesson)}
                      >
                        <label>
                          Lesson title
                          <input
                            type="text"
                            value={editLessonForm.title}
                            onChange={(event) =>
                              setEditLessonForm({
                                ...editLessonForm,
                                title: event.target.value,
                              })
                            }
                            required
                          />
                        </label>

                        <label>
                          Lesson content
                          <textarea
                            rows={3}
                            value={editLessonForm.content}
                            onChange={(event) =>
                              setEditLessonForm({
                                ...editLessonForm,
                                content: event.target.value,
                              })
                            }
                            required
                          />
                        </label>

                        <label>
                          Video URL
                          <input
                            type="url"
                            placeholder="https://www.youtube.com/watch?v=..."
                            value={editLessonForm.video_url}
                            onChange={(event) =>
                              setEditLessonForm({
                                ...editLessonForm,
                                video_url: event.target.value,
                              })
                            }
                          />
                        </label>

                        <label>
                          Lesson order
                          <input
                            type="number"
                            min="1"
                            value={editLessonForm.order}
                            onChange={(event) =>
                              setEditLessonForm({
                                ...editLessonForm,
                                order: event.target.value,
                              })
                            }
                          />
                        </label>

                        <div className="lesson-edit-actions">
                          <button className="primary-button" type="submit">
                            Save changes
                          </button>
                          <button
                            className="secondary-button"
                            type="button"
                            onClick={cancelEditLesson}
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    )}

                    {user.role === "admin" && editingLessonId !== lesson.id && (
                      <button
                        className="small-primary"
                        type="button"
                        onClick={() => startEditLesson(lesson)}
                      >
                        Edit lesson
                      </button>
                    )}
                  </div>

                  {user.role === "student" && (
                    <button
                      className={
                        lesson.completed
                          ? "completed-button"
                          : "small-primary"
                      }
                      disabled={lesson.completed}
                      onClick={() => completeLesson(lesson)}
                      type="button"
                    >
                      {lesson.completed
                        ? "Completed ✓"
                        : "Mark complete"}
                    </button>
                  )}
                </article>
              ))}
            </div>
          )}
        </main>
      )}

      {page === "admin" && user?.role === "admin" && (
        <main className="dashboard-section admin-section">
          <p className="eyebrow">LEARNOVA CONTROL CENTER</p>
          <h1>Admin Dashboard</h1>
          <p className="dashboard-subtitle">
            Welcome, {user.name}. Manage learning content from one place.
          </p>

          <div className="stats-grid">
            <div className="stat-card">
              <span>📚</span>
              <p>Total courses</p>
              <strong>{courses.length}</strong>
            </div>

            <div className="stat-card">
              <span>▤</span>
              <p>Total lessons</p>
              <strong>
                {courses.reduce(
                  (sum, course) => sum + (course.lesson_count || 0),
                  0
                )}
              </strong>
            </div>

            <div className="stat-card">
              <span>🛡️</span>
              <p>Portal</p>
              <strong>Admin</strong>
            </div>
          </div>

          <div className="admin-grid">
            <section className="form-panel">
              <p className="eyebrow">CREATE CONTENT</p>
              <h2>Add a course</h2>

              <form onSubmit={addCourse}>
                <label>
                  Course title
                  <input
                    value={courseForm.title}
                    onChange={(e) =>
                      setCourseForm({
                        ...courseForm,
                        title: e.target.value,
                      })
                    }
                    placeholder="e.g. Python Programming"
                    required
                  />
                </label>

                <label>
                  Description
                  <textarea
                    value={courseForm.description}
                    onChange={(e) =>
                      setCourseForm({
                        ...courseForm,
                        description: e.target.value,
                      })
                    }
                    rows="3"
                    placeholder="What will students learn?"
                  />
                </label>

                <div className="form-two-col">
                  <label>
                    Category
                    <input
                      value={courseForm.category}
                      onChange={(e) =>
                        setCourseForm({
                          ...courseForm,
                          category: e.target.value,
                        })
                      }
                    />
                  </label>

                  <label>
                    Duration
                    <input
                      value={courseForm.duration}
                      onChange={(e) =>
                        setCourseForm({
                          ...courseForm,
                          duration: e.target.value,
                        })
                      }
                      placeholder="e.g. 4 weeks"
                    />
                  </label>
                </div>

                <label>
                  Instructor
                  <input
                    value={courseForm.instructor}
                    onChange={(e) =>
                      setCourseForm({
                        ...courseForm,
                        instructor: e.target.value,
                      })
                    }
                    placeholder="Instructor name"
                  />
                </label>

                <label>
                  Image URL (optional)
                  <input
                    type="url"
                    value={courseForm.image_url}
                    onChange={(e) =>
                      setCourseForm({
                        ...courseForm,
                        image_url: e.target.value,
                      })
                    }
                    placeholder="https://..."
                  />
                </label>

                <button
                  className="primary-button auth-submit"
                  type="submit"
                >
                  Add course +
                </button>
              </form>
            </section>

            <section className="form-panel">
              <p className="eyebrow">LESSON MANAGEMENT</p>
              <h2>Add a lesson</h2>

              <label>
                Select course
                <select
                  value={selectedCourse?.id || ""}
                  onChange={(e) => {
                    const selected = courses.find(
                      (course) => course.id === Number(e.target.value)
                    );
                    setSelectedCourse(selected || null);
                    setMessage("");
                  }}
                  required
                >
                  <option value="">Choose a course</option>
                  {courses.map((course) => (
                    <option value={course.id} key={course.id}>
                      {course.title}
                    </option>
                  ))}
                </select>
              </label>

              <form onSubmit={addLesson}>
                <label>
                  Lesson title
                  <input
                    value={lessonForm.title}
                    onChange={(e) =>
                      setLessonForm({
                        ...lessonForm,
                        title: e.target.value,
                      })
                    }
                    placeholder="e.g. Introduction to Python"
                    required
                  />
                </label>

                <label>
                  Lesson content
                  <textarea
                    value={lessonForm.content}
                    onChange={(e) =>
                      setLessonForm({
                        ...lessonForm,
                        content: e.target.value,
                      })
                    }
                    rows="4"
                    placeholder="Write the lesson content..."
                    required
                  />
                </label>

                <label>
                  Video URL (optional)
                  <input
                    type="url"
                    value={lessonForm.video_url}
                    onChange={(e) =>
                      setLessonForm({
                        ...lessonForm,
                        video_url: e.target.value,
                      })
                    }
                    placeholder="https://..."
                  />
                </label>

                <label>
                  Lesson order (optional)
                  <input
                    type="number"
                    min="1"
                    value={lessonForm.order}
                    onChange={(e) =>
                      setLessonForm({
                        ...lessonForm,
                        order: e.target.value,
                      })
                    }
                    placeholder="Automatically assigned"
                  />
                </label>

                <button
                  className="primary-button auth-submit"
                  type="submit"
                  disabled={!selectedCourse}
                >
                  Add lesson +
                </button>
              </form>
            </section>
          </div>

          <section className="course-management">
            <div className="dashboard-heading">
              <div>
                <p className="eyebrow">YOUR CATALOG</p>
                <h2>Manage course lessons</h2>
              </div>
            </div>

            <div className="management-list">
              {courses.map((course) => (
                <article className="management-row" key={course.id}>
                  <div>
                    <h3>{course.title}</h3>
                    <p>
                      {course.lesson_count || 0} lessons ·{" "}
                      {course.category || "General"}
                    </p>
                  </div>

                  <button
                    className="secondary-button"
                    onClick={() => openLessons(course)}
                    type="button"
                  >
                    View lessons
                  </button>

                  <button
                    className="small-primary"
                    onClick={() => {
                      setSelectedCourse(course);
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    type="button"
                  >
                    Select course
                  </button>
                </article>
              ))}
            </div>
          </section>
        </main>
      )}

      <footer className="footer">
        <div>
          <h2>
            Learnova<span>.</span>
          </h2>
          <p>Learn today. Grow tomorrow.</p>
        </div>
        <p>© 2026 Learnova. All rights reserved.</p>
      </footer>
    </div>
  );
}
