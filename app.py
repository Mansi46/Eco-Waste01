from flask import Flask, render_template, url_for, redirect, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Database Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    issue_type = db.Column(db.String(100), nullable=False) 
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Pending') 
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Routes ---
@app.route('/')
def home():
    return render_template('base.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        # Make the first user an admin automatically
        is_admin = True if User.query.count() == 0 else False
        
        new_user = User(username=username, password=hashed_password, is_admin=is_admin)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        issue_type = request.form.get('issue_type')
        description = request.form.get('description')
        
        new_report = Report(issue_type=issue_type, description=description, user_id=current_user.id)
        db.session.add(new_report)
        db.session.commit()
        flash('Report submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.date_reported.desc()).all()
    return render_template('dashboard.html', reports=user_reports)

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))
    
    all_reports = Report.query.order_by(Report.date_reported.desc()).all()
    return render_template('admin.html', reports=all_reports)

@app.route('/update_status/<int:report_id>/<string:status>')
@login_required
def update_status(report_id, status):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    report = Report.query.get_or_404(report_id)
    report.status = status
    db.session.commit()
    flash(f'Report #{report_id} status updated to {status}.', 'success')
    return redirect(url_for('admin'))

@app.route('/awareness')
def awareness():
    return render_template('awareness.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)