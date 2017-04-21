import os
from flask import Flask, render_template
from router import db, bcrypt, login_manager
from views import pages
from apscheduler.schedulers.background import BackgroundScheduler
from backupscheduler import backupData
from logger import Logger
from flask_migrate import Migrate
from werkzeug.wsgi import DispatcherMiddleware


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')

if os.path.exists("instance/config.py"):
    app.config.from_pyfile('config.py')

if os.environ.get('APP_CONFIG_FILE', None):
    app.config.from_envvar('APP_CONFIG_FILE')


### Flask Configurations ####
app.secret_key = app.config["FLASK_SECRET_KEY"]

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {app.config["APPLICATION_ROOT"]:app.wsgi_app})

### SQL Alchemy Configurations ####
app.config['SQLALCHEMY_DATABASE_URI'] = app.config["DATABASE_URI"]
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]
db.init_app(app)

#### Login Manager Configurations ####
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view =  "pages.login"

### Bcrypt Configurations ###
bcrypt.init_app(app)

### Blueprints Configuration ###
app.register_blueprint(pages)


### Add Logging ###
app.logger.addHandler(Logger.getAppHandler())

### Migration ###
migrate = Migrate(app, db)


### Error Handlers ###
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html',errorcode=404), 404

@app.errorhandler(500)
def error_request(e):
    return render_template('error.html',errorcode=500), 500

### Backup ####
@app.before_first_request
def initialize():
    scheduler = BackgroundScheduler()
    scheduler.add_job(backupData, 'interval', minutes=2, args=[app])
    scheduler.start()
