from app import db, models
import datetime
import time

u = models.User(name='Admin', administrator=True)
db.session.add(u)
u = models.User(name='Wouter', administrator=False)
db.session.add(u)

u = models.User.query.get(2)
first = datetime.datetime.utcnow()
time.sleep(2)
second = datetime.datetime.utcnow()

p = models.LogbookEntries(start=first, stop=second, isotope='212Fr', author=u)
db.session.add(p)
db.session.commit()
