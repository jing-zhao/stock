class DailyStockPrice(object):
    def __init__(self, open, close, high, low):
        self.open = open
        self.close = close
        self.high = high
        self.low = low

class StockPriceHistory(object):
    FLUCTUATION_PERCENTAGE_THRESHOLD = 0.1
    
    def __init__(self, daily_price_list, date_to_daily_index_dict, start_date, end_date):
        self.daily_price_list = daily_price_list
        self.fluctuation_count_list = []
        self.date_to_daily_index_dict = date_to_daily_index_dict
        self.start_date = start_date
        self.end_date = end_date
        self._populate_fluctuation_counts()
    
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
        if abs(cur_price - prev_base_price) / prev_base_price >= FLUCTUATION_PERCENTAGE_THRESHOLD:
            signal = True if cur_price > prev_base_price else False
            if not fluctuation_signal_list or fluctuation_signal_list[-1] == signal:
                fluctuation_signal_list.append(signal)
                return (cur_price, 0)
            else:
                fluctuation_signal_list.pop()
                return (cur_price, 1)
        return (prev_base_price, 0)
        
    def load(file_path, start_date, end_date):
        # TODO: load from csv
        daily_price_list = []
        return StockPriceHistory(daily_price_list)
    
    def fluctuation_count(self, end_date, window_size):
        while end_date not in self.date_to_daily_index_dict and end_date >= self.start_date:
            end_date = end_date - timedelta(day=1)
        if end_date < self.start_date:
            return 0
        last_date_index = self.date_to_daily_index_dict[end_date]
        first_date_index = 0 if (last_date_index - window_size) < 0 else (last_date_index - window_size)
        return self.fluctuation_count_list[last_date_index] - self.fluctuation_count_list[first_date_index]
        
def say_hello():
    print 'Hello, World'

for i in xrange(5):
    say_hello()

