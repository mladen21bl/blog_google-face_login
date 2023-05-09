import flask
from flask import Flask, render_template, flash, request, redirect, url_for, abort, flash, session, make_response
from datetime import timedelta
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
import cachecontrol
import secrets
import pathlib
from googleapiclient.discovery import build
import facebook
import requests
import yaml
from flask_wtf import FlaskForm
from datetime import timedelta
from oauthlib.oauth2 import BackendApplicationClient
from flask_login import login_user, logout_user, login_required, current_user
import pickle
from flask_sqlalchemy import SQLAlchemy
import uuid
import time
from bottle import run, get
from google.oauth2 import id_token
from requests_oauthlib import OAuth2Session
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import requests_oauthlib
import google.auth.transport.requests
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from requests_oauthlib.compliance_fixes import facebook_compliance_fix

app = Flask(__name__)
mysql = MySQL(app)

db = yaml.safe_load(open('db.yaml'))

app.secret_key = os.environ.get("FLASK_SECRET_KEY", default=os.urandom(16))
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

sessions = {}


@app.route('/')
def home():
    session_id = request.cookies.get('session_id')
    return render_template('index.html', session_id=session_id, sessions=sessions)

############## SESSION #####################
# Define a function to create a new session
# create a new session


###############################################

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        userDetails = request.form
        name = userDetails['name']
        email = userDetails['email']
        password = userDetails['password']

        hash = generate_password_hash(password)

        cur = mysql.connection.cursor()

        cur.execute("SELECT * FROM korisnici00 WHERE name='"+name+"'")
        duplikat = cur.fetchone()
        if duplikat:
            return render_template("register.html",msg="to ime je već zauzeto")
        else:
            cur.execute('INSERT INTO korisnici00(name, email, password) VALUES(%s, %s, %s)',(name, email, hash))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('login'))
    else:
        return render_template("register.html")

    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ""
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        userDetails = request.form
        name = userDetails['name']
        password = userDetails['password']

        cur.execute("SELECT * FROM korisnici00 WHERE name='"+name+"'")
        record = cur.fetchone()
        hash = record[3]

        if record and check_password_hash(password=password,pwhash=hash):
            # generate a unique session ID
            session_id = str(uuid.uuid4())
            sessions[session_id] = {
            "loggedin": True,
            "username": record[1]
                }
            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('session_id', session_id)
            resp.set_cookie('username', sessions[session_id]['username'])
            return resp

        else:
            return render_template("login.html", msg="pogrešni podaci, pokušajte ponovo")

    return render_template('login.html')



@app.route('/lista_korisnika')
def lista_korisnika():
    cur = mysql.connect.cursor()
    values = cur.execute('SELECT * FROM korisnici00')
    if values > 0:
        details = cur.fetchall()
        return render_template('lista_korisnika.html', maslina = details)


@app.route('/<id>/detail_user')
def detail_korisnika(id):
    cur = mysql.connect.cursor()
    details = cur.execute("SELECT * FROM korisnici00 WHERE ID='"+id+"'")
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
        cur.execute("DELETE FROM korisnici00 WHERE ID='"+id+"'")
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('lista_korisnika'))
    return render_template('korisnik_delete_confirm.html')


@app.route('/<id>/nova_sifra', methods=['POST','GET'])
def nova_sifra(id):
    cur = mysql.connection.cursor()
    korisnici = cur.execute("SELECT * FROM korisnici00 WHERE ID='"+id+"'")
    korisnik = cur.fetchone()
    if request.method == 'POST':
        nova_sifra = request.form['ns']
        hash = generate_password_hash(nova_sifra)
        cur.execute("UPDATE korisnici00 SET password=\""+hash+"\" WHERE ID=\""+id+"\"")
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








############### FACEBOOK LOGIN ######################

load_dotenv()
URL = "http://localhost:3000"

# Facebook Config
FB_CLIENT_ID ="612584297188570"
FB_CLIENT_SECRET ="fe0eb48657f1531f21a69e8ce7f12d28"

FB_AUTHORIZATION_BASE_URL = "https://www.facebook.com/dialog/oauth"
FB_TOKEN_URL = "https://graph.facebook.com/oauth/access_token"

FB_SCOPE = ["email"]

# This allows us to use a plain HTTP callback
# <<< SimpleLogin endpoints >>>

# <<< Facebook endpoints >>>
@app.route("/fb-login")
def fb_login():
    facebook = requests_oauthlib.OAuth2Session(
        FB_CLIENT_ID, redirect_uri=URL + "/fb-callback", scope=FB_SCOPE
    )
    authorization_url, _ = facebook.authorization_url(FB_AUTHORIZATION_BASE_URL)
    return flask.redirect(authorization_url)

@app.route("/fb-callback")
def fb_callback():
    facebook = requests_oauthlib.OAuth2Session(
        FB_CLIENT_ID, scope=FB_SCOPE, redirect_uri=URL + "/fb-callback"
    )

    # we need to apply a fix for Facebook here
    facebook = facebook_compliance_fix(facebook)

    facebook.fetch_token(
        FB_TOKEN_URL,
        client_secret=FB_CLIENT_SECRET,
        authorization_response=URL + flask.request.full_path,
    )

    # Fetch a protected resource, i.e. user profile, via Graph API

    facebook_user_data = facebook.get("https://graph.facebook.com/me?fields=id,name").json()

    username = facebook_user_data["name"]
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
    "loggedin": True,
    "username": username
        }
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('session_id', session_id)
    resp.set_cookie('username', sessions[session_id]['username'])
    return resp




##############################################################
##### GOOGLE LOGIN ######
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = "964596711171-6l0osr3ma9cfi2mptjlcqj5gm0pong9n.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://localhost:3000/callback"
)




@app.route("/google_login")
def google_login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state  # Set the state parameter in the session
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    # Check that the state parameter returned by the authorization server matches the value in the session
    if "state" not in session or session["state"] != request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=1,
    )

    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "loggedin": True,
        "username": id_info.get("name")
    }
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('session_id', session_id)
    resp.set_cookie('username', sessions[session_id]['username'])
    return resp






#############################################################
@app.route('/logout')
def logout():
    session_id = request.cookies.get('session_id')
    if session_id in sessions:
        del sessions[session_id]
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('session_id', '', expires=0)
    resp.set_cookie('username', '', expires=0)
    return resp

#############################################################
if __name__ == '__main__':
    app.debug = True
    db.create_all()
    app.run(port=3000)
