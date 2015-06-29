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

    BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE = 0.5
    BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE = 0.2
    BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE = 0.3
    BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE = 0.3

    THRESHOLD_DAY_ACTIVZE = 0.05
    THRESHOLD_FLUCTUATION = 0.1

    def __init__(self, daily_price_list, date_to_daily_index_dict, str_start_date, str_end_date):
        self.daily_price_list = daily_price_list
        self.fluctuation_count_list = []
        self.date_to_daily_index_dict = date_to_daily_index_dict
        self.start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(str_end_date, "%Y-%m-%d")

        self._debug_print()

    def _debug_print(self):
        for key in self.date_to_daily_index_dict:
            print key.strftime("%Y-%m-%d") + ',' + self.daily_price_list[self.date_to_daily_index_dict[key]].to_str()

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

        print "fluctuation_counts:" + ', '.join(str(i) for i in self.fluctuation_count_list)

    
    def _process_one_price(self, prev_base_price, cur_price, fluctuation_signal_list):
        if abs(cur_price - prev_base_price) / prev_base_price < self.THRESHOLD_FLUCTUATION:
            return (prev_base_price, 0)

        signal = True if cur_price > prev_base_price else False
        count = 0
        while abs(cur_price - prev_base_price) / prev_base_price >= self.THRESHOLD_FLUCTUATION:
            if signal:
                prev_base_price = prev_base_price * (1 + self.THRESHOLD_FLUCTUATION)
            else:
                prev_base_price = prev_base_price * (1 - self.THRESHOLD_FLUCTUATION)

            if not fluctuation_signal_list or fluctuation_signal_list[-1] == signal:
                fluctuation_signal_list.append(signal)
            else:
                fluctuation_signal_list.pop()
                count = count + 1
        #iihlkhbjldfdfltlrlcefjtgehekidfuprint 'new base:' + str(prev_base_price) + ' count: ' + str(count) + ' sig: ' + ','.join(str(b) for b in fluctuation_signal_list)
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
    
    def fluctuation_percentile(self, end_date, window_size=90):
        self._populate_fluctuation_counts()
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        return float(
            self.fluctuation_count_list[last_date_index] - self.fluctuation_count_list[first_date_index]) / \
               (last_date_index - first_date_index + 1)



    def _get_start_and_end_index(self, end_date, window_size):
        end_date = datetime(end_date.year, end_date.month, end_date.day)
        while end_date not in self.date_to_daily_index_dict and end_date >= self.start_date:
            end_date = end_date - timedelta(days=1)
        if end_date < self.start_date:
            return -1, -1
        end_date_index = self.date_to_daily_index_dict[end_date]
        start_date_index = 0 if not window_size or (end_date_index - window_size) < 0 else (end_date_index - window_size)

        return start_date_index, end_date_index

    def active_day_count_percentile(self, end_date, window_size=None):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        count = 0.0
        for i in range(first_date_index, last_date_index + 1):
            if self.daily_price_list[i].is_active(self.THRESHOLD_DAY_ACTIVZE):
                count = count + 1
        return count / (last_date_index - first_date_index + 1)

    def end_price_percentile(self, end_date, window_size=None):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        max = 0.0
        min = 1000000.0
        for i in range(first_date_index, last_date_index + 1):
            if self.daily_price_list[i].high > max:
                max = self.daily_price_list[i].high
            if self.daily_price_list[i].low < min:
                min = self.daily_price_list[i].low
        return (self.daily_price_list[last_date_index].close - min) / (max-min)

    def price_down_percentile(self, end_date, window_size=30):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        down_count = 0.0
        for i in range(first_date_index + 1, last_date_index + 1):
            if self.daily_price_list[i].close < self.daily_price_list[i - 1].close:
                down_count = down_count + 1
        return down_count / (last_date_index - first_date_index)


    def is_buy_point(self, end_date):

        print 'fluctuation_percentile: ' + str(self.fluctuation_percentile(end_date, 90))
        print 'active day percentile: ' + str(self.active_day_count_percentile(end_date, 90))
        print 'end price percentile: ' + str(self.end_price_percentile(end_date, 90))
        print 'price_down_precentile: ' + str(self.price_down_percentile(end_date, 30))

        return self.price_down_percentile(end_date, 30) <= self.BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE and \
           self.end_price_percentile(end_date, 90) <= self.BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE and \
           self.active_day_count_percentile(end_date, 90) >= self.BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE and \
           self.fluctuation_percentile(end_date, 90) >= self.BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE



stock = StockPriceHistory.load('/Users/zxzhang/stock/data/BABA1.csv')
print 'is_buy_point: ' + str(stock.is_buy_point(datetime.today()))