from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import logging
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for API testing

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SQL-related MCQ questions
questions = [
    {"question": "What type of join returns only matching rows from both tables?", "options": ["LEFT JOIN", "FULL JOIN", "INNER JOIN", "RIGHT JOIN"], "correct": 2},
    {"question": "What will the result of a LEFT JOIN from customers to orders include?", "options": ["Only customers with orders", "All orders", "All customers", "Only unmatched rows"], "correct": 2},
    {"question": "Which clause is required to connect two tables logically in a JOIN?", "options": ["ORDER BY", "WHERE", "ON", "GROUP BY"], "correct": 2},
    {"question": "Which JOIN type shows all categories even if no products exist?", "options": ["LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL OUTER JOIN"], "correct": 3},
    {"question": "What would be the result of this query: 'SELECT c.first_name, o.order_id FROM customers c JOIN orders o ON c.customer_id = o.customer_id;'", "options": ["Error", "Customers with their orders", "Only customers", "Only orders"], "correct": 1},
    {"question": "What is a subquery?", "options": ["Query outside another", "Query inside another query", "A table join", "An index"], "correct": 1},
    {"question": "Which of the following can use a subquery?", "options": ["SELECT", "WHERE", "FROM", "All of the above"], "correct": 3},
    {"question": "A subquery must return how many rows for = comparison?", "options": ["1 row", "Any number", "Only NULL", "No rows"], "correct": 0},
    {"question": "Which query shows the customer with the highest order amount using subquery?", "options": ["SELECT MAX(first_name) FROM customers", "SELECT first_name WHERE total_amount = MAX(total_amount)", "SELECT first_name FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.total_amount = (SELECT MAX(total_amount) FROM orders)", "SELECT first_name ORDER BY total_amount DESC LIMIT 1"], "correct": 2},
    {"question": "What is the purpose of a stored procedure?", "options": ["Back up the database", "Encapsulate reusable SQL logic", "Query all tables", "Drop tables"], "correct": 1},
    {"question": "Which keyword is used to create a stored procedure?", "options": ["DEFINE", "PROCEDURE", "CREATE PROCEDURE", "FUNCTION"], "correct": 2},
    {"question": "Stored procedures can return values using:", "options": ["SELECT", "OUT parameters", "RETURN", "All of the above"], "correct": 3},
    {"question": "When does a trigger execute?", "options": ["Before or after a table action", "Randomly", "Only manually", "Once per day"], "correct": 0},
    {"question": "Which event can you NOT trigger on?", "options": ["INSERT", "UPDATE", "DELETE", "SELECT"], "correct": 3},
    {"question": "A trigger that logs order updates would run on which event?", "options": ["SELECT", "BEFORE INSERT", "AFTER UPDATE", "TRUNCATE"], "correct": 2},
    {"question": "What does RANK() function do?", "options": ["Groups values", "Sorts the table", "Assigns a rank based on value order", "Replaces NULLs"], "correct": 2},
    {"question": "What clause is used to restart ranking for each category?", "options": ["GROUP BY", "OVER", "PARTITION BY", "WHERE"], "correct": 2},
    {"question": "Which one is NOT a window function?", "options": ["RANK()", "DENSE_RANK()", "COUNT()", "LEAD()"], "correct": 2},
    {"question": "Which SQL clause is used to limit rows returned?", "options": ["TOP", "LIMIT", "FETCH", "All of the above (depending on DB)"], "correct": 3},
    {"question": "You want to get average order amount per category. What clause is required?", "options": ["GROUP BY", "ORDER BY", "HAVING", "WINDOW"], "correct": 0}
]

# SQL problems
sql_problems = [
    {
        "name": "Stored Procedure: RankProductsBySales",
        "query": """
CREATE PROCEDURE RankProductsBySales (IN p_category TEXT)
BEGIN
    SELECT 
        p.product_name,
        c.category_name AS category,
        SUM(oi.quantity * oi.unit_price) AS total_sales,
        RANK() OVER (PARTITION BY c.category_id ORDER BY SUM(oi.quantity * oi.unit_price) DESC) AS sales_rank
    FROM Products p
    JOIN Categories c ON p.category_id = c.category_id
    JOIN Order_Items oi ON p.product_id = oi.product_id
    WHERE p_category = 'ALL' OR c.category_name = p_category
    GROUP BY p.product_id, p.product_name, c.category_id, c.category_name
    ORDER BY c.category_name, total_sales DESC;
END;
        """,
        "test_query": "CALL RankProductsBySales('ALL');",
        "expected": [
            ("Laptop", "Electronics", 1000.0, 1),
            ("Smartphone", "Electronics", 1200.0, 2),
            ("T-Shirt", "Clothing", 40.0, 1),
            ("Jeans", "Clothing", 30.0, 2),
            ("Textbook", "Books", 50.0, 1),
            ("Novel", "Books", 45.0, 2)
        ]
    },
    {
        "name": "Scenario Query: Customers with Above-Average Orders",
        "query": """
SELECT DISTINCT 
    c.first_name,
    c.last_name,
    c.email
FROM Customers c
JOIN Orders o ON c.customer_id = o.customer_id
JOIN Order_Items oi ON o.order_id = oi.order_id
JOIN Products p ON oi.product_id = p.product_id
JOIN Categories cat ON p.category_id = cat.category_id
WHERE o.total_amount > (
    SELECT AVG(o2.total_amount)
    FROM Orders o2
    JOIN Order_Items oi2 ON o2.order_id = oi2.order_id
    JOIN Products p2 ON oi2.product_id = p2.product_id
    WHERE p2.category_id = cat.category_id
);
        """,
        "expected": [("Alice", "Smith", "alice@example.com")]
    }
]

@app.route('/')
def index():
    try:
        logger.info("Serving exam_portal.html")
        return render_template('exam_portal.html')
    except Exception as e:
        logger.error(f"Error serving template: {str(e)}")
        return jsonify({"error": "Template not found or server error", "details": str(e)}), 500

@app.route('/get_questions', methods=['GET'])
def get_questions():
    logger.info("Fetching questions")
    return jsonify({"questions": questions})

@app.route('/submit_mcq', methods=['POST'])
def submit_mcq():
    try:
        answers = request.json.get('answers', [])
        if not answers or len(answers) != len(questions):
            logger.error("Invalid number of answers provided")
            return jsonify({"error": "Invalid number of answers provided"}), 400
        score = 0
        results = []
        for i, ans in enumerate(answers):
            correct = ans == questions[i]["correct"]
            if correct:
                score += 1
            results.append({
                "correct": correct,
                "correct_answer": questions[i]["options"][questions[i]["correct"]]
            })
        logger.info(f"MCQ submitted: Score {score}/{len(questions)}")
        return jsonify({"score": score, "total": len(questions), "results": results})
    except Exception as e:
        logger.error(f"Error processing MCQ submission: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/run_sql', methods=['POST'])
def run_sql():
    try:
        queries = request.json.get('queries', [])
        student_name = request.json.get('student_name', 'Anonymous')
        if not queries or len(queries) != len(sql_problems):
            logger.error("Invalid number of queries provided")
            return jsonify({"error": "Invalid number of queries provided"}), 400

        # Set up database
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        # Create tables
        cursor.execute('CREATE TABLE Categories (category_id INTEGER PRIMARY KEY, category_name TEXT NOT NULL)')
        cursor.executemany('INSERT INTO Categories VALUES (?, ?)', [
            (1, 'Electronics'), (2, 'Clothing'), (3, 'Books')
        ])
        cursor.execute('CREATE TABLE Products (product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL, category_id INTEGER, unit_price REAL NOT NULL, FOREIGN KEY (category_id) REFERENCES Categories(category_id))')
        cursor.executemany('INSERT INTO Products VALUES (?, ?, ?, ?)', [
            (1, 'Laptop', 1, 1000.00), (2, 'Smartphone', 1, 600.00),
            (3, 'T-Shirt', 2, 20.00), (4, 'Jeans', 2, 50.00),
            (5, 'Novel', 3, 15.00), (6, 'Textbook', 3, 80.00)
        ])
        cursor.execute('CREATE TABLE Customers (customer_id INTEGER PRIMARY KEY, first_name TEXT NOT NULL, last_name TEXT NOT NULL, email TEXT NOT NULL)')
        cursor.executemany('INSERT INTO Customers VALUES (?, ?, ?, ?)', [
            (1, 'Alice', 'Smith', 'alice@example.com'),
            (2, 'Bob', 'Jones', 'bob@example.com'),
            (3, 'Carol', 'Brown', 'carol@example.com')
        ])
        cursor.execute('CREATE TABLE Orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, total_amount REAL, FOREIGN KEY (customer_id) REFERENCES Customers(customer_id))')
        cursor.executemany('INSERT INTO Orders VALUES (?, ?, ?, ?)', [
            (1, 1, '2025-01-01', 1600.00), (2, 2, '2025-01-02', 70.00),
            (3, 3, '2025-01-03', 95.00), (4, 1, '2025-01-04', 600.00)
        ])
        cursor.execute('CREATE TABLE Order_Items (order_id INTEGER, product_id INTEGER, quantity INTEGER NOT NULL, unit_price REAL NOT NULL, PRIMARY KEY (order_id, product_id), FOREIGN KEY (order_id) REFERENCES Orders(order_id), FOREIGN KEY (product_id) REFERENCES Products(product_id))')
        cursor.executemany('INSERT INTO Order_Items VALUES (?, ?, ?, ?)', [
            (1, 1, 1, 1000.00), (1, 2, 1, 600.00),
            (2, 3, 2, 20.00), (2, 4, 1, 30.00),
            (3, 5, 3, 15.00), (3, 6, 1, 50.00),
            (4, 2, 1, 600.00)
        ])
        conn.commit()

        # Enable stored procedures (simulated for SQLite)
        def create_procedure(name, body):
            cursor.executescript(body)
            conn.create_function(name, 1, lambda x: cursor.execute(f"SELECT * FROM ({body.replace('p_category', repr(x))})").fetchall())

        # Evaluate queries
        score = 0
        results = []
        for i, (query, problem) in enumerate(zip(queries, sql_problems)):
            query = query.strip()
            if not query:
                results.append({"name": problem["name"], "correct": False, "user_result": [], "error": "No query provided"})
                continue
            try:
                if i == 0:  # Stored procedure
                    # Create the procedure
                    cursor.executescript(query)
                    # Test with CALL RankProductsBySales('ALL')
                    cursor.execute(problem["test_query"])
                    user_result = cursor.fetchall()
                else:  # Scenario query
                    cursor.execute(query)
                    user_result = cursor.fetchall()
                expected = problem["expected"]
                correct = sorted(user_result) == sorted(expected)
                if correct:
                    score += 2.5
                results.append({
                    "name": problem["name"],
                    "correct": correct,
                    "user_result": user_result,
                    "error": None
                })
            except sqlite3.Error as e:
                results.append({
                    "name": problem["name"],
                    "correct": False,
                    "user_result": [],
                    "error": str(e)
                })

        conn.close()
        logger.info(f"SQL queries executed: Score {score}/5")
        return jsonify({"score": score, "total": 5, "results": results, "student_name": student_name})
    except Exception as e:
        logger.error(f"Error processing SQL queries: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)