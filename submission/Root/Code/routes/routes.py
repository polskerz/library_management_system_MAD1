from flask import Flask, render_template, url_for, flash, redirect, request, session
from models.models import db, User, Book, Section, Request, Feedback
from datetime import datetime, timedelta
import re
import plotly.graph_objs as go
from sqlalchemy import func
from app import app 
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler



## USER AUTHENTICATION
def user_login_required(func):
    @wraps(func)
    def login_function(*args, **kwargs):
        if 'user_login' not in session:
            flash('Please login first!')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return login_function



## ADMIN AUTHENTICATION
def admin_login_required(func):
    @wraps(func)
    def login_function(*args, **kwargs):
        if 'user_login' not in session:
            flash('Please login first!')
            return redirect(url_for('login'))
        user = User.query.get(session['user_login'])
        if not user.is_admin:
            flash('You are not an admin!')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return login_function



## LOGIN
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == '' or password == '':
        flash('Username or password cannot be empty')
        return redirect(url_for('login'))
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User does not exist')
        return redirect(url_for('login'))
    if not user.check_password(password):
        flash('Incorrect password')
        return redirect(url_for('login'))
    session['user_login'] = user.user_id
    flash('User successfully logged in!')
    return redirect(url_for('index'))



## SIGN UP
@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup_post():
    username = request.form.get('username')
    name = request.form.get('name')
    password = request.form.get('password')
    if username == '' or password == '':
        flash('Username or password cannot be empty')
        return redirect(url_for('signup'))
    user = User.query.filter_by(username=username).first()
    if user:
        flash('This username is not available')
        return redirect(url_for('signup'))
    user = User(username=username, name=name, password=password, is_admin=False)
    db.session.add(user)
    db.session.commit()
    flash('User successfully registered')
    return redirect(url_for('login'))



## INDEX
@app.route('/')
@user_login_required
def index():
    user = User.query.get(session['user_login'])
    section = Section.query.all()
    book = Book.query.all()
    if user.is_admin:
        return redirect(url_for('admin'))
    else:
        return render_template('index.html', user=user, section=section, book=book)



## LOGOUT
@app.route('/logout')
def logout():
    user = User.query.get(session['user_login'])
    return render_template('logout_confirmation.html', user=user)

@app.route('/logout', methods=['POST'])
def logout_post():
    session.pop('user_login', None)
    flash('User successfully logged out!')
    return redirect(url_for('login'))



## USER - STATS
@app.route('/stats')
@user_login_required
def user_stats():
    user_id = User.query.get(session['user_login']).user_id
    current_books = db.session.query(func.count(Request.request_id)).filter(
        Request.user_id == user_id,
        Request.return_date == None,
        Request.is_revoked == False
    ).scalar()

    overdue_books = db.session.query(func.count(Request.request_id)).filter(
        Request.user_id == user_id,
        Request.is_revoked == True
    ).scalar()

    completed_books = db.session.query(func.count(Request.request_id)).filter(
        Request.user_id == user_id,
        Request.return_date != None,
        Request.is_revoked == False
    ).scalar()

    completed_books_by_section = db.session.query(Request.section_id, func.count(Request.request_id)).filter(
        Request.user_id == user_id,
        Request.return_date != None,
        Request.is_revoked == False
    ).group_by(Request.section_id).all()

    sections = [] 
    for section in completed_books_by_section:
        sections.append(Section.query.get(section[0]).section_name)
    counts = [section[1] for section in completed_books_by_section]
    completed_books_chart = go.Figure()
    completed_books_chart.add_trace(go.Bar(x=sections, y=counts,
                                     marker=dict(color=['blue', 'green', 'red', 'orange']))) 
    completed_books_chart.update_layout(title='Completed Books By Section',
                                      xaxis_title='Sections',
                                      yaxis_title='Number of Books')

    book_status_pie_chart = go.Figure(data=[go.Pie(labels=['Current', 'Completed', 'Overdue'],
                                        values=[current_books, completed_books, overdue_books],
                                        hole=.3)])
    book_status_pie_chart.update_layout(title='Book Status Distribution')

    completed_books_chart = completed_books_chart.to_html(full_html=False)
    book_status_pie_chart = book_status_pie_chart.to_html(full_html=False)
    return render_template('user_stats.html', user=User.query.get(session['user_login']), completed_books_chart=completed_books_chart, book_status_pie_chart=book_status_pie_chart)



## USER - PROFILE
@app.route('/profile')
@user_login_required
def profile():
    return render_template('profile.html', user=User.query.get(session['user_login']))



## USER - EDIT PASSWORD
@app.route('/profile/edit_password')
@user_login_required
def edit_password():
    return render_template('edit_password.html', user=User.query.get(session['user_login']))

@app.route('/profile/edit_password', methods=['POST'])
@user_login_required
def edit_password_post():
    username = request.form.get('username')
    name = request.form.get('name')
    new_password = request.form.get('new-password')
    old_password = request.form.get('old-password')
    if username == '' or new_password == '':
        flash('Username or password cannot be empty')
        return redirect(url_for('edit_password'))
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User does not exist')
        return redirect(url_for('edit_password'))
    if not user.check_password(old_password):
        flash('Old password is incorrect')
        return redirect(url_for('edit_password'))
    if old_password == new_password:
        flash('New password is the same as old password')
        return redirect(url_for('edit_password'))
    user.password = new_password
    db.session.commit()
    flash('Password successfully updated')
    return redirect(url_for('index.html'))



## USER - EDIT DETAILS
@app.route('/profile/edit_details')
@user_login_required
def edit_details():
    return render_template('edit_details.html', user=User.query.get(session['user_login']))

@app.route('/profile/edit_details', methods=['POST'])
@user_login_required
def edit_details_post():
    new_username = request.form.get('new-username')
    new_name = request.form.get('new-name')
    password = request.form.get('password')
    if new_username == '' or new_name == '':
        flash('Username or name cannot be empty')
        return redirect(url_for('edit_details'))
    user = User.query.filter_by(username=new_username).first()
    if not user.check_password(password):
        flash('Password is incorrect')
        return redirect(url_for('edit_details'))
    if user and user.user_id != session['user_login']:
        flash('This username is not available')
        return redirect(url_for('edit_details'))
    user = User.query.get(session['user_login'])
    user.username = new_username
    user.name = new_name
    db.session.commit()
    flash('Details successfully updated')
    return redirect(url_for('index'))



## ADMIN
@app.route('/admin')
@admin_login_required 
def admin():
    user = User.query.get(session['user_login'])
    if not user.is_admin:
        flash('You are not an admin!')
        return redirect(url_for('index'))
    return render_template('admin.html', admin=user, users=User.query.all(), books=Book.query.all(), sections=Section.query.all(), requests=Request.query.all(), feedbacks=Feedback.query.all())



## ADMIN - STATS
@app.route('/admin/stats')
@admin_login_required 
def admin_stats():
    user_count = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    book_count = Book.query.count()
    section_count = Section.query.count()
    issued_count = Request.query.filter_by(return_date=None, is_revoked=False).count()
    returned_count = Request.query.filter(Request.return_date.isnot(None)).count()
    revoked_count = Request.query.filter_by(is_revoked=True).count()
    sections = Section.query.all()
    section_names = [section.section_name for section in sections]
    books_count = [Book.query.filter_by(section_id=section.section_id).count() for section in sections]

    section_books_chart = go.Figure()
    section_books_chart.add_trace(go.Bar(x=section_names, y=books_count,
                                     marker=dict(color=['blue', 'green', 'red', 'orange']))) 
    section_books_chart.update_layout(title='Distribution of Sections vs. Books',
                                      xaxis_title='Sections',
                                      yaxis_title='Number of Books')

    bar_chart = go.Figure()
    bar_chart.add_trace(go.Bar(x=['Users', 'Admins'], y=[user_count, admin_count],
                               marker=dict(color=['green', 'orange', 'red'])))
    bar_chart.update_layout(title='Number of Users vs. Number of Admins', xaxis_title='Users/Admins', yaxis_title='Count')

    requests_pie_chart = go.Figure(data=[go.Pie(labels=['Issued', 'Returned', 'Revoked'],
                                        values=[issued_count, returned_count, revoked_count],
                                        hole=.3)])
    requests_pie_chart.update_layout(title='Request Status Distribution')

    bar_chart_html = bar_chart.to_html(full_html=False)
    requests_pie_chart_html = requests_pie_chart.to_html(full_html=False)
    section_books_chart_html = section_books_chart.to_html(full_html=False)

    return render_template('admin_stats.html', admin=User.query.get(session['user_login']), 
                           bar_chart_html=bar_chart_html, requests_pie_chart_html=requests_pie_chart_html, 
                           section_books_chart_html=section_books_chart_html)



## ADMIN - USERS
@app.route('/admin/users')
@admin_login_required 
def admin_users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('admin_users.html', admin=User.query.get(session['user_login']), users=users)



## ADMIN - USERS - ADD
@app.route('/admin/users/add')
@admin_login_required
def admin_users_add():
    return render_template('admin_users_add.html', admin=User.query.get(session['user_login']))

@app.route('/admin/users/add', methods=['POST'])
@admin_login_required
def admin_users_add_post():
    username = request.form.get('username')
    name = request.form.get('name')
    password = request.form.get('password')
    is_admin = 'admin_status' in request.form
    if username == '' or password == '':
        flash('Username or password cannot be empty')
        return redirect(url_for('admin_users_add'))
    user = User.query.filter_by(username=username).first()
    if user:
        flash('This username is not available')
        return redirect(url_for('admin_users_add'))
    user = User(username=username, name=name, password=password, is_admin=is_admin)
    db.session.add(user)
    db.session.commit()
    flash('User successfully added')
    return redirect(url_for('admin_users'))



## ADMIN - USERS - DELETE
@app.route('/admin/users/<int:user_id>/delete')
@admin_login_required
def admin_users_delete(user_id):
    user = User.query.get(user_id)
    return render_template('admin_users_delete.html', admin=User.query.get(session['user_login']), user=user)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_login_required
def admin_users_delete_post(user_id):
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User successfully deleted')
    return redirect(url_for('admin_users'))



## ADMIN - USERS - EDIT
@app.route('/admin/users/<int:user_id>/edit_details')
@admin_login_required
def admin_users_edit(user_id):
    user = User.query.get(user_id)
    return render_template('admin_users_edit.html', admin=User.query.get(session['user_login']), user=user)

@app.route('/admin/users/<int:user_id>/edit_details', methods=['POST'])
@admin_login_required
def admin_users_edit_post(user_id):
    new_username = request.form.get('new-username')
    new_name = request.form.get('new-name')
    new_password = request.form.get('new-password')
    if new_username == '' or new_name == '' or new_password == '':
        flash('Field cannot be empty')
        return redirect(url_for('admin_users_edit', user_id=user.user_id))
    user = User.query.filter_by(username=new_username).first()
    if user and user.user_id != user_id:
        flash('This username is not available')
        return redirect(url_for('admin_users_edit', user_id=user.user_id))
    user = User.query.get(user_id)
    user.username = new_username
    user.name = new_name
    user.password = new_password
    db.session.commit()
    flash('User details successfully updated')
    return redirect(url_for('admin_users'))



## ADMIN - REQUESTS
@app.route('/admin/requests')
@admin_login_required 
def admin_requests():
    requests = Request.query.all()
    return render_template('admin_requests.html', admin=User.query.get(session['user_login']), requests=requests)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    return value.strftime(format)



## ADMIN - REQUESTS - ISSUE
@app.route('/admin/requests/issue_request')
@admin_login_required
def issue_request():
    def_issue_date = datetime.now().strftime('%Y-%m-%dT%H:%M')
    def_due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M')
    admin = User.query.get(session['user_login'])
    return render_template('issue_request.html', def_issue_date=def_issue_date, def_due_date=def_due_date, admin=admin)


@app.route('/admin/requests/issue_request', methods=['POST'])
@admin_login_required
def issue_request_post():
    user_id = request.form.get('issue_user_id')
    book_id = request.form.get('issue_book_id')
    form_issue_date = request.form.get('issue_date')
    issue_date = datetime.strptime(form_issue_date, '%Y-%m-%dT%H:%M')
    form_due_date = request.form.get('due_date')
    due_date = datetime.strptime(form_due_date, '%Y-%m-%dT%H:%M')
    section_id = Book.query.get(book_id).section_id
    if user_id == '' or book_id == '' or issue_date == '' or due_date == '':
        flash('Field cannot be empty')
        return redirect(url_for('issue_request'))
    if Request.query.filter_by(user_id=user_id, book_id=book_id, is_revoked=False, return_date=None).first():
        flash('User currently has this book in their library')
        return redirect(url_for('issue_request'))
    if due_date < issue_date:
        flash('Due date cannot be before issue date')
        return redirect(url_for('issue_request'))
    issue_request = Request(user_id=user_id, book_id=book_id, section_id=section_id, issue_date=issue_date, due_date=due_date, is_revoked=False)
    db.session.add(issue_request)
    db.session.commit()
    flash('Request successfully issued!')
    return redirect(url_for('admin_requests'))



## ADMIN - REQUESTS - MANUAL REVOKE
@app.route('/admin/requests/<int:request_id>/manual_revoke')
@admin_login_required
def manual_revoke(request_id):
    request = Request.query.get(request_id)
    return render_template('manual_revoke.html', admin=User.query.get(session['user_login']), request=request)

@app.route('/admin/requests/<int:request_id>/manual_revoke', methods=['POST'])
@admin_login_required
def manual_revoke_post(request_id):
    request = Request.query.get(request_id)
    request.is_revoked = True
    db.session.commit()
    flash('Request successfully revoked')
    return redirect(url_for('admin_requests'))



## ADMIN - REQUESTS - UNDO MANUAL REVOKE
@app.route('/admin/requests/<int:request_id>/undo_manual_revoke')
@admin_login_required
def undo_manual_revoke(request_id):
    request = Request.query.get(request_id)
    return render_template('undo_manual_revoke.html', admin=User.query.get(session['user_login']), request=request)

@app.route('/admin/requests/<int:request_id>/undo_manual_revoke', methods=['POST'])
@admin_login_required
def undo_manual_revoke_post(request_id):
    request = Request.query.get(request_id)
    if request.is_revoked == False:
        flash('Book is not overdue')
        return redirect(url_for('admin_requests'))
    request.is_revoked = False
    db.session.commit()
    flash('Request successfully un-revoked')
    return redirect(url_for('admin_requests'))



## ADMIN - REQUESTS - DELETE
@app.route('/admin/requests/<int:request_id>/delete_request')
@admin_login_required
def delete_request(request_id):
    request = Request.query.get(request_id)
    return render_template('delete_request.html', admin=User.query.get(session['user_login']), request=request)

@app.route('/admin/requests/<int:request_id>/delete_request', methods=['POST'])
@admin_login_required
def delete_request_post(request_id):
    request = Request.query.get(request_id)
    db.session.delete(request)
    db.session.commit()
    flash('Request successfully deleted!')
    return redirect(url_for('admin_requests'))



## ADMIN - ADD SECTION
@app.route('/admin/add_section')
@admin_login_required
def add_section():
    today = datetime.today()
    formatted_date = today.strftime('%Y-%m-%d')
    return render_template('add_section.html', admin=User.query.get(session['user_login']), formatted_date=formatted_date)

@app.route('/admin/add_section', methods=['POST'])
@admin_login_required
def add_section_post():
    section_name = request.form.get('section_name')
    section_date = datetime.strptime(request.form.get('section_date'), '%Y-%m-%d')
    section_description = request.form.get('section_description')
    if section_name == '' or section_description == '' or section_date == '':
        flash('Fields cannot be empty')
        return redirect(url_for('add_section'))
    section = Section.query.filter_by(section_name=section_name).first()
    if section:
        flash('Section already exists!')
        return redirect(url_for('add_section'))
    if len(section_name) > 100 or len(section_description) > 1000:
        flash('Section name or description is too long!')
        return redirect(url_for('add_section'))
    section = Section(section_name=section_name, date_created=section_date, description=section_description)
    db.session.add(section)
    db.session.commit()
    flash('Section successfully added!')
    return redirect(url_for('admin'))



## ADMIN - ADD BOOK
@app.route('/admin/<int:section_id>/add_book')
@admin_login_required
def add_book(section_id):
    today = datetime.today()
    formatted_date = today.strftime('%Y-%m-%d')
    section = Section.query.get(section_id)
    return render_template('add_book.html', admin=User.query.get(session['user_login']), section=section, formatted_date=formatted_date)

@app.route('/admin/<int:section_id>/add_book', methods=['POST'])
@admin_login_required
def add_book_post(section_id):
    book_name = request.form.get('book_name')
    book_author = request.form.get('book_author')
    book_content = request.form.get('book_content')
    book_publisher = request.form.get('book_publisher')
    book_publish_date = datetime.strptime(request.form.get('book_publish_date'), '%Y-%m-%d')
    section_id = section_id
    if book_name == '' or book_author == '' or book_publisher == '' or book_content == '' or book_publish_date == '':
        flash('Fields cannot be empty')
        return redirect(url_for('add_book', section_id=section_id))
    if len(book_name) > 50 or len(book_author) > 50 or len(book_content) > 200 or len(book_publisher) > 50:
        flash('Field length exceeded!')
        return redirect(url_for('add_book', section_id=section_id))
    book = Book(book_name=book_name, book_author=book_author, book_content=book_content, book_publisher=book_publisher, book_publish_date=book_publish_date, section_id=section_id)
    db.session.add(book)
    db.session.commit()
    flash('Book successfully added!')
    return redirect(url_for('admin'))

@app.route('/admin/<int:section_id>/view_section/add_book')
@admin_login_required
def vs_add_book(section_id):
    today = datetime.today()
    formatted_date = today.strftime('%Y-%m-%d')
    section = Section.query.get(section_id)
    return render_template('add_book.html', admin=User.query.get(session['user_login']), section=section, formatted_date=formatted_date)

@app.route('/admin/<int:section_id>/view_section/add_book', methods=['POST'])
@admin_login_required
def vs_add_book_post(section_id):
    book_name = request.form.get('book_name')
    book_author = request.form.get('book_author')
    book_content = request.form.get('book_content')
    book_publisher = request.form.get('book_publisher')
    book_publish_date = datetime.strptime(request.form.get('book_publish_date'), '%Y-%m-%d')
    section_id = section_id
    if book_name == '' or book_author == '' or book_publisher == '' or book_content == '' or book_publish_date == '':
        flash('Fields cannot be empty')
        return redirect(url_for('add_book', section_id=section_id))
    book = Book(book_name=book_name, book_author=book_author, book_content=book_content, book_publisher=book_publisher, book_publish_date=book_publish_date, section_id=section_id)
    db.session.add(book)
    db.session.commit()
    flash('Book successfully added!')
    return redirect(url_for('view_section', section_id=section_id))



## ADMIN - EDIT SECTION
@app.route('/admin/<int:section_id>/edit_section')
@admin_login_required
def edit_section(section_id):
    section = Section.query.get(section_id)
    return render_template('edit_section.html', admin=User.query.get(session['user_login']), section=section)

@app.route('/admin/<int:section_id>/edit_section', methods=['POST'])
@admin_login_required
def edit_section_post(section_id):
    new_section_name = request.form.get('section_name')
    new_description = request.form.get('section_description')
    new_date_created = datetime.strptime(request.form.get('section_date'), '%Y-%m-%d')
    if new_section_name == '' or new_description == '' or new_date_created == '':
        flash('Fields cannot be empty')
        return redirect(url_for('edit_section', section_id=section_id))
    section = Section.query.get(section_id)
    section.section_name = new_section_name
    section.date_created = new_date_created
    section.description = new_description
    db.session.commit()
    flash('Section successfully edited!')
    return redirect(url_for('admin'))



## ADMIN - DELETE SECTION
@app.route('/admin/<int:section_id>/delete_section')
@admin_login_required
def delete_section(section_id):
    section = Section.query.get(section_id)
    return render_template('delete_section.html', admin=User.query.get(session['user_login']), section=Section.query.get(section_id))

@app.route('/admin/<int:section_id>/delete_section', methods=['POST'])
@admin_login_required
def delete_section_post(section_id):
    section = Section.query.get(section_id)
    books = Book.query.filter_by(section_id=section_id).all()
    if not section:
        flash('Section does not exist')
        return redirect(url_for('admin'))
    db.session.delete(section)
    for book in books:
        db.session.delete(book)
    db.session.commit()
    flash('Section successfully deleted')
    return redirect(url_for('admin'))



## ADMIN - VIEW SECTION
@app.route('/admin/<int:section_id>/view_section')
@admin_login_required
def view_section(section_id):
    section = Section.query.get(section_id)
    books = Book.query.filter_by(section_id=section_id).all()
    return render_template('view_section.html', admin=User.query.get(session['user_login']), section=section, books=books)



## ADMIN - VIEW BOOK
@app.route('/admin/<int:section_id>/view_section/<int:book_id>/view_book')
@admin_login_required
def view_book(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    return render_template('view_book.html', admin=User.query.get(session['user_login']), section=section, book=book)

@app.route('/admin/<int:section_id>/view_section/<int:book_id>/see_book_info')
@admin_login_required
def admin_book_info(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    feedbacks = Feedback.query.filter_by(book_id=book_id).all()
    return render_template('admin_book_info.html', admin=User.query.get(session['user_login']), section=section, book=book, feedbacks=feedbacks)



## ADMIN - DELETE FEEDBACK
@app.route('/admin/<int:section_id>/view_section/<int:book_id>/see_book_info/<int:feedback_id>/delete_feedback')
@admin_login_required
def delete_feedback(feedback_id, section_id, book_id):
    feedback = Feedback.query.get(feedback_id)
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    return render_template('delete_feedback.html', admin=User.query.get(session['user_login']), section=section, book=book, feedback=feedback)

@app.route('/admin/<int:section_id>/view_section/<int:book_id>/see_book_info/<int:feedback_id>/delete_feedback', methods=['POST'])
@admin_login_required
def delete_feedback_post(feedback_id, section_id, book_id):
    feedback = Feedback.query.get(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    flash('Feedback successfully deleted')
    return redirect(url_for('admin_book_info', section_id=section_id, book_id=book_id))



## ADMIN - EDIT BOOK
@app.route('/admin/<int:section_id>/view_section/<int:book_id>/edit_book')
@admin_login_required
def edit_book(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    return render_template('edit_book.html', admin=User.query.get(session['user_login']), section=section, book=book)

@app.route('/admin/<int:section_id>/view_section/<int:book_id>/edit_book', methods=['POST'])
@admin_login_required
def edit_book_post(section_id, book_id):
    new_book_name = request.form.get('book_name')
    new_book_author = request.form.get('book_author')
    new_book_content = request.form.get('book_content')
    new_book_publisher = request.form.get('book_publisher')
    new_book_publish_date = datetime.strptime(request.form.get('book_publish_date'), '%Y-%m-%d')
    if new_book_name == '' or new_book_author == '' or new_book_publisher == '' or new_book_content == '' or new_book_publish_date == '':
        flash('Fields cannot be empty')
        return redirect(url_for('edit_book', section_id=section_id, book_id=book_id))
    book = Book.query.get(book_id)
    book.book_name = new_book_name
    book.book_author = new_book_author
    book.book_content = new_book_content
    book.book_publisher = new_book_publisher
    book.book_publish_date = new_book_publish_date
    db.session.commit()
    flash('Book successfully edited!')
    return redirect(url_for('view_section', section_id=section_id))



## ADMIN - DELETE BOOK
@app.route('/admin/<int:section_id>/view_section/<int:book_id>/delete_book')
@admin_login_required
def delete_book(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    return render_template('delete_book.html', admin=User.query.get(session['user_login']), section=section, book=book)

@app.route('/admin/<int:section_id>/view_section/<int:book_id>/delete_book', methods=['POST'])
@admin_login_required
def delete_book_post(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    if not book:
        flash('Book does not exist')
        return redirect(url_for('view_section', section_id=section_id))
    db.session.delete(book)
    db.session.commit()
    flash('Book successfully deleted')
    return redirect(url_for('view_section', section_id=section_id))



## USER - BOOK INFO
@app.route('/<int:section_id>/<int:book_id>/book_info')
@user_login_required
def book_info(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    feedbacks = Feedback.query.filter_by(book_id=book_id).all()
    return render_template('book_info.html', user=User.query.get(session['user_login']), section=section, book=book, feedbacks=feedbacks)



## USER - SEARCH
@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('query')
    search_filter = request.form.get('filter')
    user = User.query.get(session['user_login'])
    if search_query == '' :
        flash('Search field cannot be empty')
        return redirect(url_for('index'))
    if search_filter == 'sections':
        search_sections = Section.query.filter(Section.section_name.ilike(f'%{search_query}%')).all()
        return render_template('search_results_section.html', user=user, search_sections=search_sections, filter=search_filter, search_query=search_query)
    elif search_filter == 'books':
        search_books = Book.query.filter(Book.book_name.ilike(f'%{search_query}%')).all()
        return render_template('search_results_book.html', user=user, search_books=search_books, filter=search_filter, search_query=search_query)
    else:
        search_authors = Book.query.filter(Book.book_author.ilike(f'%{search_query}%')).all()
        return render_template('search_results_author.html', user=user, search_authors=search_authors, filter=search_filter, search_query=search_query)
    


## USER - REQUEST BOOK
@app.route('/<int:section_id>/<int:book_id>/request_confirmation')
@user_login_required
def request_confirmation(section_id, book_id):
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    return render_template('request_confirmation.html', user=User.query.get(session['user_login']), section=section, book=book)

@app.route('/<int:section_id>/<int:book_id>/request_confirmation', methods=['POST'])
@user_login_required
def request_confirmation_post(section_id, book_id):
    user = User.query.get(session['user_login'])
    section = Section.query.get(section_id)
    book = Book.query.get(book_id)
    requests = Request.query.filter_by(user_id=user.user_id).all()
    not_returned = 0
    for request in requests:
        if request.return_date == None:
            not_returned += 1
    if not_returned >= 5:
        flash('You can only request up to 5 books at a time')
        return redirect(url_for('user_view_section', section_id=section_id))
    total_requests = Request.query.filter_by(user_id=user.user_id, book_id=book.book_id)
    flagged = 0
    for request in total_requests:
        if request.return_date == None:
            flagged = 1
    if flagged != 0:
        flash('You have already requested this book')
        return redirect(url_for('user_view_section', section_id=section_id))
    request = Request(user_id=user.user_id, book_id=book.book_id, section_id=section.section_id, issue_date=datetime.now(), due_date=datetime.now() + timedelta(days=7), return_date=None)
    db.session.add(request)
    db.session.commit()
    flash('Request successfully added to your library!')
    return redirect(url_for('current_books'))



## USER - MY LIBRARY - CURRENT BOOKS
@app.route('/my_library/current_books')
@user_login_required
def current_books():
    user = User.query.get(session['user_login'])
    requests = Request.query.filter_by(user_id=user.user_id, is_revoked=False).all()
    for request in requests:
        time_difference = request.due_date - datetime.now()
        days = time_difference.days
        hours, remainder = divmod(time_difference.seconds, 3600) 
        minutes, seconds = divmod(remainder, 60) 
        request.time_remaining = {'days': days, 'hours': hours, 'minutes': minutes, 'seconds': seconds}
    return render_template('current_books.html', user=user, requests=requests)

@app.route('/my_library/completed_books')
@user_login_required
def completed_books():
    user = User.query.get(session['user_login'])
    requests = Request.query.filter_by(user_id=user.user_id, is_revoked=False).all()
    for request in requests:
        if request.return_date != None :
            time_difference = request.return_date - request.issue_date
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600) 
            minutes, seconds = divmod(remainder, 60) 
            request.time_taken = {'days': days, 'hours': hours, 'minutes': minutes, 'seconds': seconds}
    return render_template('completed_books.html', user=user, requests=requests)



## USER - MY LIBRARY - OVERDUE BOOKS
@app.route('/my_library/overdue_books')
@user_login_required
def overdue_books():
    user = User.query.get(session['user_login'])
    requests = Request.query.filter_by(user_id=user.user_id, is_revoked=True).all()
    return render_template('overdue_books.html', user=user, requests=requests)



## USER - VIEW SECTION
@app.route('/<int:section_id>/view_section')
@user_login_required
def user_view_section(section_id):
    section = Section.query.get(section_id)
    books = Book.query.filter_by(section_id=section_id).all()
    return render_template('user_view_section.html', user=User.query.get(session['user_login']), section=section, books=books)



## USER - READ BOOK
@app.route('/my_library/current_books/<int:request_id>/read_book')
@user_login_required
def read_book(request_id):
    request = Request.query.get(request_id)
    return render_template('read_book.html', user=User.query.get(session['user_login']), request=request)



## USER - RETURN BOOK
@app.route('/my_library/current_books/<int:request_id>/return_confirmation')
@user_login_required
def return_confirmation(request_id):
    request = Request.query.get(request_id)
    return render_template('return_confirmation.html', user=User.query.get(session['user_login']), request=request)

@app.route('/my_library/current_books/<int:request_id>/return_confirmation', methods=['POST'])
@user_login_required
def return_confirmation_post(request_id):
    request = Request.query.get(request_id)
    request.return_date = datetime.now()
    db.session.commit()
    flash('Book successfully returned!')
    return redirect(url_for('completed_books'))



## USER - WRITE FEEDBACK
@app.route('/my_library/completed_books/<int:book_id>/write_feedback')
@user_login_required
def write_feedback(book_id):
    book = Book.query.get(book_id)
    user = User.query.get(session['user_login'])
    return render_template('write_feedback.html', user=user, book=book)

@app.route('/my_library/completed_books/<int:book_id>/write_feedback', methods=['POST'])
@user_login_required
def write_feedback_post(book_id):
    user = User.query.get(session['user_login'])
    book = Book.query.get(book_id)
    content = request.form.get('content')
    if len(content) > 1000:
        flash('Feedback must be less than 1000 characters')
        return redirect(url_for('write_feedback', book_id=book_id))
    feedback = Feedback(user_id=user.user_id, book_id=book.book_id, content=content)
    db.session.add(feedback)
    db.session.commit()
    flash('Feedback successfully submitted!')
    return redirect(url_for('book_info', book_id=book.book_id, section_id=book.section_id))



## BACKGROUND TASK - REVOKING OVERDUE BOOKS
@app.route('/overdue_books')
def overdue_books_check():
    requests = Request.query.all()
    for request in requests:
        if request.return_date == None and request.due_date < datetime.now() and request.is_revoked == False:
            request.return_date = datetime.now()
            request.is_revoked = True
            db.session.commit()

def scheduled_task():
    with app.app_context():
        overdue_books_check()

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_task, trigger="interval", seconds=5)
scheduler.start()