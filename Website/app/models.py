from app import db


class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    administrator = db.Column(db.Boolean(), index=True)
    entries = db.relationship('LogbookEntries', backref='author')

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)  # python 3

    def __repr__(self):
        return '<User %r>' % self.name


class LogbookEntries(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime)
    stop = db.Column(db.DateTime)
    isotope = db.Column(db.String(64))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Scan %r>' % self.start
