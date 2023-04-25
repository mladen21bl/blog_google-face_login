from flask import Flask, render_template, flash, request, redirect, url_for, session
from datetime import timedelta
from flask_mysqldb import MySQL
import os
import yaml
from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_wtf import FlaskForm
from datetime import timedelta
from flask_login import login_user, logout_user, login_required, current_user
import pickle
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
mysql = MySQL(app)

db = yaml.safe_load(open('db.yaml'))

app.secret_key = 'supersecret'
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

app.permanent_session_lifetime = timedelta(minutes=60)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users28.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.app_context().push()
db = SQLAlchemy(app)

class post(db.Model):
    _id = db.Column('_id', db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.String(1000))
    autor = db.Column(db.String(1000))
    odobren = db.Column(db.Boolean, default=False)
    comments = db.relationship('comment', backref='post', passive_deletes=True)


    def __init__(self, title, text, autor, odobren):
        self.title = title
        self.text = text
        self.autor = autor
        self.odobren = odobren
        self.komentari = []


class comment(db.Model):
    _id = db.Column('_id', db.Integer, primary_key=True)
    text = db.Column(db.String(100))
    author = db.Column(db.String(1000))
    blog_id = db.Column(db.Integer, db.ForeignKey(
        'post._id', ondelete="CASCADE"), nullable=False)


    def __init__(self, text, author, blog_id):
        self.text = text
        self.author = author
        self.blog_id = blog_id


    def __str__(self):
        return self.text


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        userDetails = request.form
        name = userDetails['name']
        email = userDetails['email']
        password = userDetails['password']

        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM korisnici3 WHERE name='"+name+"'")
        duplikat = cur.fetchone()

        if duplikat:
            return render_template("register.html",msg="to ime je već zauzeto")
        else:
            cur.execute('INSERT INTO korisnici3(name, email, password) VALUES(%s, %s, %s)',(name, email, password))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login'))
    else:
        return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg=""
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        # Fetch form data
        userDetails = request.form
        name = userDetails['name']
        password = userDetails['password']
        cur.execute('SELECT * FROM korisnici3 WHERE name=%s AND password=%s',(name, password)) # TODO: store hash intead plain password
        record = cur.fetchone()

        if record:
            session['loggedin']=True # TODO: napravi svoju sessiju
            session['username']=record[1]
            return redirect(url_for('home'))
        else:
            return render_template("login.html", msg="pogrešni podaci, pokušajte ponovo")
    return render_template('login.html')




@app.route('/lista_korisnika')
def lista_korisnika():
    cur = mysql.connect.cursor()
    values = cur.execute('SELECT * FROM korisnici3')
    if values > 0:
        details = cur.fetchall()
        return render_template('lista_korisnika.html', maslina = details)


@app.route('/<id>/detail_user')
def detail_korisnika(id):
    cur = mysql.connect.cursor()
    details = cur.execute("SELECT * FROM korisnici3 WHERE ID='"+id+"'")
    korisnik = cur.fetchall()
    return render_template('detail_korisnik.html', korisnik=korisnik)


@app.route('/<id>/user_delete', methods=['POST', 'GET'])
def user_delete(id):
    ID = id
    return redirect(url_for('user_delete_confirm', id=ID))

@app.route('/<id>/user_delete_confirm', methods=['POST', 'GET'])
def user_delete_confirm(id):
    if request.method == 'POST':
        ID = id
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM korisnici3 WHERE ID='"+id+"'")
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('lista_korisnika'))
    return render_template('korisnik_delete_confirm.html')


@app.route('/<id>/nova_sifra', methods=['POST','GET'])
def nova_sifra(id):
    cur = mysql.connection.cursor()
    korisnici = cur.execute("SELECT * FROM korisnici3 WHERE ID='"+id+"'")
    korisnik = cur.fetchone()
    if request.method == 'POST':
        nova_sifra = request.form['ns']
        cur.execute("UPDATE korisnici3 SET password='"+nova_sifra+"' WHERE ID='"+id+"'")
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('lista_korisnika'))

    return render_template('nova_sifra.html', sifra=korisnik)



@app.route('/kreiraj_post', methods=['POST', 'GET'])
def create():
    if request.method == 'POST':
        naslov = request.form['naslov']
        tekst = request.form['tekst']
        autor = request.form['autor']
        odobren = False
        clanak = post(naslov, tekst, autor, odobren)
        db.session.add(clanak)
        db.session.commit()
        return redirect(url_for('lista_postova'))
    else:
        return render_template('create.html')


@app.route('/<id>/odobri_post', methods=['POST', 'GET'])
def odobri_post(id):
    post_odobri = post.query.get(id)
    post_odobri.odobren = True
    db.session.commit()
    return redirect(url_for('lista_postova'))


@app.route('/lista_postova')
def lista_postova():
    return render_template('lista_postova.html',  values=post.query.filter_by(odobren=True).all())


@app.route('/lista_draftova')
def lista_draftova():
    return render_template('lista_draftova.html',  values=post.query.filter_by(odobren=False).all())


@app.route('/<id>', methods=['POST', 'GET'])
def detail_post(id):
    return render_template('detail_page.html', detail=post.query.filter_by(_id=id))


@app.route('/<id>/delete', methods=['POST', 'GET'])
def delete(id):
    return render_template('confirm_delete.html', got=post.query.filter_by(_id=id))

@app.route('/<id>/delete_confirm', methods=['POST', 'GET'])
def delete_confirm(id):
    postd = post.query.get(id)
    komentari = comment.query.filter_by(blog_id=id)
    komentari.delete()
    db.session.delete(postd)
    db.session.commit()
    return redirect(url_for('lista_postova'))

@app.route('/<id>/edit', methods=['POST', 'GET'])
def edit(id):
    if request.method == 'POST':
        naslov = request.form['naslov']
        tekst = request.form['tekst']
        post_edit = post.query.get(id)
        post_edit.title = naslov
        post_edit.text = tekst
        db.session.commit()


        return redirect(url_for('lista_postova'))
    else:
        return render_template('edit.html', edit=post.query.filter_by(_id=id))


@app.route('/<id>/komentar', methods=['POST', 'GET'])
def komentarisi(id):
    if request.method == 'POST':

        tekst = request.form['kom']
        autor = request.form['aut']
        komentar = comment(tekst, autor, blog_id=id)
        db.session.commit()
        maslina = post.query.filter_by(_id=id).first()
        maslina.comments.append(komentar)
        db.session.commit()

        return redirect(url_for('lista_postova'))
    else:
        return render_template('komentar.html', maslina=post.query.filter_by(_id=id))

@app.route('/<id>/obrisi_komentar', methods=['POST', 'GET'])
def obrisi_komentar(id):
    komentard = comment.query.get(id)
    db.session.delete(komentard)
    db.session.commit()
    return redirect(url_for('lista_postova'))


@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return render_template("logout.html")



if __name__ == '__main__':
    app.debug = True
    db.create_all()
    app.run()
