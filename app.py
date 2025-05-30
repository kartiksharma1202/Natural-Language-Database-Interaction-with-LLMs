# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
from flask import jsonify
import os
from nlp_to_sql import NLPtoSQL
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # MySQL username
app.config['MYSQL_PASSWORD'] = 'Kartik@1997'  #MySQL password
app.config['MYSQL_DB'] = 'flask_auth_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get form fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare Passwords
            if check_password_hash(password, password_candidate):
                # Passed
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = data['id']

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid password'
                return render_template('login.html', error=error)
            
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form fields
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('signup.html')
        
        # Create cursor
        cur = mysql.connection.cursor()
        
        # Check if username already exists
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])
        if result > 0:
            flash('Username already exists', 'danger')
            return render_template('signup.html')
        
        # Check if email already exists
        result = cur.execute("SELECT * FROM users WHERE email = %s", [email])
        if result > 0:
            flash('Email already exists', 'danger')
            return render_template('signup.html')
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        # Execute
        cur.execute("INSERT INTO users(username, email, password) VALUES(%s, %s, %s)", 
                    (username, email, hashed_password))
        
        # Commit to DB
        mysql.connection.commit()
        
        # Close connection
        cur.close()
        
        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Create cursor
    cur = mysql.connection.cursor()
    
    # Get user info
    result = cur.execute("SELECT * FROM users WHERE id = %s", [session['user_id']])
    user = cur.fetchone()
    
    # Get grades
    result = cur.execute("SELECT * FROM grades WHERE user_id = %s", [session['user_id']])
    grades = cur.fetchall()
    
    # Close connection
    cur.close()
    
    return render_template('dashboard.html', user=user, grades=grades)

@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if request.method == 'POST':
        # Get form fields
        name = request.form.get('name', '')
        email = request.form['email']
        
        # Create cursor
        cur = mysql.connection.cursor()
        
        # Execute
        cur.execute("UPDATE users SET name = %s, email = %s WHERE id = %s", 
                    (name, email, session['user_id']))
        
        # Commit to DB
        mysql.connection.commit()
        
        # Close connection
        cur.close()
        
        flash('Profile updated', 'success')
        return redirect(url_for('dashboard'))
    
    # Get current user info
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM users WHERE id = %s", [session['user_id']])
    user = cur.fetchone()
    cur.close()
    
    return render_template('update_profile.html', user=user)

@app.route('/reset_password', methods=['GET', 'POST'])
@login_required
def reset_password():
    if request.method == 'POST':
        # Get form fields
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Create cursor
        cur = mysql.connection.cursor()
        
        # Get user by id
        result = cur.execute("SELECT * FROM users WHERE id = %s", [session['user_id']])
        user = cur.fetchone()
        
        # Validate old password
        if not check_password_hash(user['password'], old_password):
            flash('Old password is incorrect', 'danger')
            return render_template('reset_password.html')
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return render_template('reset_password.html')
        
        # Hash new password
        hashed_password = generate_password_hash(new_password)
        
        # Execute
        cur.execute("UPDATE users SET password = %s WHERE id = %s", 
                    (hashed_password, session['user_id']))
        
        # Commit to DB
        mysql.connection.commit()
        
        # Close connection
        cur.close()
        
        flash('Password reset successfully', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('reset_password.html')
nlp_sql = NLPtoSQL()



@app.route('/nlp_query', methods=['GET', 'POST'])
@login_required
def nlp_query():
    """Page for entering natural language queries"""
    return render_template('nlp_query.html')

@app.route('/api/query', methods=['POST'])
@login_required
def process_query():
    """API endpoint to process natural language queries"""
    try:
        # Get the natural language query from the request
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "No query provided"}), 400
            
        natural_language_query = data['query']
        
        # Convert natural language to SQL
        sql_query, error = nlp_sql.generate_sql(natural_language_query)
        if error:
            return jsonify({"error": error}), 400
            
        # Execute the SQL query
        results, error = nlp_sql.execute_query(sql_query, mysql.connection)
        if error:
            return jsonify({"error": error, "sql": sql_query}), 400
            
        # Return the results along with the generated SQL query
        return jsonify({
            "sql": sql_query,
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/query_builder', methods=['GET'])
@login_required
def query_builder():
    """Admin interface for running direct SQL queries and viewing results"""
    return render_template('query_builder.html')

@app.route('/api/run_sql', methods=['POST'])
@login_required
def run_sql_query():
    """API endpoint to directly run SQL queries (admin only)"""
    try:
        # Get the SQL query from the request
        data = request.get_json()
        if not data or 'sql' not in data:
            return jsonify({"error": "No SQL query provided"}), 400
            
        sql_query = data['sql']
        
        
        if not nlp_sql._validate_sql(sql_query):
            return jsonify({"error": "SQL query contains potentially unsafe operations"}), 403
            
        # Execute the SQL query
        results, error = nlp_sql.execute_query(sql_query, mysql.connection)
        if error:
            return jsonify({"error": error}), 400
            
        # Return the results
        return jsonify({
            "results": results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)