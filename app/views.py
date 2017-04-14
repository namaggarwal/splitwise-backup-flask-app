from flask import Blueprint, render_template, redirect, session, url_for, request, flash, current_app as app
from model import User
from flask_login import login_required, login_user, current_user
from oauth2client import client
from googlesheets import GoogleSheet
from splitwise import Splitwise
import datetime
import httplib2
import json
import utils

pages = Blueprint('pages', __name__,template_folder='templates')

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

    flow.params['include_granted_scopes'] = "true"
    flow.params['access_type'] = 'offline'

    if 'code' not in request.args:
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)
    else:
        auth_code = request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        credentials = json.loads(credentials.to_json())
        email = credentials["id_token"]["email"]
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email)
            user.googleAccessToken  = credentials["access_token"]
            user.googleRefreshToken = credentials["refresh_token"]
            user.googleTokenExpiry  = credentials["token_expiry"]
            user.googleTokenURI     = credentials["token_uri"]
            user.googleRevokeURI    = credentials["revoke_uri"]
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

    flow.params['include_granted_scopes'] = "true"
    flow.params['access_type'] = 'offline'

    if 'code' not in request.args:
        app.logger.debug("User "+current_user.email+" trying to provide spreadsheet access")
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)
    else:
        auth_code = request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        credentials = json.loads(credentials.to_json())

        user = current_user
        user.googleAccessToken  = credentials["access_token"]
        user.googleRefreshToken = credentials["refresh_token"]
        user.googleTokenExpiry  = credentials["token_expiry"]
        user.googleTokenURI     = credentials["token_uri"]
        user.googleRevokeURI    = credentials["revoke_uri"]
        user.googleSheetAccess = True
        user.save()
        app.logger.debug("User "+user.email+" provided spreadsheet access")
        return redirect(url_for('pages.home'))


@pages.route("/login/splitwise")
@login_required
def splitwiseLogin():
    if 'oauth_token' not in request.args or 'oauth_verifier' not in request.args:
        app.logger.debug("User "+current_user.email+" trying to provide splitwise access")
        sObj = Splitwise(app.config["SPLITWISE_CONSUMER_KEY"],app.config["SPLITWISE_CONSUMER_SECRET"])
        url, secret = sObj.getAuthorizeURL()
        session['splitwisesecret'] = secret
        return redirect(url)

    else:
        oauth_token    = request.args.get('oauth_token')
        oauth_verifier = request.args.get('oauth_verifier')
        sObj = Splitwise(app.config["SPLITWISE_CONSUMER_KEY"],app.config["SPLITWISE_CONSUMER_SECRET"])
        access_token = sObj.getAccessToken(oauth_token,session['splitwisesecret'],oauth_verifier)
        user = current_user
        user.splitwiseToken = access_token["oauth_token"]
        user.splitwiseTokenSecret = access_token["oauth_token_secret"]
        user.splitwiseAccess = True
        user.save()
        app.logger.debug("User "+user.email+" provided splitwise access")
        return redirect(url_for('pages.home'))
