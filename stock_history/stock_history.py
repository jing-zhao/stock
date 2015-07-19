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
    THRESHOLD_FLUCTUATION = 0.05

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
        signal = True if cur_price > prev_base_price else False
        threshold = self.THRESHOLD_FLUCTUATION
        if not signal:
            threshold = threshold / (1 + threshold)

        if abs(cur_price - prev_base_price) / prev_base_price < threshold:
            return (prev_base_price, 0)

        count = 0
        while abs(cur_price - prev_base_price) / prev_base_price >= threshold:
            if signal:
                prev_base_price = prev_base_price * (1 + threshold)
            else:
                prev_base_price = prev_base_price * (1 - threshold)

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
        with open(file_path, "r") as fs:
            fs.readline()
            lines = fs.readlines()
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



    def _get_start_and_end_index(self, end_date, window_size=None):
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
        min = 1000000000.0
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

        fluctuation_percentile = self.fluctuation_percentile(end_date, 90)
        active_day_percentile = self.active_day_count_percentile(end_date, 90)
        end_price_percentile = self.end_price_percentile(end_date, 90)
        price_down_precentile = self.price_down_percentile(end_date, 30)

        print 'fluctuation_percentile: ' + str(fluctuation_percentile) + \
              ' PassValue: >=' + str(self.BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE)
        print 'active day percentile: ' + str(active_day_percentile) + \
              ' PassValue: >=' + str(self.BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE)
        print 'end price percentile: ' + str(end_price_percentile) + \
              ' PassValue: <=' + str(self.BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE)
        print 'price_down_precentile: ' + str(price_down_precentile) + \
              ' PassValue: <=' + str(self.BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE)

        return fluctuation_percentile >= self.BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE and \
               active_day_percentile >= self.BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE and \
               end_price_percentile <=  self.BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE and \
               price_down_precentile <= self.BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE

    def get_previous_close_price(self, start_date):
        _, last_date_index = self._get_start_and_end_index(start_date, 90)
        return self.daily_price_list[last_date_index].close

    def is_market_open(self, the_day):
        return the_day in self.date_to_daily_index_dict

    def get_stock_price(self, the_day):
        if self.is_market_open(the_day):
            return self.daily_price_list[self.date_to_daily_index_dict[the_day]]
        raise "Error"


class Order(object):
    def __init__(self, amount, price):

        self.amount = amount
        self.price = price

class TransactionSimulator(object):

    def __init__(self, stock_symbol):

        self.stock_price_history = StockPriceHistory.load('/Users/zxzhang/stock/data/' + stock_symbol + '.csv')
        self.stock_symbol = stock_symbol
        self.position = 0
        self.cost = 0.0
        self.cash = 1000000.0
        self.buy_orders = []
        self.sell_orders = []
        self.start_amount = None

    def _get_account_value(self, the_day):
        return self.cash + self.position * self.stock_price_history.get_stock_price(the_day).close

    def deal_buy(self, amount, order_price, deal_price):
        print "buy: amount: " + str(amount) + "deal_price: " + str(deal_price)

        self.position = self.position + amount
        self.cost = self.cost + amount * deal_price
        self.cash = self.cash - amount * deal_price
        self.sell_orders.append(Order(amount, order_price * (1 + StockPriceHistory.THRESHOLD_FLUCTUATION)))

    def deal_sell(self, amount, order_price, deal_price):
        print "sell: amount: " + str(amount) + "deal_price: " + str(deal_price)

        self.position = self.position - amount
        self.cost = self.cost - amount * deal_price
        self.cash = self.cash + amount * deal_price
        threshold = StockPriceHistory.THRESHOLD_FLUCTUATION / (1 + StockPriceHistory.THRESHOLD_FLUCTUATION)

        self.buy_orders.append(Order(amount, order_price * (1 - threshold)))

    def start(self, start_date):
        #assume start from market closed of start_date

        cur_date = datetime(start_date.year, start_date.month, start_date.day)
        while (cur_date <=  self.stock_price_history.end_date):
            if not self.start_amount and self.stock_price_history.is_buy_point(cur_date):
                price = self.stock_price_history.get_previous_close_price(start_date)
                self.start_amount = round(self.cash/10/price)
                #use 1/10 fund for first buy
                self.buy_orders.append(Order(self.start_amount, price))
            elif self.stock_price_history.is_market_open(cur_date):
                cur_price = self.stock_price_history.get_stock_price(cur_date)
                #try to execute buy
                if (self.buy_orders):
                    for buy_order in self.buy_orders:
                        if buy_order.price >= cur_price.low:
                            self.deal_buy(buy_order.amount, buy_order.price, min(buy_order.price, cur_price.open))
                            self.buy_orders.remove(buy_order)
                #try to execute sell
                if (self.sell_orders):
                    for sell_order in self.sell_orders:
                        if sell_order.price <= cur_price.high:
                            self.deal_sell(sell_order.amount, sell_order.price, min(sell_order.price, cur_price.open))
                            self.sell_orders.remove(sell_order)

                print "Date:" + cur_date.strftime("%Y-%m-%d") + " Account Value: " + str(self._get_account_value(cur_date))
            cur_date = cur_date + timedelta(days=1)


#stock = StockPriceHistory.load('/Users/zxzhang/stock/data/BABA1.csv')
#print 'is_buy_point: ' + str(stock.is_buy_point(datetime.today()))
trans = TransactionSimulator("BABA1")
trans.start(datetime(2015, 06, 12))