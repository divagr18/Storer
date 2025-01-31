import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="keshav",
    password="keshav1234" ,
    database = 'storer',
    port = 3308
)

cursor = conn.cursor()


# Test connection by fetching some data from Products table
cursor.execute("""
    INSERT INTO Products (name, description, price, stock_level, category)
    VALUES (%s, %s, %s, %s, %s)
""", ("Product A", "A description for Product A", 19.99, 100, "Category 1"))
conn.commit()
cursor.execute("SELECT * FROM Products;")
products = cursor.fetchall()
for product in products:
    print(product)

cursor.close()
conn.close()