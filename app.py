from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from functools import wraps
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'FirstFlashApp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:admin@localhost/FirstFlashApp'
app.config['SECRET_KEY'] = 'yWTo9R4oOX'
mysql = MySQL(app)

db = SQLAlchemy(app)

admin = Admin(app)

class Users(db.Model):
            id = db.Column(db.Integer, primary_key = True)
            username = db.Column(db.String(30))
            name = db.Column(db.String(30))
            email = db.Column(db.String(30))
            register_date = db.Column(db.String(30))

class Articles(db.Model):
            id = db.Column(db.Integer, primary_key = True)
            title = db.Column(db.String(30))
            author = db.Column(db.String(30))
            create_date = db.Column(db.String(30))

admin.add_view(ModelView(Users, db.session))
admin.add_view(ModelView(Articles, db.session))

#Articles = Articles()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
        cur.close()

@app.route('/article/<string:id>/')
def article(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cur.fetchone()
    return render_template('article.html', article=article)

class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min = 1, max = 50)])
    username = StringField('Username', [validators.Length(min = 4, max = 25)])
    email = StringField('Email', [validators.Length(min = 6, max = 50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message = 'Passwords do not match!')
    ])
    confirm = PasswordField('Confirm Password', [validators.DataRequired()])

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash('You are now registered and can log in!', 'success')

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in!', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Login!'
                return render_template('login.html', error = error)

        else:
            error = 'Invalid Login!'
            return render_template('login.html', error = error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Error: Please Login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM articles WHERE author=%s", [session['username']])
    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
        cur.close()

class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min = 1, max = 200), validators.DataRequired()])
    body = TextAreaField('Body', [validators.Length(min = 30), validators.DataRequired()])

@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))
        mysql.connection.commit()

        cur.close()
        flash('Article Created!', "success")

        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Get article by id
    result = cur.execute("SELECT * FROM articles WHERE id = %s AND author=%s", [id, session['username']])

    article = cur.fetchone()
    cur.close()
    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(title)
        # Execute
        cur.execute ("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title, body, id))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash('Article Deleted!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='Secret0123'
    app.run(host="0.0.0.0", port=5000, debug=True)
