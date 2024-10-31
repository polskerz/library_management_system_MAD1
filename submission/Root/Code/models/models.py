from flask_sqlalchemy import SQLAlchemy
from app import app
from datetime import datetime
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    def check_password(self, password):
        if self.password == password:
            return True
        else:
            return False

class Book(db.Model):
    __tablename__ = 'book'
    book_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    book_name = db.Column(db.String(50), nullable=False)
    book_author = db.Column(db.String(50), nullable=False)
    book_content = db.Column(db.String(200), nullable=True)
    book_publisher = db.Column(db.String(50), nullable=False)
    book_publish_date = db.Column(db.Date, nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.section_id'), nullable=False)

class Section(db.Model):
    __tablename__ = 'section'
    section_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    section_name = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(1000), nullable=True)

    books = db.relationship('Book', backref='section', lazy=True)

class Request(db.Model):
    __tablename__ = 'request'
    request_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.book_id'), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.section_id'), nullable=False)
    issue_date= db.Column(db.DateTime, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    is_revoked = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='request', lazy=True)
    book = db.relationship('Book', backref='request', lazy=True)
    section = db.relationship('Section', backref='request', lazy=True)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    feedback_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.book_id'), nullable=False)
    content = db.Column(db.String(1000), nullable=False)

    user = db.relationship('User', backref='feedback', lazy=True)
    book = db.relationship('Book', backref='feedback', lazy=True)


with app.app_context():
    db.create_all()
    # create admin if admin does not exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password='admin', name='admin', is_admin=True)
        db.session.add(admin)
        db.session.commit()
    user = User.query.filter_by(username='user').first()
    if not user:
        user = User(username='user', password='user', name='user')
        db.session.add(user)
        db.session.commit()
    section = Section.query.filter_by(section_name='section').first()
    if not section:
        today = datetime.today().date()
        section = Section(section_name='section', date_created=today, description='description')
        db.session.add(section)
        db.session.commit()
    book = Book.query.filter_by(book_name='book').first()
    if not book:
        today = datetime.today().date()
        book_content = "https://clickdimensions.com/links/TestPDFfile.pdf"
        book = Book(book_name='book', book_author='author', book_content=book_content, book_publisher='publisher', book_publish_date=today, section_id='1')
        db.session.add(book)
        db.session.commit()