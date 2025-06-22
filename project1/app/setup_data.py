import mysql.connector
import random
from textblob import TextBlob
from datetime import datetime, timedelta

conn = mysql.connector.connect(host="localhost", user="root", password="", database="restaurant_reviews", unix_socket="/var/run/mysqld/mysqld.sock", ssl_disabled=True)
cursor = conn.cursor()

review_templates = [
    "The ambiance here is delightful, service was prompt.",
    "Food quality was disappointing, staff seemed rude.",
    "Meal was decent, nothing to write home about.",
    "Loved the vibrant atmosphere, food exceeded expectations.",
    "Taste was off, texture felt unpleasant.",
    "Service was average, food was okay for the price.",
    "Incredible dining vibe, staff made the experience.",
    "Dishes were subpar, waiter was inattentive.",
    "Food was satisfactory, not particularly memorable.",
    "Exceptional meal, highly recommend this spot.",
    "Experience was terrible, won’t visit again.",
    "Staff was friendly, meal was moderately good."
]

unique_reviews = set()
while len(unique_reviews) < 100:
    base = random.choice(review_templates)
    variation = base + " " + random.choice(["on a busy night", "during lunch", "with great company", "in a cozy corner", "after a long day"])
    if variation not in unique_reviews:
        unique_reviews.add(variation)
reviews = list(unique_reviews)

start_date = datetime.now() - timedelta(days=30)
random_dates = [start_date + timedelta(days=random.randint(0, 30)) for _ in range(100)]

cursor.execute('''CREATE TABLE IF NOT EXISTS reviews_table (
                    id INT PRIMARY KEY,
                    review_text VARCHAR(255),
                    review_date DATE)''')
for i, (review, date) in enumerate(zip(reviews, random_dates), 1):
    cursor.execute("INSERT IGNORE INTO reviews_table (id, review_text, review_date) VALUES (%s, %s, %s)", (i, review, date.strftime('%Y-%m-%d')))
conn.commit()

cursor.execute('''CREATE TABLE IF NOT EXISTS sentiment_table (
                    id INT PRIMARY KEY,
                    review_text VARCHAR(255),
                    review_date DATE,
                    sentiment_score FLOAT,
                    sentiment_category VARCHAR(20))''')

def get_sentiment(review):
    analysis = TextBlob(review)
    score = (analysis.sentiment.polarity + 1) * 5
    if score >= 8:
        category = "Very Good"
    elif score >= 6:
        category = "Good"
    elif score >= 4:
        category = "Average"
    elif score >= 2:
        category = "Bad"
    else:
        category = "Very Bad"
    return score, category

cursor.execute("SELECT r.id, r.review_text, r.review_date FROM reviews_table r")
rows = cursor.fetchall()
for row in rows:
    id, review, date = row
    score, category = get_sentiment(review)
    cursor.execute("INSERT INTO sentiment_table (id, review_text, review_date, sentiment_score, sentiment_category) VALUES (%s, %s, %s, %s, %s)", (id, review, date, score, category))
conn.commit()

cursor.close()
conn.close()
print("Data setup completed")
