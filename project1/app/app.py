from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import plotly.express as px
import plotly.io as pio
import pandas as pd
import sys
from datetime import datetime

app = Flask(__name__)
app.secret_key = "a_very_secure_key_2025"

# Initialize MySQL connection
def get_db_connection():
    return mysql.connector.connect(host="localhost", user="root", password="", database="restaurant_reviews", unix_socket="/var/run/mysqld/mysqld.sock", ssl_disabled=True)

# Initialize and populate database tables
def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create application_users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS application_users (
                        userid VARCHAR(50) PRIMARY KEY,
                        password VARCHAR(50),
                        email VARCHAR(100))''')
    users = [
        ("admin", "password123", "admin@example.com"),
        ("user1", "pass123", "user1@example.com"),
        ("user2", "pass456", "user2@example.com"),
        ("user3", "pass789", "user3@example.com")
    ]
    cursor.executemany("INSERT IGNORE INTO application_users (userid, password, email) VALUES (%s, %s, %s)", users)

    # Create login_logs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS login_logs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        userid VARCHAR(50),
                        login_time DATETIME,
                        logout_time DATETIME,
                        duration TIME,
                        FOREIGN KEY (userid) REFERENCES application_users(userid))''')
    conn.commit()
    cursor.close()
    conn.close()

init_database()

# Routes
@app.route('/')
def login():
    print("Checking session in login route")
    if 'user' in session:
        print(f"User {session['user']} is logged in, redirecting to display_chart")
        return redirect(url_for('display_chart'))
    print("No user in session, showing login page")
    env_info = f"Running in: {sys.executable.split('/')[-3] if 'venv' in sys.executable else 'Global Python'}"
    return render_template('login.html', env_info=env_info)

@app.route('/login', methods=['POST'])
def login_post():
    print("Processing login request")
    conn = get_db_connection()
    cursor = conn.cursor()
    userid = request.form['userid']
    password = request.form['password']
    print(f"Attempting login for userid: {userid}, password: {password}")
    cursor.execute("SELECT * FROM application_users WHERE userid = %s AND password = %s", (userid, password))
    user = cursor.fetchone()
    if user:
        print(f"Login successful for {userid}")
        session['user'] = userid
        # Record login time
        login_time = datetime.now()
        cursor.execute("INSERT INTO login_logs (userid, login_time) VALUES (%s, %s)", (userid, login_time))
        conn.commit()
    cursor.close()
    conn.close()
    if user:
        return redirect(url_for('display_chart'))
    print("Login failed, invalid credentials")
    env_info = f"Running in: {sys.executable.split('/')[-3] if 'venv' in sys.executable else 'Global Python'}"
    return render_template('login.html', error="Invalid credentials", env_info=env_info)

@app.route('/logout', methods=['POST'])
def logout():
    print("Processing logout request")
    if 'user' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        userid = session['user']
        logout_time = datetime.now()
        # Update logout time and calculate duration
        cursor.execute("SELECT login_time FROM login_logs WHERE userid = %s AND logout_time IS NULL ORDER BY login_time DESC LIMIT 1", (userid,))
        login_time = cursor.fetchone()
        if login_time:
            login_time = login_time[0]
            duration = logout_time - login_time
            cursor.execute("UPDATE login_logs SET logout_time = %s, duration = %s WHERE userid = %s AND logout_time IS NULL ORDER BY login_time DESC LIMIT 1", 
                           (logout_time, str(duration), userid))
            conn.commit()
        print(f"User {userid} logged out")
        session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/display_chart')
def display_chart():
    print("Entering display_chart function")
    if 'user' not in session:
        print("No user session, redirecting to login")
        return redirect(url_for('login'))
    print("User authenticated, rendering chart page")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Bar chart data
        cursor.execute("SELECT sentiment_category, COUNT(*) as count FROM sentiment_table GROUP BY sentiment_category")
        bar_data = cursor.fetchall()
        print("Bar Data:", bar_data)
        if not bar_data:
            bar_chart = "<p>No bar chart data available.</p>"
        else:
            bar_categories = [row[0] for row in bar_data]
            bar_counts = [row[1] for row in bar_data]
            bar_fig = px.bar(x=bar_categories, y=bar_counts, title="Sentiment Distribution",
                             labels={"x": "Sentiment Category", "y": "Count"},
                             category_orders={"sentiment_category": ["Very Bad", "Bad", "Average", "Good", "Very Good"]})
            bar_fig.update_layout(
                title_font_color="#32CD32",
                xaxis_title_font_color="#32CD32",
                yaxis_title_font_color="#32CD32"
            )
            bar_chart = pio.to_html(bar_fig, full_html=False)

        # Line chart data
        cursor.execute("SELECT review_date, sentiment_category FROM sentiment_table WHERE sentiment_category IN ('Very Good', 'Good', 'Very Bad', 'Bad')")
        line_data = cursor.fetchall()
        print("Line Data:", line_data)
        if not line_data:
            line_chart = "<p>No line chart data available.</p>"
        else:
            df = pd.DataFrame(line_data, columns=['review_date', 'sentiment_category'])
            print("Raw DataFrame:", df.head())
            df['review_date'] = pd.to_datetime(df['review_date'])
            df_grouped = df.groupby(['review_date', 'sentiment_category']).size().reset_index(name='count')
            print("Grouped DataFrame:", df_grouped)
            if df_grouped.empty:
                line_chart = "<p>No grouped data for line chart.</p>"
            else:
                line_fig = px.line(df_grouped, x='review_date', y='count', color='sentiment_category',
                                   title="Positive and Negative Reviews Over Time",
                                   labels={"review_date": "Date", "count": "Number of Reviews"},
                                   category_orders={"sentiment_category": ["Very Bad", "Bad", "Good", "Very Good"]})
                line_fig.update_layout(
                    title_font_color="#32CD32",
                    xaxis_title_font_color="#32CD32",
                    yaxis_title_font_color="#32CD32"
                )
                line_chart = pio.to_html(line_fig, full_html=False)

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error in display_chart: {str(e)}")
        bar_chart = "<p>Error loading bar chart.</p>"
        line_chart = "<p>Error loading line chart.</p>"

    env_info = f"Running in: {sys.executable.split('/')[-3] if 'venv' in sys.executable else 'Global Python'}"
    return render_template('chart.html', bar_chart=bar_chart, line_chart=line_chart, env_info=env_info)

@app.route('/logs')
def view_logs():
    print("Entering view_logs function")
    if 'user' not in session or session['user'] != 'admin':
        print("Unauthorized access to logs, redirecting to login")
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM login_logs ORDER BY login_time")  # Reverse order (newest first)
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    env_info = f"Running in: {sys.executable.split('/')[-3] if 'venv' in sys.executable else 'Global Python'}"
    return render_template('logs.html', logs=logs, env_info=env_info)

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True, host='0.0.0.0', port=5000)