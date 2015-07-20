#!/usr/bin/python

from datetime import datetime
from datetime import timedelta

class DailyStockPrice(object):
    def __init__(self, open, high, low, close):
        self.open = float(open)
        self.close = float(close)
        self.high = float(high)
        self.low = float(low)
        self.split_factor = 1.0

    def to_str(self):
        return '%.2f,%.2f,%.2f,%.2f'%(self.open, self.high, self.low, self.close)

    def is_active(self, threshold):
        return (self.high - self.low) / self.low > threshold

    @property
    def open_normalized(self):
        return self.open * self.split_factor

    @property
    def close_normalized(self):
        return self.close * self.split_factor

    @property
    def low_normalized(self):
        return self.low * self.split_factor

    @property
    def high_normalized(self):
        return self.high * self.split_factor

class StockPriceHistory(object):

    BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE = 0.5         #Not more than half days are going down
    BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE = 0.2          #Last price is at low 20% end
    BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE = 0.3         # 30% of the days are active
    BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE = 0.2        # 2 buy/sold win in 10 days

    THRESHOLD_DAY_ACTIVE = 0.05               # 5%
    THRESHOLD_FLUCTUATION = 0.05              # 5%

    def __init__(self, daily_price_list, date_to_daily_index_dict, str_start_date, str_end_date, date_to_split_ratio):
        self.daily_price_list = daily_price_list
        self.fluctuation_count_list = []
        self.date_to_daily_index_dict = date_to_daily_index_dict
        self.start_date = datetime.strptime(str_start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(str_end_date, "%Y-%m-%d")
        self.date_to_split_ratio = date_to_split_ratio

        self._normalize_daily_price_factor()
        #self._debug_print()

    def _normalize_daily_price_factor(self):
        cur_date = self.start_date
        cur_split_factor = 1.0
        while cur_date <= self.end_date:
            if cur_date in self.date_to_daily_index_dict:
                cur_price = self.daily_price_list[self.date_to_daily_index_dict[cur_date]]
                if cur_date in self.date_to_split_ratio:
                    cur_split_factor = cur_split_factor * self.date_to_split_ratio[cur_date]
                cur_price.split_factor = cur_split_factor
            cur_date = cur_date + timedelta(days=1)

    def _debug_print(self):
        for key in self.date_to_daily_index_dict:
            print key.strftime("%Y-%m-%d") + ',' + self.daily_price_list[self.date_to_daily_index_dict[key]].to_str()

    def _populate_fluctuation_counts(self):
        if not self.daily_price_list or self.fluctuation_count_list:
            return

        prev_base_price = self.daily_price_list[0].open_normalized
        fluctuation_signal_list = []

        for daily_price in self.daily_price_list:
            prev_base_price, count1 = self._process_one_price(prev_base_price, daily_price.open_normalized, fluctuation_signal_list)
            prev_base_price, count2 = self._process_one_price(prev_base_price, daily_price.close_normalized, fluctuation_signal_list)
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

        #print 'new base:' + str(prev_base_price) + ' count: ' + str(count) + ' sig: ' + ','.join(str(b) for b in fluctuation_signal_list)
        return prev_base_price, count

    @classmethod
    def load(cls, file_path, split_file_path):
        daily_price_list = []
        date_to_daily_index_dict = {}
        date_to_split_ratio = {}
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

        with open(split_file_path, "r") as fs:
            fs.readline()
            lines = fs.readlines()
            for line in lines:
                cols = line.split(',')
                #SPLIT, 20150522, 1:05
                if cols[0] == 'SPLIT':
                    split_ratios = cols[2].split(':')
                    date_to_split_ratio[datetime.strptime(cols[1].strip(' '), "%Y%m%d")] = float(split_ratios[0]) / float(split_ratios[1])

        return StockPriceHistory(daily_price_list, date_to_daily_index_dict, first_date, last_date, date_to_split_ratio)
    
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
            if self.daily_price_list[i].is_active(self.THRESHOLD_DAY_ACTIVE):
                count = count + 1
        return count / (last_date_index - first_date_index + 1)

    def end_price_percentile(self, end_date, window_size=None):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        max = 0.0
        min = 1000000000.0
        for i in range(first_date_index, last_date_index + 1):
            if self.daily_price_list[i].high_normalized > max:
                max = self.daily_price_list[i].high_normalized
            if self.daily_price_list[i].low_normalized < min:
                min = self.daily_price_list[i].low_normalized
        return (self.daily_price_list[last_date_index].close_normalized - min) / (max-min)

    def price_down_percentile(self, end_date, window_size=30):
        first_date_index, last_date_index = self._get_start_and_end_index(end_date, window_size)
        down_count = 0.0
        for i in range(first_date_index + 1, last_date_index + 1):
            if self.daily_price_list[i].close_normalized < self.daily_price_list[i - 1].close_normalized:
                down_count = down_count + 1
        return down_count / (last_date_index - first_date_index)


    def is_buy_point(self, end_date):

        fluctuation_percentile = self.fluctuation_percentile(end_date, 30)
        active_day_percentile = self.active_day_count_percentile(end_date, 30)
        end_price_percentile = self.end_price_percentile(end_date, 10)
        price_down_precentile = self.price_down_percentile(end_date, 30)


        print '1: ' + str(fluctuation_percentile) + \
              ' (>=' + str(self.BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE) + ')'
        print '2: ' + str(active_day_percentile) + \
              ' (>=' + str(self.BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE) + ')'
        print '3: ' + str(end_price_percentile) + \
              ' (<=' + str(self.BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE) + ')'
        print '4: ' + str(price_down_precentile) + \
              ' (<=' + str(self.BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE) + ')'


        return fluctuation_percentile >= self.BUY_POINT_THRESHOLD_FLUCTUATION_PERCENTILE and \
               active_day_percentile >= self.BUY_POINT_THRESHOLD_ACTIVE_DAY_PERCENTILE and \
               end_price_percentile <=  self.BUY_POINT_THRESHOLD_END_PRICE_PERCENTILE and \
               price_down_precentile <= self.BUY_POINT_THRESHOLD_PRICE_DOWN_PERCENTILE

    def get_previous_close_price(self, start_date):
        return self.get_stock_price(start_date).close

    def is_market_open(self, the_day):
        return the_day in self.date_to_daily_index_dict

    def get_stock_price(self, the_day):
        _, last_date_index = self._get_start_and_end_index(the_day)

        if last_date_index > 0:
            return self.daily_price_list[last_date_index]

        raise "Error"


class Order(object):
    def __init__(self, amount, price):

        self.amount = amount
        self.price = price
        self.is_active = False

class TransactionSimulator(object):

    def __init__(self, stock_symbol):

        self.stock_price_history = StockPriceHistory.load('/Users/zxzhang/stock/data/' + stock_symbol + '.csv',
                                                          '/Users/zxzhang/stock/data/' + stock_symbol + '_split.csv')
        self.stock_symbol = stock_symbol
        self.position = 0
        self.cost = 0.0
        self.cash = 1000000.0
        self.buy_orders = []
        self.sell_orders = []
        self.start_amount = None

    def _apply_split_ratio(self, ratio):
        self.position = self.position * ratio
        if self.start_amount:
            self.start_amount = self.start_amount  * ratio
        for o in self.buy_orders:
            o.amount = o.amount * ratio
            o.price = o.price / ratio
        for o in self.sell_orders:
            o.amount = o.amount * ratio
            o.price = o.price / ratio

    def _account_status(self, the_day):
        print "Date:" + the_day.strftime("%Y-%m-%d") +\
              " Price:" + str(self._last_price(the_day)) + \
              " Total:" + str(self._get_account_value(the_day)) +\
              " Pending Buy: " + ",".join(str(o.price) for o in self.buy_orders) + \
              " Pending Sell: " + ",".join(str(o.price) for o in self.sell_orders)

    def _last_price(self, the_day):
        return self.stock_price_history.get_stock_price(the_day).close

    def _get_account_value(self, the_day):
        return self.cash + self.position * self._last_price(the_day)

    def _add_buy_order(self, amount, price):
        #print "Add Buy Order: amount:" + str(amount) + " price:" + str(price)
        if (self.cash >= price * amount):
            self.buy_orders.append(Order(amount, price))

    def _add_sell_order(self, amount, price):
        #print "Add Sell Order: amount:" + str(amount) + " price:" + str(price)
        self.sell_orders.append(Order(amount, price))

    def deal_buy(self, amount, deal_price, the_date):
        print "date:" + the_date.strftime("%Y-%m-%d") + " buy: amount: " + str(amount) + " deal_price: " + str(deal_price)

        self.position = self.position + amount
        self.cost = self.cost + amount * deal_price
        self.cash = self.cash - amount * deal_price
        self._add_sell_order(amount, deal_price * (1 + StockPriceHistory.THRESHOLD_FLUCTUATION))

        threshold = StockPriceHistory.THRESHOLD_FLUCTUATION / (1 + StockPriceHistory.THRESHOLD_FLUCTUATION)
        self._add_buy_order(amount, deal_price * (1 - threshold))

    def deal_sell(self, amount, deal_price, the_date, buy_deal_happened):
        print "date:" + the_date.strftime("%Y-%m-%d") + " sell: amount: " + str(amount) + " deal_price: " + str(deal_price)

        self.position = self.position - amount
        self.cost = max(0, self.cost - amount * deal_price)
        self.cash = self.cash + amount * deal_price

        if not buy_deal_happened:
            self.buy_orders = []
            threshold = StockPriceHistory.THRESHOLD_FLUCTUATION / (1 + StockPriceHistory.THRESHOLD_FLUCTUATION)
            self._add_buy_order(amount, deal_price * (1 - threshold))

    def start(self, start_date, end_date=None):
        #assume start from market closed of start_date

        cur_date = datetime(start_date.year, start_date.month, start_date.day)
        if not end_date or end_date > self.stock_price_history.end_date:
            end_date = self.stock_price_history.end_date

        while (cur_date <=  end_date):
            # TODO: Process split, impacting position, pending order
            if cur_date in self.stock_price_history.date_to_split_ratio:
                self._apply_split_ratio(self.stock_price_history.date_to_split_ratio[cur_date])

            if not self.start_amount and self.stock_price_history.is_buy_point(cur_date):
                price = self.stock_price_history.get_previous_close_price(cur_date)
                self.start_amount = round(self.cash/10/price)
                #use 1/10 fund for first buy
                self._add_buy_order(self.start_amount, price)
                print "Buy point found"
            elif self.stock_price_history.is_market_open(cur_date):
                cur_price = self.stock_price_history.get_stock_price(cur_date)
                deal_buy_happened = False
                #try to execute buy
                if (self.buy_orders):
                    for buy_order in self.buy_orders:
                        if buy_order.is_active and buy_order.price >= cur_price.low:
                            self.deal_buy(buy_order.amount, min(buy_order.price, cur_price.open), cur_date)
                            buy_order.amount = 0
                            deal_buy_happened = True
                self.buy_orders = [o for o in self.buy_orders if o.amount > 0]

                #try to execute sell
                deal_sell_happened = False
                if (self.sell_orders):
                    for sell_order in self.sell_orders:
                        if sell_order.is_active and sell_order.price <= cur_price.high:
                            self.deal_sell(sell_order.amount, max(sell_order.price, cur_price.open), cur_date, deal_buy_happened)
                            sell_order.amount = 0
                            deal_sell_happened = True
                    self.sell_orders = [o for o in self.sell_orders if o.amount > 0]

                #print "Date:" + cur_date.strftime("%Y-%m-%d") + " Account Value: " + str(self._get_account_value(cur_date))
                if deal_sell_happened and not self.sell_orders:
                    self.buy_orders = []
                    self.start_amount = None


            #update order to active
            for o in self.buy_orders:
                o.is_active = True
            for o in self.sell_orders:
                o.is_active = True

            self._account_status(cur_date)
            cur_date = cur_date + timedelta(days=1)

#stock = StockPriceHistory.load('/Users/zxzhang/stock/data/BABA1.csv')
#print 'is_buy_point: ' + str(stock.is_buy_point(datetime.today()))
trans = TransactionSimulator("UCO")
trans.start(datetime(2015, 01, 01), datetime(2015, 05, 20))