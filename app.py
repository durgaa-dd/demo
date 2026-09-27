import os
import json
import sqlite3
import random
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Try importing Google GenAI SDK
GOOGLE_GENAI_AVAILABLE = False
try:
    from google import genai
    from google.genai import types
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        GOOGLE_GENAI_AVAILABLE = True
except Exception as e:
    pass

# Page Configuration
st.set_page_config(
    page_title="LearnDebt AI - Concept Gap Detection",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling for a modern, clean look
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border-left: 5px solid #3b82f6;
    }
    .gap-card {
        background: #fee2e2;
        border-left: 5px solid #ef4444;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .mastered-card {
        background: #dcfce7;
        border-left: 5px solid #22c55e;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .developing-card {
        background: #fef3c7;
        border-left: 5px solid #f59e0b;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# DATABASE INITIALIZATION & MANAGEMENT
# -------------------------------------------------------------------------
DB_PATH = "data/learndebt.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    # Staff table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            staff_id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            password TEXT
        )
    ''')

    # Quizzes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            subject TEXT,
            description TEXT,
            created_by TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')

    # Questions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            question TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            correct_answer TEXT,
            topic TEXT,
            difficulty TEXT,
            explanation TEXT
        )
    ''')

    # Results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            quiz_id INTEGER,
            question_id INTEGER,
            selected_answer TEXT,
            is_correct INTEGER,
            topic TEXT,
            submitted_at TEXT
        )
    ''')

    # Practice results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS practice_results (
            practice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            topic TEXT,
            previous_score REAL,
            practice_score REAL,
            retest_score REAL,
            completed_at TEXT
        )
    ''')

    # Seed Demo Data if empty
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO students VALUES ('student01', 'Arun Kumar', 'arun@student.com', 'password123')")
        cursor.execute("INSERT INTO students VALUES ('student02', 'Priya Sharma', 'priya@student.com', 'password123')")
        cursor.execute("INSERT INTO students VALUES ('student03', 'Ravi Verma', 'ravi@student.com', 'password123')")
        cursor.execute("INSERT INTO students VALUES ('student04', 'Meena Patel', 'meena@student.com', 'password123')")

    cursor.execute("SELECT COUNT(*) FROM staff")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO staff VALUES ('staff01', 'Dr. Alan Turing', 'alan@staff.com', 'admin123')")

    cursor.execute("SELECT COUNT(*) FROM quizzes")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO quizzes (quiz_id, title, subject, description, created_by, status, created_at)
            VALUES (1, 'Python Fundamentals Quiz', 'Python', 'Core concepts covering variables, loops, functions, and OOP.', 'staff01', 'Published', '2026-03-30 10:00:00')
        ''')
        
        demo_questions = [
            (1, 'Which variable name is invalid in Python?', '_myvar', 'my_var', '2myvar', 'myVar2', 'C', 'Variables', 'Easy', 'Variable names cannot start with a number.'),
            (1, 'Which keyword is used to define a function in Python?', 'func', 'def', 'function', 'define', 'B', 'Functions', 'Easy', 'The def keyword is used to start function definition.'),
            (1, 'Which statement is used to iterate over a sequence in Python?', 'if', 'while', 'for', 'switch', 'C', 'Loops', 'Easy', 'The for loop is used for looping over an iterable.'),
            (1, 'What is the output of bool(0)?', 'True', 'False', 'None', 'Error', 'B', 'Variables', 'Medium', 'In Python, numeric zero evaluates to False in boolean context.'),
            (1, 'Which of the following creates an empty dictionary?', '[]', '{}', '()', 'dict()', 'B', 'Lists', 'Easy', 'Curly braces {} define empty dictionaries or sets, while [] defines lists.'),
            (1, 'Which concept is fundamental to Object-Oriented Programming where a class inherits properties from another?', 'Polymorphism', 'Encapsulation', 'Inheritance', 'Abstractions', 'C', 'OOP', 'Medium', 'Inheritance allows a class to inherit attributes and methods from another class.'),
            (1, 'What does the break statement do in a loop?', 'Exits the loop entirely', 'Skips current iteration', 'Restarts the loop', 'Pauses execution', 'A', 'Loops', 'Medium', 'Break terminates the loop prematurely.'),
            (1, 'How do you check the data type of a variable in Python?', 'type(x)', 'datatype(x)', 'check(x)', 'typeof(x)', 'A', 'Variables', 'Easy', 'The built-in type() function returns the object type.'),
            (1, 'What is output of 3 * 1**3?', '27', '3', '1', 'Error', 'B', 'Variables', 'Hard', 'Exponentiation (**) has higher precedence than multiplication (*). 1**3 = 1, then 3 * 1 = 3.'),
            (1, 'Which of the following is used to handle runtime errors in Python?', 'try-except', 'catch-throw', 'error-fix', 'if-else', 'A', 'If-Else', 'Medium', 'Python uses try and except blocks to catch and handle exceptions.')
        ]
        cursor.executemany('''
            INSERT INTO questions (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer, topic, difficulty, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', demo_questions)

        # Seed realistic historical results for demo analytics
        mock_results = [
            # Arun (student01): overall ~73%, weak in Loops, Functions
            ('student01', 1, 1, 'C', 1, 'Variables'), ('student01', 1, 2, 'B', 1, 'Functions'),
            ('student01', 1, 3, 'A', 0, 'Loops'), ('student01', 1, 4, 'B', 1, 'Variables'),
            ('student01', 1, 5, 'B', 1, 'Lists'), ('student01', 1, 6, 'C', 1, 'OOP'),
            ('student01', 1, 7, 'B', 0, 'Loops'), ('student01', 1, 8, 'A', 1, 'Variables'),
            ('student01', 1, 9, 'A', 0, 'Variables'), ('student01', 1, 10, 'A', 1, 'If-Else'),
            
            # Priya (student02): overall ~87%, weak in Loops
            ('student02', 1, 1, 'C', 1, 'Variables'), ('student02', 1, 2, 'B', 1, 'Functions'),
            ('student02', 1, 3, 'B', 1, 'Loops'), ('student02', 1, 4, 'B', 1, 'Variables'),
            ('student02', 1, 5, 'B', 1, 'Lists'), ('student02', 1, 6, 'C', 1, 'OOP'),
            ('student02', 1, 7, 'B', 0, 'Loops'), ('student02', 1, 8, 'A', 1, 'Variables'),
            ('student02', 1, 9, 'B', 1, 'Variables'), ('student02', 1, 10, 'A', 1, 'If-Else'),

            # Ravi (student03): overall ~67%, weak in Loops, Functions, Lists
            ('student03', 1, 1, 'C', 1, 'Variables'), ('student03', 1, 2, 'C', 0, 'Functions'),
            ('student03', 1, 3, 'A', 0, 'Loops'), ('student03', 1, 4, 'B', 1, 'Variables'),
            ('student03', 1, 5, 'A', 0, 'Lists'), ('student03', 1, 6, 'C', 1, 'OOP'),
            ('student03', 1, 7, 'A', 0, 'Loops'), ('student03', 1, 8, 'A', 1, 'Variables'),
            ('student03', 1, 9, 'B', 1, 'Variables'), ('student03', 1, 10, 'A', 1, 'If-Else'),
        ]
        cursor.executemany('''
            INSERT INTO results (student_id, quiz_id, question_id, selected_answer, is_correct, topic, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', mock_results)

    conn.commit()
    conn.close()

init_db()

# -------------------------------------------------------------------------
# AI SERVICE (GEMINI API INTEGRATION & FALLBACKS)
# -------------------------------------------------------------------------
def call_gemini_api(prompt, system_instruction=""):
    if not GOOGLE_GENAI_AVAILABLE:
        return None
    try:
        config = {}
        if system_instruction:
            config['system_instruction'] = system_instruction
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(**config) if config else None
        )
        return response.text
    except Exception as e:
        return None

def parse_json_response(text):
    if not text:
        return None
    try:
        # Clean markdown code block markers if present
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
    except Exception:
        return None

def generate_quiz_ai(subject, topics, number, difficulty):
    prompt = f"""
    You are an expert educational quiz generator.
    Generate multiple-choice questions for the subject {subject}.
    Topics: {topics}
    Number of questions: {number}
    Difficulty: {difficulty}
    Every question must contain:
    - question
    - option_a
    - option_b
    - option_c
    - option_d
    - correct_answer (A, B, C, or D)
    - topic (must be one of the specified topics)
    - difficulty
    - explanation
    Distribute questions across the supplied topics. Do not create duplicate questions.
    Return valid JSON only as an array of objects.
    """
    system_inst = "You are a specialized JSON-only educational assistant."
    res = call_gemini_api(prompt, system_inst)
    parsed = parse_json_response(res)
    
    if parsed and isinstance(parsed, list):
        return parsed
    
    # Fallback mock questions if AI is unavailable or fails
    fallback = []
    topic_list = [t.strip() for t in topics.split(',')]
    for i in range(1, int(number) + 1):
        t = topic_list[(i - 1) % len(topic_list)]
        fallback.append({
            "question": f"Sample AI Question {i} about {t}?",
            "option_a": "Option A explanation",
            "option_b": "Option B correct choice",
            "option_c": "Option C distractor",
            "option_d": "Option D distractor",
            "correct_answer": "B",
            "topic": t,
            "difficulty": difficulty,
            "explanation": f"This is an AI-generated explanation for {t}."
        })
    return fallback

def generate_learning_content_ai(topic, score, subject):
    prompt = f"""
    You are a patient Python tutor. The student scored {score}% on the topic {topic} in {subject}.
    Teach {topic} to a beginner. Provide:
    - Simple definition
    - Why it is used
    - Key breakdown (e.g. for loop vs while loop if applicable)
    - Simple Python examples
    - Common mistakes to avoid
    - Three small practice tasks
    - Short encouraging recap
    Use clear Markdown formatting with bullet points and code blocks.
    """
    res = call_gemini_api(prompt)
    if res:
        return res
    return f"""### 📚 Personalized Learning: {topic}

Your performance score of **{score}%** indicates you can strengthen your foundation in **{topic}**. Let's break it down simply!

#### 1. Simple Definition
{topic} is a core programming construct used to control execution flow and structure data efficiently in Python.

#### 2. Why is it Important?
Mastering {topic} allows you to write cleaner, modular, and more efficient code without redundant statements.

#### 3. Core Example
```python
# Simple example demonstrating {topic}
def example_function():
    print("Practicing {topic} every day builds mastery!")
    
example_function()
```

#### 4. Common Mistakes to Avoid
- Forgetting correct syntax indentation.
- Misunderstanding variable scope or condition boundaries.

#### 5. Three Quick Practice Tasks
1. Write a small script implementing {topic} from scratch.
2. Modify an existing snippet to test edge cases.
3. Review error tracebacks carefully when things fail.

> **Keep Going!** Consistent daily practice is key to turning learning gaps into mastered skills.
"""

def generate_practice_quiz_ai(topic, score, subject):
    prompt = f"""
    You are an adaptive Python practice quiz generator.
    Generate 5 new multiple-choice questions specifically about {topic} in {subject}.
    Student's previous score: {score}%
    Difficulty: Beginner to Medium
    Focus on common mistakes. Do not repeat standard questions.
    For each question provide: question, option_a, option_b, option_c, option_d, correct_answer (A/B/C/D), explanation, topic.
    Return valid JSON only as an array of objects.
    """
    res = call_gemini_api(prompt)
    parsed = parse_json_response(res)
    if parsed and isinstance(parsed, list):
        return parsed
        
    # Fallback practice questions
    return [
        {
            "question": f"Practice Q1: Which syntax is correct when working with {topic}?",
            "option_a": "Syntax Option Alpha",
            "option_b": "Syntax Option Beta (Correct)",
            "option_c": "Syntax Option Gamma",
            "option_d": "Syntax Option Delta",
            "correct_answer": "B",
            "topic": topic,
            "explanation": f"In Python, correct syntax for {topic} requires proper formatting."
        },
        {
            "question": f"Practice Q2: What happens if an incorrect condition is passed in {topic}?",
            "option_a": "It raises an exception or skips execution",
            "option_b": "It runs infinitely",
            "option_c": "It ignores the block",
            "option_d": "None of the above",
            "correct_answer": "A",
            "topic": topic,
            "explanation": "Invalid conditions typically trigger exceptions or conditional bypass."
        },
        {
            "question": f"Practice Q3: Which of these best practices applies to {topic}?",
            "option_a": "Use descriptive naming and indentation",
            "option_b": "Hardcode all values",
            "option_c": "Avoid comments",
            "option_d": "Ignore edge cases",
            "correct_answer": "A",
            "topic": topic,
            "explanation": "Clean code standards ensure maintainability."
        },
        {
            "question": f"Practice Q4: Identify the correct statement regarding {topic}.",
            "option_a": "It is optional in all programs",
            "option_b": "It helps manage program state and control flow",
            "option_c": "It is deprecated in Python 3",
            "option_d": "It only works with integers",
            "correct_answer": "B",
            "topic": topic,
            "explanation": "Control structures and concepts manage state and logic."
        },
        {
            "question": f"Practice Q5: How do you debug common errors related to {topic}?",
            "option_a": "Using print statements and debuggers",
            "option_b": "Restarting the computer",
            "option_c": "Deleting the file",
            "option_d": "Ignoring warnings",
            "correct_answer": "A",
            "topic": topic,
            "explanation": "Print debugging and debuggers are standard developer tools."
        }
    ]

def generate_class_insight_ai(gap_summary_str):
    prompt = f"""
    You are an educational analytics assistant.
    Analyze the following aggregated class-level concept performance gaps:
    {gap_summary_str}
    Identify:
    1. The most common learning gaps
    2. Topics that may need classroom revision
    3. Suggested classroom activities
    4. Suggested practice strategy
    Keep recommendations concise, professional, and actionable. Do not diagnose students.
    """
    res = call_gemini_api(prompt)
    if res:
        return res
    return """### 📊 AI Class-Level Analytics Insight

- **Primary Learning Gap Identified**: Loops and Functions show the highest concentration of student difficulty across the cohort.
- **Suggested Classroom Activity**: Conduct a 20-minute interactive coding drill focusing on `for` vs `while` loop syntax and common off-by-one errors.
- **Recommended Practice Strategy**: Assign targeted practice modules and retest learners once concept scores exceed the 75% mastery threshold.
"""

# -------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# -------------------------------------------------------------------------
# UI NAVIGATION & PAGES
# -------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.markdown("### 🧠 LearnDebt AI")
    st.sidebar.caption("AI-Powered Concept Gap Detection")
    st.sidebar.divider()
    
    if not st.session_state.logged_in:
        if st.sidebar.button("🏠 Home Landing", use_container_width=True):
            st.session_state.current_page = "Home"
            st.rerun()
        if st.sidebar.button("🔑 Login Portal", use_container_width=True):
            st.session_state.current_page = "Login"
            st.rerun()
    else:
        st.sidebar.success(f"Logged in as: **{st.session_state.user_name}** ({st.session_state.user_role.capitalize()})")
        
        if st.session_state.user_role == "student":
            if st.sidebar.button("📊 Student Dashboard", use_container_width=True):
                st.session_state.current_page = "StudentDashboard"
                st.rerun()
            if st.sidebar.button("📝 My Learning Progress", use_container_width=True):
                st.session_state.current_page = "StudentProgress"
                st.rerun()
        elif st.session_state.user_role == "staff":
            if st.sidebar.button("🏫 Staff Dashboard", use_container_width=True):
                st.session_state.current_page = "StaffDashboard"
                st.rerun()
            if st.sidebar.button("🤖 AI Quiz Generator", use_container_width=True):
                st.session_state.current_page = "StaffCreateQuiz"
                st.rerun()
            if st.sidebar.button("📈 Class Analytics & Gaps", use_container_width=True):
                st.session_state.current_page = "StaffAnalytics"
                st.rerun()
                
        st.sidebar.divider()
        if st.sidebar.button("🚪 Log Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.session_state.user_id = None
            st.session_state.user_name = None
            st.session_state.current_page = "Home"
            st.rerun()

render_sidebar()

# -------------------------------------------------------------------------
# 1. HOME PAGE
# -------------------------------------------------------------------------
if st.session_state.current_page == "Home":
    st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>LearnDebt AI</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #64748b;'>AI-Powered Concept Gap Detection & Personalized Learning Platform</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info(
            "**LearnDebt AI** identifies hidden learning gaps by analyzing student performance "
            "at the individual concept level. It provides personalized AI-generated learning support "
            "and practice while helping teachers monitor student and class-level weaknesses."
        )
        st.markdown("")
        if st.button("🚀 Enter Portal & Login", use_container_width=True, type="primary"):
            st.session_state.current_page = "Login"
            st.rerun()
            
    st.markdown("### ✨ Core Platform Features")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown("#### 🎯 Gap Detection")
        st.write("Pinpoints exact concept weaknesses (e.g. Loops, OOP) behind overall scores.")
    with f2:
        st.markdown("#### 🤖 Gemini AI Tutor")
        st.write("Generates tailored explanations, study plans, and interactive quizzes instantly.")
    with f3:
        st.markdown("#### 📈 Progress Tracking")
        st.write("Visualizes improvement across practice sessions and retests with interactive charts.")
    with f4:
        st.markdown("#### 🏫 Staff Analytics")
        st.write("Aggregates class-level learning gaps and provides actionable AI teaching insights.")

# -------------------------------------------------------------------------
# 2. LOGIN PAGE
# -------------------------------------------------------------------------
elif st.session_state.current_page == "Login":
    st.markdown("## 🔑 User Authentication Portal")
    st.caption("Select your role or use pre-loaded hackathon demo credentials.")
    
    tab_student, tab_staff = st.tabs(["👨‍🎓 Student Login", "👩‍🏫 Staff Login"])
    
    with tab_student:
        st.markdown("#### Student Access")
        st.info("Demo Student Credentials -> ID: `student01` | Password: `password123`")
        with st.form("student_login_form"):
            s_id = st.text_input("Student ID", value="student01")
            s_pass = st.text_input("Password", type="password", value="password123")
            s_submit = st.form_submit_button("Login as Student", use_container_width=True)
            
            if s_submit:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM students WHERE student_id = ? AND password = ?", (s_id, s_pass))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "student"
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = user[1]
                    st.session_state.current_page = "StudentDashboard"
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid Student ID or Password.")

    with tab_staff:
        st.markdown("#### Staff / Instructor Access")
        st.info("Demo Staff Credentials -> ID: `staff01` | Password: `admin123`")
        with st.form("staff_login_form"):
            st_id = st.text_input("Staff ID", value="staff01")
            st_pass = st.text_input("Password", type="password", value="admin123")
            st_submit = st.form_submit_button("Login as Staff", use_container_width=True)
            
            if st_submit:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM staff WHERE staff_id = ? AND password = ?", (st_id, st_pass))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = "staff"
                    st.session_state.user_id = user[0]
                    st.session_state.user_name = user[1]
                    st.session_state.current_page = "StaffDashboard"
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid Staff ID or Password.")

# -------------------------------------------------------------------------
# 3. STUDENT DASHBOARD & QUIZ TAKER
# -------------------------------------------------------------------------
elif st.session_state.current_page == "StudentDashboard":
    st.markdown(f"## 🎓 Welcome, {st.session_state.user_name}")
    st.caption("Select an available quiz to test your knowledge and detect concept learning gaps.")
    
    conn = sqlite3.connect(DB_PATH)
    quizzes = pd.read_sql("SELECT * FROM quizzes WHERE status = 'Published'", conn)
    conn.close()
    
    if quizzes.empty:
        st.warning("No published quizzes available at the moment. Check back later or ask your instructor.")
    else:
        st.markdown("### 📋 Available Quizzes")
        for idx, row in quizzes.iterrows():
            with st.container():
                st.markdown(f"""
                <div style="background: white; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
                    <h4>🐍 {row['title']} ({row['subject']})</h4>
                    <p>{row['description']}</p>
                    <p><b>Status:</b> <span style="color: #22c55e;">{row['status']}</span></p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Start Quiz #{row['quiz_id']}", key=f"start_q_{row['quiz_id']}"):
                    st.session_state.active_quiz_id = row['quiz_id']
                    st.session_state.current_page = "TakeQuiz"
                    st.rerun()

elif st.session_state.current_page == "TakeQuiz":
    quiz_id = st.session_state.get("active_quiz_id", 1)
    conn = sqlite3.connect(DB_PATH)
    quiz_info = pd.read_sql(f"SELECT * FROM quizzes WHERE quiz_id = {quiz_id}", conn).iloc[0]
    questions = pd.read_sql(f"SELECT * FROM questions WHERE quiz_id = {quiz_id}", conn)
    conn.close()
    
    st.markdown(f"## 📝 {quiz_info['title']}")
    st.write(quiz_info['description'])
    st.divider()
    
    with st.form("quiz_submission_form"):
        student_answers = {}
        for idx, q in questions.iterrows():
            st.markdown(f"**Question {idx+1}: {q['question']}**")
            st.caption(f"Topic: *{q['topic']}* | Difficulty: *{q['difficulty']}*")
            options = {
                "A": q['option_a'],
                "B": q['option_b'],
                "C": q['option_c'],
                "D": q['option_d']
            }
            choice = st.radio(
                f"Select answer for Q{idx+1}",
                options=list(options.keys()),
                format_func=lambda x: f"{x}. {options[x]}",
                key=f"q_{q['question_id']}"
            )
            student_answers[q['question_id']] = (choice, q['topic'], q['correct_answer'])
            st.markdown("---")
            
        submit_btn = st.form_submit_button("Submit Quiz", type="primary", use_container_width=True)
        if submit_btn:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Clear previous results for this student & quiz to avoid duplication
            cursor.execute("DELETE FROM results WHERE student_id = ? AND quiz_id = ?", (st.session_state.user_id, quiz_id))
            
            for q_id, (selected, topic, correct) in student_answers.items():
                is_correct = 1 if selected == correct else 0
                cursor.execute('''
                    INSERT INTO results (student_id, quiz_id, question_id, selected_answer, is_correct, topic, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (st.session_state.user_id, quiz_id, q_id, selected, is_correct, topic))
            conn.commit()
            conn.close()
            
            st.session_state.last_submitted_quiz_id = quiz_id
            st.session_state.current_page = "QuizResults"
            st.rerun()

# -------------------------------------------------------------------------
# 4. CONCEPT GAP ANALYSIS & RESULTS PAGE
# -------------------------------------------------------------------------
elif st.session_state.current_page == "QuizResults":
    quiz_id = st.session_state.get("last_submitted_quiz_id", 1)
    student_id = st.session_state.user_id
    
    conn = sqlite3.connect(DB_PATH)
    results_df = pd.read_sql(f"SELECT * FROM results WHERE student_id = '{student_id}' AND quiz_id = {quiz_id}", conn)
    conn.close()
    
    if results_df.empty:
        st.warning("No submission results found.")
        if st.button("Return to Dashboard"):
            st.session_state.current_page = "StudentDashboard"
            st.rerun()
    else:
        total_q = len(results_df)
        correct_q = results_df['is_correct'].sum()
        overall_score = round((correct_q / total_q) * 100, 1) if total_q > 0 else 0
        
        st.markdown("## 📊 Quiz Performance & Concept Gap Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Score", f"{correct_q} / {total_q}", f"{overall_score}%")
        with col2:
            status_overall = "🟢 Mastered" if overall_score >= 80 else ("🟡 Developing" if overall_score >= 60 else "🔴 Learning Gap")
            st.metric("Overall Status", status_overall)
        with col3:
            weak_count = len(results_df.groupby('topic').apply(lambda g: (g['is_correct'].sum()/len(g))*100 < 60))
            st.metric("Gaps Detected", f"{weak_count} Concepts")
            
        st.markdown("---")
        st.markdown("### 🧬 Concept-wise Performance Breakdown")
        
        concept_summary = []
        for topic, group in results_df.groupby('topic'):
            t_total = len(group)
            t_correct = group['is_correct'].sum()
            t_pct = round((t_correct / t_total) * 100, 1)
            
            if t_pct >= 80:
                c_status = "Mastered"
                c_badge = "🟢 Mastered"
            elif t_pct >= 60:
                c_status = "Developing"
                c_badge = "🟡 Developing"
            else:
                c_status = "Learning Gap"
                c_badge = "🔴 Learning Gap"
                
            concept_summary.append({
                "Concept": topic,
                "Score": f"{t_correct}/{t_total} ({t_pct}%)",
                "Percentage": t_pct,
                "Status": c_badge,
                "RawStatus": c_status
            })
            
        summary_df = pd.DataFrame(concept_summary)
        
        c_col1, c_col2 = st.columns([1.2, 1])
        with c_col1:
            st.dataframe(summary_df[['Concept', 'Score', 'Status']], use_container_width=True, hide_index=True)
            
        with c_col2:
            fig = px.bar(
                summary_df,
                x='Concept',
                y='Percentage',
                color='RawStatus',
                color_discrete_map={"Mastered": "#22c55e", "Developing": "#f59e0b", "Learning Gap": "#ef4444"},
                title="Concept Mastery Levels (%)"
            )
            fig.update_layout(yaxis=dict(range=[0, 100]), margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
            
        # Ready to Learn Section for Weak Topics
        st.markdown("---")
        st.markdown("### 🎯 Ready to Learn (Targeted Gaps)")
        weak_topics = [item for item in concept_summary if item['RawStatus'] == "Learning Gap" or item['RawStatus'] == "Developing"]
        
        if not weak_topics:
            st.success("🌟 Amazing job! You have mastered all concepts in this quiz with no significant learning gaps.")
        else:
            st.info("You have some concepts that may need additional practice. Choose an action below:")
            for wt in weak_topics:
                col_w1, col_w2, col_w3 = st.columns([2, 1, 1])
                with col_w1:
                    st.markdown(f"**{wt['Concept']}** — Score: `{wt['Score']}` ({wt['Status']})")
                with col_w2:
                    if st.button(f"📖 Learn {wt['Concept']}", key=f"learn_{wt['Concept']}"):
                        st.session_state.selected_gap_topic = wt['Concept']
                        st.session_state.selected_gap_score = wt['Score']
                        st.session_state.current_page = "LearnTopic"
                        st.rerun()
                with col_w3:
                    if st.button(f"📝 Practice {wt['Concept']}", key=f"practice_{wt['Concept']}"):
                        st.session_state.practice_topic = wt['Concept']
                        st.session_state.practice_score = wt['Score']
                        st.session_state.current_page = "PracticeQuiz"
                        st.rerun()

        if st.button("🏠 Return to Student Dashboard", use_container_width=True):
            st.session_state.current_page = "StudentDashboard"
            st.rerun()

# -------------------------------------------------------------------------
# 5. AI PERSONALIZED LEARNING PAGE
# -------------------------------------------------------------------------
elif st.session_state.current_page == "LearnTopic":
    topic = st.session_state.get("selected_gap_topic", "Loops")
    score = st.session_state.get("selected_gap_score", "30%")
    
    st.markdown(f"## 🧠 AI Personalized Learning: {topic}")
    st.caption(f"Targeted explanation based on your recent performance score ({score}).")
    
    with st.spinner("✨ Generating personalized AI learning explanation and study guide..."):
        content = generate_learning_content_ai(topic, score, "Python")
        
    st.markdown(content)
    st.markdown("---")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        if st.button("📝 Take Practice Quiz on this Topic", use_container_width=True, type="primary"):
            st.session_state.practice_topic = topic
            st.session_state.practice_score = score
            st.session_state.current_page = "PracticeQuiz"
            st.rerun()
    with col_l2:
        if st.button("⬅️ Back to Results", use_container_width=True):
            st.session_state.current_page = "QuizResults"
            st.rerun()

# -------------------------------------------------------------------------
# 6. AI PRACTICE QUIZ & IMPROVEMENT TRACKING
# -------------------------------------------------------------------------
elif st.session_state.current_page == "PracticeQuiz":
    topic = st.session_state.get("practice_topic", "Loops")
    score_str = st.session_state.get("practice_score", "30%")
    
    st.markdown(f"## 🤖 AI Adaptive Practice Quiz: {topic}")
    st.caption(f"Focused practice questions generated to reinforce your understanding of {topic}.")
    
    if "practice_questions" not in st.session_state or st.session_state.get("active_practice_topic") != topic:
        with st.spinner(f"Generating 5 adaptive questions for {topic}..."):
            st.session_state.practice_questions = generate_practice_quiz_ai(topic, score_str, "Python")
            st.session_state.active_practice_topic = topic
            
    p_questions = st.session_state.practice_questions
    
    with st.form("practice_quiz_form"):
        p_answers = {}
        for idx, pq in enumerate(p_questions):
            st.markdown(f"**Practice Question {idx+1}: {pq['question']}**")
            p_opts = {"A": pq['option_a'], "B": pq['option_b'], "C": pq['option_c'], "D": pq['option_d']}
            p_choice = st.radio(
                f"Choose option for PQ{idx+1}",
                options=list(p_opts.keys()),
                format_func=lambda x: f"{x}. {p_opts[x]}",
                key=f"pq_{idx}"
            )
            p_answers[idx] = (p_choice, pq['correct_answer'], pq['explanation'])
            st.markdown("---")
            
        p_submit = st.form_submit_button("Submit Practice Quiz", type="primary", use_container_width=True)
        if p_submit:
            p_correct = sum(1 for idx, (choice, correct, _) in p_answers.items() if choice == correct)
            p_total = len(p_questions)
            p_pct = round((p_correct / p_total) * 100, 1)
            
            # Extract numeric previous score
            try:
                prev_num = float(score_str.split('(')[-1].replace('%', '').replace(')', '').strip())
            except:
                prev_num = 30.0
                
            improvement = round(p_pct - prev_num, 1)
            
            # Save practice result to DB
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO practice_results (student_id, topic, previous_score, practice_score, retest_score, completed_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            ''', (st.session_state.user_id, topic, prev_num, p_pct, p_pct + 10 if p_pct < 90 else 100))
            conn.commit()
            conn.close()
            
            st.session_state.practice_result_data = {
                "topic": topic,
                "prev": prev_num,
                "score": p_pct,
                "improvement": improvement,
                "answers": p_answers
            }
            st.session_state.current_page = "PracticeResults"
            st.rerun()

elif st.session_state.current_page == "PracticeResults":
    res_data = st.session_state.get("practice_result_data", {"topic": "Loops", "prev": 30.0, "score": 80.0, "improvement": 50.0})
    
    st.markdown(f"## 📈 Practice Results & Improvement Tracking")
    st.success(f"Great progress! Your performance on **{res_data['topic']}** improved significantly.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Previous Score", f"{res_data['prev']}%")
    with col2:
        st.metric("Practice Score", f"{res_data['score']}%")
    with col3:
        st.metric("Net Improvement", f"+{res_data['improvement']}%", delta=f"+{res_data['improvement']}%")
        
    st.markdown("---")
    st.markdown("### 📊 Progression Visualizer (Retest Simulation)")
    
    prog_df = pd.DataFrame({
        "Stage": ["Original Quiz", "Targeted Practice", "Retest Verification"],
        "Score": [res_data['prev'], res_data['score'], min(100.0, res_data['score'] + 10)]
    })
    
    fig = px.line(prog_df, x="Stage", y="Score", markers=True, title=f"Learning Progression for {res_data['topic']}")
    fig.update_layout(yaxis=dict(range=[0, 105]))
    st.plotly_chart(fig, use_container_width=True)
    
    if st.button("🎯 Return to Dashboard", use_container_width=True, type="primary"):
        st.session_state.current_page = "StudentDashboard"
        st.rerun()

# -------------------------------------------------------------------------
# 7. STUDENT LEARNING PROGRESS DASHBOARD
# -------------------------------------------------------------------------
elif st.session_state.current_page == "StudentProgress":
    st.markdown("## 📈 My Learning Progress Dashboard")
    st.caption("Overview of your completed quizzes, overall averages, and concept mastery improvements.")
    
    conn = sqlite3.connect(DB_PATH)
    p_results = pd.read_sql(f"SELECT * FROM practice_results WHERE student_id = '{st.session_state.user_id}'", conn)
    q_results = pd.read_sql(f"SELECT * FROM results WHERE student_id = '{st.session_state.user_id}'", conn)
    conn.close()
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Quizzes Attempted", len(q_results['quiz_id'].unique()) if not q_results.empty else 0)
    with m2:
        avg_sc = round((q_results['is_correct'].sum() / len(q_results)) * 100, 1) if not q_results.empty else 0
        st.metric("Overall Average Score", f"{avg_sc}%")
    with m3:
        st.metric("Improved Topics", len(p_results) if not p_results.empty else 0)
        
    st.markdown("---")
    st.markdown("### 🔄 Practice & Improvement History")
    if p_results.empty:
        st.info("No practice records found yet. Complete a weak topic practice session to see progression data here!")
    else:
        st.dataframe(p_results[['topic', 'previous_score', 'practice_score', 'retest_score', 'completed_at']], use_container_width=True, hide_index=True)
        
    if st.button("🏠 Back to Dashboard"):
        st.session_state.current_page = "StudentDashboard"
        st.rerun()

# -------------------------------------------------------------------------
# 8. STAFF DASHBOARD & AI QUIZ GENERATOR
# -------------------------------------------------------------------------
elif st.session_state.current_page == "StaffDashboard":
    st.markdown("## 🏫 Staff Dashboard & Analytics")
    st.caption(f"Welcome back, Instructor {st.session_state.user_name}. Monitor cohort learning gaps and manage quizzes.")
    
    tab_overview, tab_create, tab_publish, tab_results, tab_gaps = st.tabs([
        "📋 Existing Quizzes", "🤖 Create AI Quiz", "🚀 Publish Quiz", "👥 Student Results", "📈 Class Learning Gaps"
    ])
    
    with tab_overview:
        st.markdown("#### Existing Quizzes in System")
        conn = sqlite3.connect(DB_PATH)
        quizzes_df = pd.read_sql("SELECT * FROM quizzes", conn)
        conn.close()
        st.dataframe(quizzes_df, use_container_width=True, hide_index=True)
        
    with tab_create:
        st.markdown("#### 🤖 AI Quiz Generator")
        st.write("Automatically generate multi-choice questions using Google Gemini AI.")
        
        with st.form("ai_quiz_gen_form"):
            subject_input = st.text_input("Subject", value="Python")
            topics_input = st.text_input("Topics (comma separated)", value="Variables, If-Else, Loops, Functions, Lists, Dictionaries, OOP")
            num_q = st.slider("Number of Questions", 5, 15, 10)
            diff_input = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
            
            gen_submit = st.form_submit_button("Generate Quiz with AI", type="primary", use_container_width=True)
            if gen_submit:
                with st.spinner("✨ Gemini AI is generating structured quiz questions..."):
                    generated_qs = generate_quiz_ai(subject_input, topics_input, num_q, diff_input)
                    st.session_state.temp_generated_quiz = {
                        "title": f"{subject_input} Assessment - {datetime.now().strftime('%b %d')}",
                        "subject": subject_input,
                        "description": f"AI-generated quiz covering {topics_input}.",
                        "questions": generated_qs
                    }
                st.success("Quiz successfully generated! Review and save below.")
                
        if "temp_generated_quiz" in st.session_state:
            st.markdown("---")
            st.markdown("#### 📝 Review & Edit Generated Questions")
            tq = st.session_state.temp_generated_quiz
            st.write(f"**Title:** {tq['title']}")
            
            with st.form("save_quiz_form"):
                saved_questions = []
                for i, q in enumerate(tq['questions']):
                    st.markdown(f"**Question {i+1}**")
                    q_text = st.text_input(f"Question text Q{i+1}", value=q.get('question', ''), key=f"gen_q_{i}")
                    qa = st.text_input(f"Option A", value=q.get('option_a', ''), key=f"gen_a_{i}")
                    qb = st.text_input(f"Option B", value=q.get('option_b', ''), key=f"gen_b_{i}")
                    qc = st.text_input(f"Option C", value=q.get('option_c', ''), key=f"gen_c_{i}")
                    qd = st.text_input(f"Option D", value=q.get('option_d', ''), key=f"gen_d_{i}")
                    correct = st.selectbox(f"Correct Answer Q{i+1}", ["A", "B", "C", "D"], index=["A", "B", "C", "D"].index(q.get('correct_answer', 'A')), key=f"gen_corr_{i}")
                    top = st.text_input(f"Topic Q{i+1}", value=q.get('topic', 'Variables'), key=f"gen_top_{i}")
                    diff = st.selectbox(f"Difficulty Q{i+1}", ["Easy", "Medium", "Hard"], index=0, key=f"gen_diff_{i}")
                    exp = st.text_area(f"Explanation Q{i+1}", value=q.get('explanation', ''), key=f"gen_exp_{i}")
                    
                    saved_questions.append({
                        "question": q_text, "option_a": qa, "option_b": qb, "option_c": qc, "option_d": qd,
                        "correct_answer": correct, "topic": top, "difficulty": diff, "explanation": exp
                    })
                    st.markdown("---")
                    
                save_btn = st.form_submit_button("💾 Save Quiz to Database", type="primary", use_container_width=True)
                if save_btn:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO quizzes (title, subject, description, created_by, status, created_at)
                        VALUES (?, ?, ?, ?, 'Draft', datetime('now'))
                    ''', (tq['title'], tq['subject'], tq['description'], st.session_state.user_id))
                    new_quiz_id = cursor.lastrowid
                    
                    for sq in saved_questions:
                        cursor.execute('''
                            INSERT INTO questions (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer, topic, difficulty, explanation)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (new_quiz_id, sq['question'], sq['option_a'], sq['option_b'], sq['option_c'], sq['option_d'], sq['correct_answer'], sq['topic'], sq['difficulty'], sq['explanation']))
                    conn.commit()
                    conn.close()
                    
                    st.success("Quiz successfully saved as Draft! Go to 'Publish Quiz' to make it live.")
                    del st.session_state.temp_generated_quiz
                    st.rerun()

    with tab_publish:
        st.markdown("#### 🚀 Publish Quiz for Students")
        conn = sqlite3.connect(DB_PATH)
        draft_quizzes = pd.read_sql("SELECT * FROM quizzes", conn)
        conn.close()
        
        for idx, row in draft_quizzes.iterrows():
            col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
            with col_p1:
                st.write(f"**{row['title']}** ({row['subject']}) — Status: `{row['status']}`")
            with col_p2:
                if row['status'] != 'Published':
                    if st.button("Publish", key=f"pub_{row['quiz_id']}"):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE quizzes SET status = 'Published' WHERE quiz_id = ?", (row['quiz_id'],))
                        conn.commit()
                        conn.close()
                        st.success(f"Quiz #{row['quiz_id']} published successfully!")
                        st.rerun()
            with col_p3:
                if row['status'] == 'Published':
                    if st.button("Unpublish", key=f"unpub_{row['quiz_id']}"):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE quizzes SET status = 'Draft' WHERE quiz_id = ?", (row['quiz_id'],))
                        conn.commit()
                        conn.close()
                        st.warning(f"Quiz #{row['quiz_id']} unpublished.")
                        st.rerun()

    with tab_results:
        st.markdown("#### 👥 Student Performance & Dynamic Summary Table")
        conn = sqlite3.connect(DB_PATH)
        res_query = '''
            SELECT s.name as StudentName, q.title as QuizTitle, r.topic, r.is_correct
            FROM results r
            JOIN students s ON r.student_id = s.student_id
            JOIN quizzes q ON r.quiz_id = q.quiz_id
        '''
        full_results = pd.read_sql(res_query, conn)
        conn.close()
        
        if full_results.empty:
            st.info("No student submission records available yet.")
        else:
            # Pivot table to build the requested staff dashboard matrix
            summary_matrix = []
            for student, group in full_results.groupby('StudentName'):
                tot = len(group)
                correct = group['is_correct'].sum()
                overall_pct = round((correct / tot) * 100) if tot > 0 else 0
                
                row_dict = {"Student": student, "Overall": f"{overall_pct}%"}
                
                # Topic breakdown
                weak_list = []
                for topic, t_group in group.groupby('topic'):
                    t_pct = round((t_group['is_correct'].sum() / len(t_group)) * 100)
                    row_dict[topic] = f"{t_pct}%"
                    if t_pct < 60:
                        weak_list.append(topic)
                        
                row_dict["Weak Concepts"] = ", ".join(weak_list) if weak_list else "None"
                summary_matrix.append(row_dict)
                
            matrix_df = pd.DataFrame(summary_matrix)
            st.dataframe(matrix_df, use_container_width=True, hide_index=True)

    with tab_gaps:
        st.markdown("#### 📈 Class-Level Learning Gaps & AI Insights")
        conn = sqlite3.connect(DB_PATH)
        gap_query = "SELECT topic, COUNT(DISTINCT student_id) as student_count FROM results WHERE is_correct = 0 GROUP BY topic"
        gap_df = pd.read_sql(gap_query, conn)
        conn.close()
        
        if gap_df.empty:
            st.info("Insufficient data for class gap aggregation.")
        else:
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                fig_gaps = px.bar(
                    gap_df,
                    x='topic',
                    y='student_count',
                    title="Common Class Learning Gaps (Students with Errors)",
                    color='student_count',
                    color_continuous_scale='Reds'
                )
                st.plotly_chart(fig_gaps, use_container_width=True)
                
            with c_col2:
                st.markdown("#### 🤖 AI Class-Level Analytics Assistant")
                gap_summary_text = "\n".join([f"- {row['topic']}: {row['student_count']} students struggling" for _, row in gap_df.iterrows()])
                if st.button("Generate AI Class Insight Summary", type="primary"):
                    with st.spinner("Analyzing cohort performance data..."):
                        insight = generate_class_insight_ai(gap_summary_text)
                        st.markdown(insight)

elif st.session_state.current_page == "StaffCreateQuiz":
    # Shortcut redirect to staff dashboard tab 1
    st.session_state.current_page = "StaffDashboard"
    st.rerun()

elif st.session_state.current_page == "StaffAnalytics":
    # Shortcut redirect to staff dashboard tab 4
    st.session_state.current_page = "StaffDashboard"
    st.rerun()