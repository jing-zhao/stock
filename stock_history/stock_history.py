#!/usr/bin/python

from datetime import datetime
from datetime import timedelta

class DailyStockPrice(object):
    def __init__(self, open, high, low, close):
        self.open = float(open)
        self.close = float(close)
        self.high = float(high)
        self.low = float(low)

    def to_str(self):
        return '%.2f,%.2f,%.2f,%.2f'%(self.open, self.high, self.low, self.close)

    def is_active(self, threshold):
        return (self.high - self.low) / self.low > threshold

class StockPriceHistory(object):
    FLUCTUATION_PERCENTAGE_THRESHOLD = 0.1
    
    def __init__(self, daily_price_list, date_to_daily_index_dict, str_start_date, str_end_date):
        self.daily_price_list = daily_price_list
        self.fluctuation_count_list = []
        self.date_to_daily_index_dict = date_to_daily_index_dict
        self.start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(str_end_date, "%Y-%m-%d")
        self._populate_fluctuation_counts()
        self._debug_print()

    def _debug_print(self):
        for key in self.date_to_daily_index_dict:
            print key.strftime("%Y-%m-%d") + ',' + self.daily_price_list[self.date_to_daily_index_dict[key]].to_str()
        print "fluctuation_counts:" + ', '.join(str(i) for i in self.fluctuation_count_list)

    def _populate_fluctuation_counts(self):
        if not self.daily_price_list:
            return

        prev_base_price = self.daily_price_list[0].open
        fluctuation_signal_list = []

        for daily_price in self.daily_price_list:
            prev_base_price, count1 = self._process_one_price(prev_base_price, daily_price.open, fluctuation_signal_list)
            prev_base_price, count2 = self._process_one_price(prev_base_price, daily_price.close, fluctuation_signal_list)
            if not self.fluctuation_count_list:
                self.fluctuation_count_list.append(count1 + count2)
            else:
                self.fluctuation_count_list.append(count1 + count2 + self.fluctuation_count_list[-1])
            
    
    def _process_one_price(self, prev_base_price, cur_price, fluctuation_signal_list):
        if abs(cur_price - prev_base_price) / prev_base_price < self.FLUCTUATION_PERCENTAGE_THRESHOLD:
            return (prev_base_price, 0)

        signal = True if cur_price > prev_base_price else False
        count = 0
        while abs(cur_price - prev_base_price) / prev_base_price >= self.FLUCTUATION_PERCENTAGE_THRESHOLD:
            if signal:
                prev_base_price = prev_base_price * (1 + self.FLUCTUATION_PERCENTAGE_THRESHOLD)
            else:
                prev_base_price = prev_base_price * (1 - self.FLUCTUATION_PERCENTAGE_THRESHOLD)

            if not fluctuation_signal_list or fluctuation_signal_list[-1] == signal:
                fluctuation_signal_list.append(signal)
            else:
                fluctuation_signal_list.pop()
                count = count + 1
        print 'new base:' + str(prev_base_price) + ' count: ' + str(count) + ' sig: ' + ','.join(str(b) for b in fluctuation_signal_list)
        return prev_base_price, count

    @classmethod
    def load(cls, file_path):
        daily_price_list = []
        date_to_daily_index_dict = {}
        first_date = None
        last_date = None
        with open(file_path, "r") as lines:
            lines.readline()
            lines = lines.readlines()
            lines.reverse()
            for line in lines:
                cols = line.split(',')
                #Date	Open	High	Low	Close	Volume	Adj Close
                daily_price_list.append(DailyStockPrice(cols[1], cols[2], cols[3], cols[4]))
                date_to_daily_index_dict[datetime.strptime(cols[0], "%Y-%m-%d")] = len(daily_price_list) - 1

                if not first_date:
                    first_date = cols[0]
                last_date = cols[0]

        return StockPriceHistory(daily_price_list, date_to_daily_index_dict, first_date, last_date)
    
    def fluctuation_count(self, end_date, window_size=None):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        return self.fluctuation_count_list[last_date_index] - self.fluctuation_count_list[first_date_index]

    def _get_start_and_end_index(self, end_date, window_size):
        end_date = datetime(end_date.year, end_date.month, end_date.day)
        while end_date not in self.date_to_daily_index_dict and end_date >= self.start_date:
            end_date = end_date - timedelta(days=1)
        if end_date < self.start_date:
            return -1, -1
        end_date_index = self.date_to_daily_index_dict[end_date]
        start_date_index = 0 if not window_size or (end_date_index - window_size) < 0 else (end_date_index - window_size)

        return start_date_index, end_date_index

    def active_day_count(self, end_date, window_size=None, threshhold=0.05):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        count = 0
        for i in range(first_date_index, last_date_index + 1):
            if self.daily_price_list[i].is_active(threshhold):
                count = count + 1
        return count

    

StockPriceHistory.FLUCTUATION_PERCENTAGE_THRESHOLD = 0.05
stock = StockPriceHistory.load('/Users/zxzhang/stock/data/YY.csv')
print 'fluctuation count:' + str(stock.fluctuation_count(datetime.today(), 90))
print 'active day count:' + str(stock.active_day_count(datetime.today(), 90))
