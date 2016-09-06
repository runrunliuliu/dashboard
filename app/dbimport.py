
from sqlalchemy.exc import IntegrityError

for line in open('/home/himalayas/apps/opt/pytrade-3.0.1/data/stockinfo.csv'):
    arr = line.split(',')
    f = Stock(stockid   = arr[1],
             stockname  = arr[2].decode('utf8'),
             hangye     = arr[3],)
    db.session.add(f)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
