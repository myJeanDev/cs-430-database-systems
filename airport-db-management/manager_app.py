import os
import pyodbc
import hashlib
from functools import wraps
from flask import Flask, session, request, render_template, redirect, url_for

# START-STUDENT-CODE
# Define the DSN for the ODBC connection to your PostgreSQL database.
DSN = "DRIVER={PostgreSQL};SERVER=faure.cs.colostate.edu;PORT=5432;DATABASE=willschm;UID=willschm;PWD=831553213"
# END-STUDENT-CODE

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


def parse_float(value):
    return float(value) if value.replace('.', '', 1).isdigit() else None


def parse_int(value):
    return int(value) if value.isdigit() else None


def get_employees():
    # START-STUDENT-CODE
    # 1. Connect to the database using pyodbc and DSN.
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    # 2. Retrieve employees with their roles (Manager, Technician, ATC) or blank.
    cursor.execute('''
        SELECT 
            e.ssn, 
            e.name, 
            e.address,
            e.phone,
            e.salary,
            CASE 
                WHEN m.ssn IS NOT NULL THEN 'Manager'
                WHEN t.ssn IS NOT NULL THEN 'Technician'
                WHEN a.ssn IS NOT NULL THEN 'ATC'
                ELSE ''
            END AS role
        FROM airport.employee e
        LEFT JOIN airport.manager m ON e.ssn = m.ssn
        LEFT JOIN airport.technician t ON e.ssn = t.ssn
        LEFT JOIN airport.atc a ON e.ssn = a.ssn
    ''')
    employees = cursor.fetchall()
    
    # 3. Close the connection and return the result.
    cnxn.close()

    # END-STUDENT-CODE
    return employees


def get_airplane_models():
    # START-STUDENT-CODE
    # 1. Connect to the database
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    # 2. Retrieve all airplane models (model_number, capacity, weight)
    cursor.execute('''
        SELECT model_number, capacity, weight
        FROM airport.airplane_model
    ''')
    
    models = cursor.fetchall()
    
    # 3. Close the connection
    cnxn.close()

    # END-STUDENT-CODE
    return models


def get_airplanes():
    # START-STUDENT-CODE
    # 1. Connect to the database
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    # 2. Retrieve all airplanes (reg_number, model_number)
    cursor.execute('''
        SELECT reg_number, model_number
        FROM airport.airplane
    ''')
    
    # 3. Close the connection
    cnxn.close()
    airplanes = cursor.fetchall()

    # END-STUDENT-CODE
    return airplanes


def get_faa_tests():
    # START-STUDENT-CODE
    # 1. Connect to the database
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    # 2. Retrieve all FAA tests (test_number, name, max_score)
    cursor.execute('''
        SELECT test_number, name, max_score
        FROM airport.faa_test
    ''')
    
    faa_tests = cursor.fetchall()
    
    # 3. Close the connection
    cnxn.close()

    return faa_tests


def get_airworthiness_tests():
    # START-STUDENT-CODE
    # 1. Connect to the database
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    # 2. Retrieve all airworthiness test events (test_number, ssn, reg_number, date, duration, score)
    cursor.execute('''
        SELECT test_number, ssn, reg_number, date, duration, score
        FROM airport.test_event
    ''')
    
    tests = cursor.fetchall()
    
    # 3. Close the connection
    cnxn.close()
    # END-STUDENT-CODE
    return tests


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # START-SAMPLE-SOLUTION
        # 1. Connect to the DB
        # 2. Select manager based on SSN and retrieve the password
        # 3. Close the connection
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()
        cursor.execute('''
            SELECT e.password
            FROM airport.employee e
            JOIN airport.manager m ON e.ssn = m.ssn
            WHERE e.ssn = ?
        ''', (username,))
        user = cursor.fetchone()
        cnxn.close()
        # END-SAMPLE-SOLUTION

        if user and verify_password(password, user[0]):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', message="Authentication error!")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def employee_add():
    employees = get_employees()
    error_message = None

    if request.method == 'POST':
        ssn = request.form['ssn'].strip()
        name = request.form['name'].strip() or None
        password = request.form['password'].strip() or None
        address = request.form['address'].strip() or None
        phone = request.form['phone'].strip() or None
        salary = request.form['salary'].strip()
        specialization = request.form.get('specialization')

        # Validate SSN length
        if len(ssn) > 9:
            error_message = "SSN must be 9 characters or less"
            return render_template('employees.html', employees=employees, action='Add', error_message=error_message)
        
        # Continue with the rest of the code if validation passes
        salary = parse_float(salary)
        password_hashed = hash_password(password) if password else None

        # START-STUDENT-CODE
        # 1. Connect to DB
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()
        
        # 2. Check if this SSN already exists
        cursor.execute('''
            SELECT ssn FROM airport.employee WHERE ssn = ?
        ''', (ssn,))
        
        existing_employee = cursor.fetchone()
        
        # 3. If not, insert into employee and handle specialization
        if not existing_employee:
            try:
                # Insert into employee table
                cursor.execute('''
                    INSERT INTO airport.employee (ssn, name, password, address, phone, salary)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (ssn, name, password_hashed, address, phone, salary))
                
                # Handle specialization if provided
                if specialization:
                    if specialization == 'manager':
                        cursor.execute('''
                            INSERT INTO airport.manager (ssn)
                            VALUES (?)
                        ''', (ssn,))
                    elif specialization == 'technician':
                        cursor.execute('''
                            INSERT INTO airport.technician (ssn)
                            VALUES (?)
                        ''', (ssn,))
                    elif specialization == 'atc':
                        cursor.execute('''
                            INSERT INTO airport.atc (ssn)
                            VALUES (?)
                        ''', (ssn,))
                
                # Commit the transaction
                cnxn.commit()
                return redirect(url_for('employee_add'))
            except Exception as e:
                cnxn.rollback()
                error_message = f"Database error: {str(e)}"
            finally:
                # 4. Close connection
                cnxn.close()
        else:
            error_message = "An employee with this SSN already exists"
        # END-STUDENT-CODE

    return render_template('employees.html', employees=employees, action='Add', error_message=error_message)


@app.route('/employee/update', methods=['GET', 'POST'])
@login_required
def employee_update():
    employees = get_employees()

    if request.method == 'POST':
        ssn = request.form['ssn'].strip()
        name = request.form['name'].strip() or None
        password = request.form['password'].strip() or None
        address = request.form['address'].strip() or None
        phone = request.form['phone'].strip() or None
        salary = request.form['salary'].strip()
        specialization = request.form.get('specialization')

        salary = parse_float(salary)
        password_hashed = hash_password(password) if password else None

        # START-STUDENT-CODE
        # 1. Connect to DB
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()
        
        # 2. Check if employee with SSN exists
        cursor.execute('''
            SELECT ssn FROM airport.employee WHERE ssn = ?
        ''', (ssn,))
        
        existing_employee = cursor.fetchone()
        
        # 3. If exists, update non-empty fields
        if existing_employee:
            # Build update parts for non-empty fields
            update_parts = []
            params = []
            
            if name:
                update_parts.append("name = ?")
                params.append(name)
            
            if password_hashed:
                update_parts.append("password = ?")
                params.append(password_hashed)
            
            if address:
                update_parts.append("address = ?")
                params.append(address)
            
            if phone:
                update_parts.append("phone = ?")
                params.append(phone)
            
            if salary:
                update_parts.append("salary = ?")
                params.append(salary)
            
            # If we have fields to update
            if update_parts:
                query = "UPDATE airport.employee SET " + ", ".join(update_parts) + " WHERE ssn = ?"
                params.append(ssn)
                cursor.execute(query, params)
            
            # 4. Handle specialization
            if specialization:
                # Change specialization
                # (I am assuming employees can only be: manager, technician, or atc)
                cursor.execute("DELETE FROM airport.manager WHERE ssn = ?", (ssn,))
                cursor.execute("DELETE FROM airport.technician WHERE ssn = ?", (ssn,))
                cursor.execute("DELETE FROM airport.atc WHERE ssn = ?", (ssn,))
                
                if specialization == 'manager':
                    cursor.execute("INSERT INTO airport.manager (ssn) VALUES (?)", (ssn,))
                elif specialization == 'technician':
                    cursor.execute("INSERT INTO airport.technician (ssn) VALUES (?)", (ssn,))
                elif specialization == 'atc':
                    cursor.execute("INSERT INTO airport.atc (ssn) VALUES (?)", (ssn,))
            
            cnxn.commit()
        # 5. Close connection
        cnxn.close()
        # END-STUDENT-CODE

        return redirect(url_for('employee_update'))

    return render_template('employees.html', employees=employees, action='Update')


@app.route('/employee/delete', methods=['GET', 'POST'])
@login_required
def employee_delete():
    employees = get_employees()

    if request.method == 'POST':
        ssn = request.form['ssn'].strip()

        # START-STUDENT-CODE
        # 1. Connect to DB
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()
        
        try:
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # 2. Delete the employee's specializations
            cursor.execute("DELETE FROM airport.manager WHERE ssn = ?", (ssn,))
            cursor.execute("DELETE FROM airport.technician WHERE ssn = ?", (ssn,))
            cursor.execute("DELETE FROM airport.atc WHERE ssn = ?", (ssn,))
            
            cursor.execute("DELETE FROM airport.expert WHERE ssn = ?", (ssn,))
            cursor.execute("DELETE FROM airport.test_event WHERE ssn = ?", (ssn,))
            
            # 3. Delete employee data
            cursor.execute("DELETE FROM airport.employee WHERE ssn = ?", (ssn,))
            
            # Commit the transaction
            cursor.execute("COMMIT")
        except Exception as e:
            # If anything goes wrong, rollback
            cursor.execute("ROLLBACK")
            print(f"Error deleting employee: {e}")
        finally:
            # 4. Close connection
            cnxn.close()
        # END-STUDENT-CODE

        return redirect(url_for('employee_delete'))

    return render_template('employees.html', employees=employees, action='Delete')


@app.route('/expertise', methods=['GET', 'POST'])
@login_required
def expertise():
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    if request.method == 'POST':
        ssn = request.form['ssn'].strip()
        model_number = request.form['model_number'].strip()
        action = request.form['action']

        if action == "add":
            try:
                cursor.execute('''
                    CALL airport.insert_expert(?, ?)
                ''', (ssn, model_number))
                cnxn.commit()
            except pyodbc.IntegrityError:
                pass
        elif action == "remove":
            cursor.execute('''
                DELETE FROM airport.expert
                WHERE ssn = ? AND model_number = ?
            ''', (ssn, model_number))
            if cursor.rowcount > 0:
                cnxn.commit()

    cursor.execute('''
        SELECT t.ssn, e.name, 
               (SELECT STRING_AGG(model_number, ', ') 
                FROM airport.expert 
                WHERE ssn = t.ssn) AS expertise
        FROM airport.technician t
        JOIN airport.employee e ON t.ssn = e.ssn
        ORDER BY e.name
    ''')
    technicians = cursor.fetchall()

    formatted_technicians = [
        (tech[0], tech[1], tech[2] if tech[2] is not None else '') for tech in technicians
    ]

    cursor.execute('''
        SELECT model_number, capacity, weight 
        FROM airport.airplane_model
        ORDER BY model_number
    ''')
    models = cursor.fetchall()

    cnxn.close()

    return render_template('expertise.html', technicians=formatted_technicians, models=models)


@app.route('/update_salaries', methods=['GET', 'POST'])
@login_required
def update_salaries():
    if request.method == 'POST':
        percentage = parse_float(request.form['percentage'].strip())
        if percentage is not None:
            percentage = round(percentage, 2) / 100

            # START-STUDENT-CODE
            # 1. Connect to DB
            cnxn = pyodbc.connect(DSN)
            cursor = cnxn.cursor()
            
            # 2. Increase salary by 'percentage' for all employees
            cursor.execute('''
                UPDATE airport.employee
                SET salary = salary + (salary * ?)
            ''', (percentage,))
            
            # Commit the transaction
            cnxn.commit()
            
            # 3. Close connection
            cursor.close()
            cnxn.close()
            # END-STUDENT-CODE

        return redirect(url_for('index'))

    return render_template('salary.html')


@app.route('/models/add', methods=['GET', 'POST'])
@login_required
def model_add():
    if request.method == 'POST':
        model_number = request.form['model_number'].strip()
        capacity = parse_int(request.form['capacity'].strip())
        weight = parse_float(request.form['weight'].strip())

        # START-STUDENT-CODE
        # 1. Connect to DB
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()

        # 2. Insert new airplane model if it does not exist
        try:
            cursor.execute('''
                SELECT model_number
                FROM airport.airplane_model
                WHERE model_number = ?
            ''', (model_number,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute('''
                    INSERT INTO airport.airplane_model (model_number, capacity, weight)
                    VALUES (?, ?, ?)
                ''', (model_number, capacity, weight))
                cnxn.commit()
            else:
                error_message = f"Model number {model_number} already exists."
        except pyodbc.Error as e:
            cnxn.rollback()
        finally:
            # 3. Close connection
            cnxn.close()
        # END-STUDENT-CODE


    return render_template('models.html', models=get_airplane_models(), action="Add")


@app.route('/models/update', methods=['GET', 'POST'])
@login_required
def model_update():
    if request.method == 'POST':
        model_number = request.form['model_number'].strip()
        capacity = request.form['capacity'].strip() or None
        weight = request.form['weight'].strip() or None

        capacity = parse_int(capacity) if capacity else None
        weight = parse_float(weight) if weight else None

        # START-STUDENT-CODE
        # 1. Connect to DB
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()

        try:
            # 2. If model exists, update non-empty fields
            cursor.execute('''
                SELECT model_number
                FROM airport.airplane_model
                WHERE model_number = ?
            ''', (model_number,))
            existing = cursor.fetchone()

            if existing:
                update_fields = []
                params = []
                
                if capacity is not None:
                    update_fields.append("capacity = ?")
                    params.append(capacity)
                if weight is not None:
                    update_fields.append("weight = ?")
                    params.append(weight)
                
                if update_fields:
                    update_query = '''
                        UPDATE airport.airplane_model
                        SET {}
                        WHERE model_number = ?
                    '''.format(", ".join(update_fields))
                    params.append(model_number)
                    cursor.execute(update_query, params)
                    cnxn.commit()
            else:
                error_message = f"Model number {model_number} does not exist."
        except pyodbc.Error as e:
            cnxn.rollback()
        finally:
            # 3. Close connection
            cnxn.close()
        # END-STUDENT-CODE

    return render_template('models.html', models=get_airplane_models(), action="Update")


@app.route('/models/delete', methods=['GET', 'POST'])
@login_required
def model_delete():
    if request.method == 'POST':
        model_number = request.form['model_number'].strip()

        # START-STUDENT-CODE
        # 1. Connect to DB
        cnxn = pyodbc.connect(DSN)
        cursor = cnxn.cursor()

        try:
            # Check for airplanes that have the model we are deleting
            cursor.execute('''
                SELECT reg_number 
                FROM airport.airplane 
                WHERE model_number = ?
            ''', (model_number,))
            dependent_airplanes = cursor.fetchall()
            
            if dependent_airplanes:
                message = "Cannot delete: Model is used by existing airplanes!"
            else:
                # 2. Delete the model if it exists
                cursor.execute('''
                    DELETE FROM airport.airplane_model 
                    WHERE model_number = ?
                ''', (model_number,))
                if cursor.rowcount > 0:
                    cnxn.commit()
                    message = "Model deleted successfully"
                else:
                    message = "Model not found"

        except pyodbc.Error as e:
            message = f"Database error: {str(e)}"
        finally:
            # 3. Close connection
            cnxn.close()
        # END-STUDENT-CODE

    return render_template('models.html', models=get_airplane_models(), action="Delete")


@app.route('/airplanes/add', methods=['GET', 'POST'])
@login_required
def airplane_add():
    # Connect to DB
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    if request.method == 'POST':
        reg_number = request.form['reg_number'].strip()
        model_number = request.form['model_number'].strip()
        
        # Check if airplane with this reg_number already exists
        cursor.execute('''
            SELECT COUNT(*) 
            FROM airport.airplane 
            WHERE reg_number = ?
        ''', (reg_number,))
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert new airplane
            cursor.execute('''
                INSERT INTO airport.airplane (reg_number, model_number)
                VALUES (?, ?)
            ''', (reg_number, model_number))
            cnxn.commit()
    
    # Retrieve list of airplane_model for dropdown
    cursor.execute('''
        SELECT model_number, capacity, weight   
        FROM airport.airplane_model
        ORDER BY model_number
    ''')
    
    models = cursor.fetchall()
    
    # Get airplanes BEFORE closing the connection
    cursor.execute('''
        SELECT a.reg_number, a.model_number, am.capacity, am.weight
        FROM airport.airplane a
        JOIN airport.airplane_model am ON a.model_number = am.model_number
        ORDER BY a.reg_number
    ''')
    
    airplanes = cursor.fetchall()
    
    # Close connection
    cursor.close()
    cnxn.close()

    return render_template('airplanes.html', airplanes=airplanes, models=models, action="Add")


@app.route('/airplanes/update', methods=['GET', 'POST'])
@login_required
def airplane_update():
    # 1. Connect to DB
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    
    # 2. (POST) If airplane exists, update the model_number
    if request.method == 'POST':
        reg_number = request.form['reg_number'].strip()
        model_number = request.form['model_number'].strip()
        
        # Check if airplane with this reg_number exists
        cursor.execute('''
            SELECT COUNT(*) 
            FROM airport.airplane 
            WHERE reg_number = ?
        ''', (reg_number,))
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            # Update the existing airplane's model number
            cursor.execute('''
                UPDATE airport.airplane
                SET model_number = ?
                WHERE reg_number = ?
            ''', (model_number, reg_number))
            cnxn.commit()
    
    # 3. Retrieve list of airplane_model for dropdown
    cursor.execute('''
        SELECT model_number, capacity, weight
        FROM airport.airplane_model
        ORDER BY model_number
    ''')
    
    models = cursor.fetchall()
    
    cursor.execute('''
        SELECT a.reg_number, a.model_number, am.capacity, am.weight
        FROM airport.airplane a
        JOIN airport.airplane_model am ON a.model_number = am.model_number
        ORDER BY a.reg_number
    ''')
    
    airplanes = cursor.fetchall()
    
    # 4. Close connection
    cursor.close()
    cnxn.close()

    return render_template('airplanes.html', airplanes=airplanes, models=models, action="Update")


@app.route('/airplanes/delete', methods=['GET', 'POST'])
@login_required
def airplane_delete():
    # 1. Connect to DB
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    message = None
    
    # 2. If airplane exists, delete it
    if request.method == 'POST':
        reg_number = request.form['reg_number'].strip()
        
        # First check if there are any test_events using this airplane
        cursor.execute('''
            SELECT COUNT(*) 
            FROM airport.test_event 
            WHERE reg_number = ?
        ''', (reg_number,))
        
        event_count = cursor.fetchone()[0]
        
        if event_count > 0:
            # Cannot delete airplane with associated test events
            message = f"Cannot delete airplane {reg_number} because of test events {event_count}."
        else:
            # Check if airplane exists
            cursor.execute('''
                SELECT COUNT(*) 
                FROM airport.airplane 
                WHERE reg_number = ?
            ''', (reg_number,))
            
            airplane_count = cursor.fetchone()[0]
            
            if airplane_count > 0:
                # Delete the airplane
                cursor.execute('''
                    DELETE FROM airport.airplane
                    WHERE reg_number = ?
                ''', (reg_number,))
                cnxn.commit()
    
    # Get the airplane data
    cursor.execute('''
        SELECT a.reg_number, a.model_number, am.capacity, am.weight
        FROM airport.airplane a
        JOIN airport.airplane_model am ON a.model_number = am.model_number
        ORDER BY a.reg_number
    ''')
    airplanes = cursor.fetchall()
    
    # Get the airplane models data
    cursor.execute('''
        SELECT model_number, capacity, weight
        FROM airport.airplane_model
        ORDER BY model_number
    ''')
    models = cursor.fetchall()
    
    # 3. Close connection
    cursor.close()
    cnxn.close()

    return render_template('airplanes.html', airplanes=airplanes, models=models, action="Delete", message=message)


@app.route('/faa_tests/add', methods=['GET', 'POST'])
@login_required
def faa_test_add():
    # START-STUDENT-CODE
    # 1. Connect to DB
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    message = None
    
    # 2. If test_number doesn't exist, insert new FAA test
    if request.method == 'POST':
        test_number = request.form['test_number'].strip()
        name = request.form['name'].strip()
        max_score = parse_float(request.form['max_score'].strip())
        
        # Check if test_number already exists
        cursor.execute('''
            SELECT COUNT(*) 
            FROM airport.faa_test 
            WHERE test_number = ?
        ''', (test_number,))
        
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Insert new FAA test
            cursor.execute('''
                INSERT INTO airport.faa_test (test_number, name, max_score)
                VALUES (?, ?, ?)
            ''', (test_number, name, max_score))
            cnxn.commit()
    
    # 3. Close connection
    cursor.close()
    cnxn.close()
    # END-STUDENT-CODE

    return render_template('faa_tests.html', faa_tests=get_faa_tests(), action="Add")


@app.route('/faa_tests/update', methods=['GET', 'POST'])
@login_required
def faa_test_update():
    # START-STUDENT-CODE
    # 1. Connect to DB
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    message = None
    
    # 2. If test_number exists, update name/max_score
    if request.method == 'POST':
        test_number = request.form['test_number'].strip()
        name = request.form['name'].strip() or None
        max_score = request.form['max_score'].strip() or None
        max_score = parse_float(max_score) if max_score else None
        
        # Check if test_number exists
        cursor.execute('''
            SELECT COUNT(*) 
            FROM airport.faa_test 
            WHERE test_number = ?
        ''', (test_number,))
        
        count = cursor.fetchone()[0]
        
        if count > 0:
            update_parts = []
            params = []
            
            if name is not None:
                update_parts.append("name = ?")
                params.append(name)
                
            if max_score is not None:
                update_parts.append("max_score = ?")
                params.append(max_score)
                
            if update_parts:
                query = f'''
                    UPDATE airport.faa_test
                    SET {', '.join(update_parts)}
                    WHERE test_number = ?
                '''
                params.append(test_number)
                
                cursor.execute(query, params)
                cnxn.commit()
    
    # 3. Close connection
    cursor.close()
    cnxn.close()
    # END-STUDENT-CODE

    return render_template('faa_tests.html', faa_tests=get_faa_tests(), action="Update")


@app.route('/faa_tests/delete', methods=['GET', 'POST'])
@login_required
def faa_test_delete():
# START-STUDENT-CODE
    # 1. Connect to DB
    cnxn = pyodbc.connect(DSN)
    cursor = cnxn.cursor()
    message = None
    
    # 2. If test_number exists, delete from faa_test
    if request.method == 'POST':
        test_number = request.form['test_number'].strip()
        
        # First check if there are any test_events using this FAA test
        cursor.execute('''
            SELECT COUNT(*) 
            FROM airport.test_event 
            WHERE test_number = ?
        ''', (test_number,))
        
        event_count = cursor.fetchone()[0]
        
        if event_count > 0:
            # Cannot delete FAA test with associated test events
            message = f"Can't delete FAA Test #{test_number} because it has {event_count} test events"
        else:
            # Check if FAA test exists
            cursor.execute('''
                SELECT COUNT(*) 
                FROM airport.faa_test 
                WHERE test_number = ?
            ''', (test_number,))
            
            test_count = cursor.fetchone()[0]
            
            if test_count > 0:
                # Delete the FAA test
                cursor.execute('''
                    DELETE FROM airport.faa_test
                    WHERE test_number = ?
                ''', (test_number,))
                cnxn.commit()
    
    # 3. Close connection
    cursor.close()
    cnxn.close()
    # END-STUDENT-CODE

    return render_template('faa_tests.html', faa_tests=get_faa_tests(), action="Delete")


@app.route('/tests')
@login_required
def tests():
    return render_template('tests.html', tests=get_airworthiness_tests())


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
