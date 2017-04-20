from flask import Blueprint, render_template, redirect, session, url_for, request, flash, abort, current_app as app
from model import User
from flask_login import login_required, login_user, current_user
from oauth2client import client
from googlesheets import GoogleSheet
from splitwise import Splitwise
from router import bcrypt
import datetime
import httplib2
import json
import utils

pages = Blueprint('pages', __name__,template_folder='templates')

#### String Constants ####
INCLUDE_GRANTED_SCOPES = "include_granted_scopes"
ACCESS_TYPE = "access_type"
GOOGLE_SECRET = "google_secret"
GOOGLE_CODE = "code"
GOOGLE_ID_TOKEN = "id_token"
GOOGLE_EMAIL = "email"
GOOGLE_ACCESS_TOKEN = "access_token"
GOOGLE_REFRESH_TOKEN = "refresh_token"
GOOGLE_TOKEN_EXPIRY = "token_expiry"
GOOGLE_TOKEN_URI = "token_uri"
GOOGLE_REVOKE_URI = "revoke_uri"
SPLITWISE_SECRET = "splitwise_secret"
SPLITWISE_OAUTH_TOKEN = "oauth_token"
SPLITWISE_OAUTH_VERIFIER = "oauth_verifier"
SPLITWISE_OAUTH_TOKEN_SECRET = "oauth_token_secret"

@pages.route("/")
@login_required
def home():
    app.logger.debug("User "+current_user.email+" logged in")
    lastBackupTime = "Will backup soon"
    if current_user.lastBackupTime:
        lastBackupTime = utils.datetimeToHumanString(current_user.lastBackupTime)
    return render_template("home.html",lastBackupTime=lastBackupTime)

@pages.route("/login")
def login():
    return render_template("login.html")


@pages.route("/login/google")
def googleLogin():
    flow = client.OAuth2WebServerFlow(client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    scope='email',
    redirect_uri=url_for('pages.googleLogin', _external=True))

    flow.params[INCLUDE_GRANTED_SCOPES] = "true"
    flow.params[ACCESS_TYPE] = 'offline'

    if GOOGLE_CODE not in request.args:
        auth_uri = flow.step1_get_authorize_url()
        session[GOOGLE_SECRET] = bcrypt.generate_password_hash(app.config["FLASK_SECRET_KEY"])
        return redirect(auth_uri)
    else:
        if not bcrypt.check_password_hash(session[GOOGLE_SECRET], app.config["FLASK_SECRET_KEY"]):
            abort(500)
        auth_code = request.args.get(GOOGLE_CODE)
        credentials = flow.step2_exchange(auth_code)
        credentials = json.loads(credentials.to_json())
        email = credentials[GOOGLE_ID_TOKEN][GOOGLE_EMAIL]
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            user.googleAccessToken  = credentials[GOOGLE_ACCESS_TOKEN]
            user.googleRefreshToken = credentials[GOOGLE_REFRESH_TOKEN]
            user.googleTokenExpiry  = credentials[GOOGLE_TOKEN_EXPIRY]
            user.googleTokenURI     = credentials[GOOGLE_TOKEN_URI]
            user.googleRevokeURI    = credentials[GOOGLE_REVOKE_URI]
            user.googleSheetAccess=False
            user.save()
        login_user(user)
        app.logger.debug("User "+email+" logged in to google")
        return redirect(url_for('pages.home'))


@pages.route("/login/google/spreadsheets")
@login_required
def googleSpreadsheetLogin():
    flow = client.OAuth2WebServerFlow(client_id=app.config["GOOGLE_CLIENT_ID"],
    client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    scope='https://www.googleapis.com/auth/spreadsheets',
    redirect_uri=url_for('pages.googleSpreadsheetLogin', _external=True))

    flow.params[INCLUDE_GRANTED_SCOPES] = "true"
    flow.params[ACCESS_TYPE] = 'offline'

    if GOOGLE_CODE not in request.args:
        app.logger.debug("User "+current_user.email+" trying to provide spreadsheet access")
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)
    else:
        auth_code = request.args.get(GOOGLE_CODE)
        credentials = flow.step2_exchange(auth_code)
        credentials = json.loads(credentials.to_json())

        user = current_user
        user.googleAccessToken  = credentials[GOOGLE_ACCESS_TOKEN]
        user.googleRefreshToken = credentials[GOOGLE_REFRESH_TOKEN]
        user.googleTokenExpiry  = credentials[GOOGLE_TOKEN_EXPIRY]
        user.googleTokenURI     = credentials[GOOGLE_TOKEN_URI]
        user.googleRevokeURI    = credentials[GOOGLE_REVOKE_URI]
        user.googleSheetAccess = True
        user.save()
        app.logger.debug("User "+user.email+" provided spreadsheet access")
        return redirect(url_for('pages.home'))


@pages.route("/login/splitwise")
@login_required
def splitwiseLogin():
    if SPLITWISE_OAUTH_TOKEN not in request.args or SPLITWISE_OAUTH_VERIFIER not in request.args:
        app.logger.debug("User "+current_user.email+" trying to provide splitwise access")
        sObj = Splitwise(app.config["SPLITWISE_CONSUMER_KEY"],app.config["SPLITWISE_CONSUMER_SECRET"])
        url, secret = sObj.getAuthorizeURL()
        session[SPLITWISE_SECRET] = secret
        return redirect(url)

    else:
        oauth_token    = request.args.get(SPLITWISE_OAUTH_TOKEN)
        oauth_verifier = request.args.get(SPLITWISE_OAUTH_VERIFIER)
        sObj = Splitwise(app.config["SPLITWISE_CONSUMER_KEY"],app.config["SPLITWISE_CONSUMER_SECRET"])
        access_token = sObj.getAccessToken(oauth_token,session[SPLITWISE_SECRET],oauth_verifier)
        user = current_user
        user.splitwiseToken = access_token[SPLITWISE_OAUTH_TOKEN]
        user.splitwiseTokenSecret = access_token[SPLITWISE_OAUTH_TOKEN_SECRET]
        user.splitwiseAccess = True
        user.save()
        app.logger.debug("User "+user.email+" provided splitwise access")
        return redirect(url_for('pages.home'))
