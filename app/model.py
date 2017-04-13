from database import db, bcrypt, login_manager

@login_manager.user_loader
def load_user(userid):
    return User.query.filter(User.id==userid).first()

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    googleAccessToken = db.Column(db.String(256), unique=True)
    googleRefreshToken = db.Column(db.String(256), unique=True)
    googleTokenExpiry = db.Column(db.String(128))
    googleTokenURI    = db.Column(db.String(128))
    googleRevokeURI   = db.Column(db.String(128))
    googleSheetAccess = db.Column(db.Boolean)
    splitwiseToken = db.Column(db.String(256), unique=True)
    splitwiseTokenSecret = db.Column(db.String(256))
    splitwiseAccess = db.Column(db.Boolean)
    sheets = db.relationship('Sheet', backref='user',
                                lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.email

    def save(self):
        db.session.add(self)
        db.session.commit()

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

class Sheet(db.Model):

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sheetName = db.Column(db.String(256), nullable=False)
    sheetId = db.Column(db.String(256), nullable=False)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return '<Sheet User %r  SheetName %r>' % self.user_id+" "+sheetName
