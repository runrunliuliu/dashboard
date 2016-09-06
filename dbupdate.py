import requests
import sqlite3
import time

conn = sqlite3.connect('/home/himalayas/apps/webserver/dashboard/data-dev.sqlite')

def upNowPrice():
    c = conn.cursor()
    c.execute("select * from holds where status != 3")
    stocks    = set()
    id_stocks = []

    for line in c.fetchall():
        id_stocks.append((line[0], line[1]))
        stocks.add(line[1])

    id_nprice = dict()
    for s in stocks:
        url = 'http://api.quchaogu.com/stock/batchinfo?code=' + s.strip()
        r   = requests.get(url)
        js  =  r.json()
        id_nprice[s] = js['data'][0]['price']

    for item in id_stocks:
       p = id_nprice[item[1]]
       sql = 'UPDATE holds SET nprice = ' + str(p) + ' WHERE ID = ' + str(item[0])
       c.execute(sql)
    conn.commit()

while True:
    upNowPrice()
    print 'Update Price is DONE! Sleep 60s'
    time.sleep(60)
conn.close()
