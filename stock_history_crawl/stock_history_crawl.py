#!/usr/bin/python

__author__ = 'zxzhang'
import urllib2

stock_list = \
[
    'DGAZ',
    'UGAZ',
    'UCO',
    'SCO',
    'CHK',
    'TOT',
    'SLB',
    'BABA',
    'BIDU',
    'JD',
    'CTRP',
    'QUNR',
    'YY',
    'DANG',
    'FB',
    'GOOG',
    'AMZN',
    'AAPL',
    'NFLX',
    'MSFT',
    'TSLA',
]

url_parten = 'http://real-chart.finance.yahoo.com/table.csv?s=%1%&d=5&e=19&f=2015&g=d&a=0&b=2&c=1962&ignore=.csv'
file_path_parten = '/Users/zxzhang/stock/data/%1%.csv'

for s in stock_list:
    url = url_parten.replace('%1%', s)
    data = urllib2.urlopen(url)
    file_path = file_path_parten.replace('%1%', s)
    with open(file_path, "w") as f:
        f.write(data.read())
        print "done with:" + file_path

print"done!"