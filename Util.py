import urllib.parse
import urllib.request
import pickle
from bisect import bisect_left
from pprint import pprint
from datetime import date
from datetime import datetime, timedelta
import dateutil.parser




"""
Get last trading day

Gets the last trading day starting from date and going back. A trading day is
Monday - Friday (does not take into account holidays).

Args:
    date (date): Going back from this day

Returns:
    datetime: The last trade day

"""
# get last trade day going back from date
def getLastTradeDay(da=None):
    # if before 4pm, use yesterdays, otherwise use today
    if da is None:
        if datetime.now().hour < 16:
            da = datetime.now()-timedelta(days=1)
        else:
            da = datetime.now()
    
    # convert to date
    if isinstance(da, datetime):
        da = da.date()
    
    # 0 is monday 4 is friday (weekday)
    if da.weekday() < 5:
        return da
    # weekend
    else:
        curDate = da
        while curDate.weekday() > 4:
            curDate = curDate - timedelta(days=1)
        return curDate



"""
Gets the price of a stock.

Gets prices of ticker from begin to end with date, open, high, low, close,
volume, and adjusted close from local database.

Args:
    ticker (str): Ticker of the stock
    begin (date): Beginning of the date range for the stock price
    end (`date`): End of the date range for the stock price. End >= begin

Returns:
    float[][]: 2d array of date, open, high, low, close, volume, and adj close.
        Date will be in datetime format.

Raises:
    IOError: Raised if ticker not yet downloaded.
"""
def getStockPrice(ticker, begin, end):
    begin = getLastTradeDay(begin)
    end = getLastTradeDay(end)
    
    # loads pickled data
    f = open('stock_data/' + ticker, 'rb')
    data = pickle.load(f)
    f.close()
    
    if begin == end:
        # since start == end, only need to look for one of them
        
        # zip list into only date values and reverse list (so earlier dates first)
        dates = list(list(zip(*data))[0])[::-1]
        
        # find index with bisect_left
        i = bisect_left(dates, begin)
        if i != len(dates) and dates[i] == begin:
            return data[::-1][i]
    else:
        # start and end index to slice list
        startIndex = 0
        endIndex = 0
        
        # zip list into only date values and reverse list (so earlier dates first)
        dates = list(list(zip(*data))[0])[::-1]
        
        # find start and end index with bisect_left
        i = bisect_left(dates, begin)
        if i != len(dates) and dates[i] == begin:
            startIndex = i
        i = bisect_left(dates, end)
        if i != len(dates) and dates[i] == end:
            endIndex = i
        
        # reverse data and bisect and reverse again
        data = data[::-1][startIndex:endIndex+1][::-1]
    
    return data



"""
Gets closing prices of stock.

Gets prices of ticker from begin to end of only closing price. If end is None,
will return the prices of stock at beginning as a float.

Args:
    ticker (str): Ticker of the stock
    begin (date): Beginning of the date range for the stock price
    end (date): End of the date range for the stock price. End >= begin

Returns:
    float: Closing ticker price
    -or-
    float[]: Closing ticker prices
"""
def getStockClose(ticker, begin, end=None):
    if end is None:
        prices = getStockPrice(ticker, begin, begin)
        return prices[4] # directly returns values if only one date
    else:
        prices = getStockPrice(ticker, begin, end)
        return [p[4] for p in prices]



"""
Pretty prints 2d arrays

Pretty prints 2d arrays by adding equals signs before and after and aligning the
values into a table.
http://stackoverflow.com/questions/13214809/pretty-print-2d-python-list

Args:
    headers (str[]): Headers of the table to print
    matrix ([][]): 2d array of values to print in the table. Size of each
        individual array must equal the size of headers.

"""
def prettyPrint(headers, matrix):
    if len(matrix) == 0:
        return
    
    matrix = [headers] + matrix
    s = [[str(e) for e in row] for row in matrix]
    lens = [max(map(len, col)) for col in zip(*s)]
    fmt = '\t'.join('{{:{}}}'.format(x) for x in lens)
    table = [fmt.format(*row) for row in s]
    
    print('=' * 8 * sum([l // 8 + 1 for l in lens]))
    print('\n'.join(table))
    print('=' * 8 * sum([l // 8 + 1 for l in lens]))



"""
Downloads stock data.

Downloads stock data to a file to be accessed by getStockPrice. Pass only ticker
to download whole stock history.

Args:
    ticker (str): Downloads data of this stock.
    begin (date): Optional. Begin range to download
    end (date): Optional. End range to download
"""
def downloadStockData(ticker, begin=None, end=None):
    beginStr = ''
    endStr = ''
    
    if begin is not None:
        begin = getLastTradeDay(begin)
        beginStr = '&a={}&b={}&c={}'.format(
            begin.month - 1,
            begin.day,
            begin.year
        )
    if end is not None:
        end = getLastTradeDay(end)
        endStr = '&d={}&e={}&f={}'.format(
            end.month - 1,
            end.day,
            end.year
        )
    
    # https://greenido.wordpress.com/2009/12/22/work-like-a-pro-with-yahoo-finance-hidden-api/
    # month starts at 0
    url = 'http://ichart.finance.yahoo.com/table.csv?s={}{}{}&g=d&ignore=.csv'.format(
        ticker,
        beginStr,
        endStr
    )
    
    try:
        # request url, splitting csv by newline and remove header and last newline
        response = urllib.request.urlopen(url).read().decode('utf-8').split('\n')[1:-1]
    except urllib.error.HTTPError:
        print('URL ERROR!: ', url)
    
    # split each line by a comma
    processed = [r.split(',') for r in response]
    # turn the first element into a date
    processed = [[dateutil.parser.parse(r[0]).date()] + r[1:] for r in processed]
    # round numbers for consistency
    processed = [[round(float(item), 2) if not isinstance(item, date) else item for item in r] for r in processed]
    
    f = open('stock_data/' + ticker, 'wb')
    pickle.dump(processed, f)
    f.close()
