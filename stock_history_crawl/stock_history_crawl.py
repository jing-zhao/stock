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

url_parten = 'http://real-chart.finance.yahoo.com/table.csv?s=%1%&d=5&e=19&f=2025&g=d&a=0&b=2&c=1962&ignore=.csv'
file_path_parten = '/Users/zxzhang/stock/data/%1%.csv'

url_parten2 = 'http://ichart.finance.yahoo.com/x?s=%1%&a=00&b=2&c=1962&d=04&e=25&f=2025&g=v&y=0&z=30000'
file_path_parten2 = '/Users/zxzhang/stock/data/%1%_split.csv'

def do_crawl(url_parten, file_path_parten):
    for s in stock_list:
        url = url_parten.replace('%1%', s)
        data = urllib2.urlopen(url)
        file_path = file_path_parten.replace('%1%', s)
        with open(file_path, "w") as f:
            f.write(data.read())
            print "done with:" + file_path

do_crawl(url_parten, file_path_parten)
do_crawl(url_parten2, file_path_parten2)

print"done!"