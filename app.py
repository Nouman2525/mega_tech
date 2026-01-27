from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import os

app = Flask(__name__)
# This secret key protects your user sessions
app.secret_key = os.environ.get('SECRET_KEY', 'mega_tech_secret_999')

def get_db_connection():
    # This reads the 'DATABASE_URL' we will add to Render settings
    # If it's not found, it won't crash, but it won't connect.
    db_url = os.environ.get('DATABASE_URL')
    
    # Cloud databases (like Neon) often use 'postgres://' 
    # but Python needs 'postgresql://'. This fix makes it work automatically.
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return psycopg2.connect(db_url)

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, role FROM users WHERE username = %s AND password = %s", 
                    (data['username'], data['password']))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user:
            session['user'] = user[0]
            session['role'] = user[1]
            return jsonify({"status": "success"})
    except Exception as e:
        print(f"Database Error: {e}")
    return jsonify({"status": "error"}), 401

@app.route('/dashboard')
def dashboard():
    if 'user' not in session: return redirect(url_for('login_page'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ip_uploads WHERE uploaded_by = %s", (session['user'],))
    count = cur.fetchone()[0]
    cur.execute("SELECT ip_address, ip_type, upload_time FROM ip_uploads WHERE uploaded_by = %s ORDER BY upload_time DESC LIMIT 10", (session['user'],))
    history = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('dashboard.html', username=session['user'], role=session['role'], count=count, history=history)

@app.route('/upload_page')
def upload_page():
    if 'user' not in session: return redirect(url_for('login_page'))
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_ip():
    if 'user' not in session: return jsonify({"status": "error"}), 403
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO ip_uploads (ip_address, ip_type, uploaded_by) VALUES (%s, %s, %s)", 
                    (data['ip'], data['type'], session['user']))
        conn.commit()
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error"}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/admin/manage')
def admin_page():
    if session.get('role') != 'admin': return "Access Denied", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, role FROM users")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('admin.html', users=users)

@app.route('/admin/create_user', methods=['POST'])
def create_user():
    if session.get('role') != 'admin': return jsonify({"status": "error"}), 403
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'staff')", 
                    (data['username'], data['password']))
        conn.commit()
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error"}), 400
    finally:
        cur.close()
        conn.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

if __name__ == '__main__':
    # On the web, Render will handle the port, but locally it uses 5000
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))