import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    port = 3308
)

print("Connected to MySQL!", conn.is_connected())
conn.close()
