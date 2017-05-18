import urllib.parse
import urllib.request
import pickle
from bisect import bisect_left
import datetime
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
# get last trade datey going back from date
def getLastTradeDay(date=None):
    # if before 4pm, use yesterdays, otherwise use today
    if date is None:
        if datetime.datetime.now().hour < 16:
            date = datetime.datetime.now()-datetime.timedelta(days=1)
        else:
            date = datetime.datetime.now()
    
    # convert to date
    if isinstance(date, datetime.datetime):
        date = date.date()
    
    # 0 is monday 4 is friday (weekday)
    if date.weekday() < 5:
        return date
    # weekend
    else:
        curDate = date
        while curDate.weekday() > 4:
            curDate = curDate - datetime.timedelta(days=1)
        return curDate



"""
Gets the price of a stock.

Gets prices of ticker from begin to end with date, open, high, low, close,
volume, and adjusted close from local database. If part of requested date range
has not been downloaded, will return the part that has been downloaded

Args:
    ticker (str): Ticker of the stock
    begin (date): Beginning of the date range for the stock price
    end (date): End of the date range for the stock price. End >= begin

Returns:
    float[][]: 2d array of date, open, high, low, close, volume, and adj close.
        Date will be in datetime format.

Raises:
    IOError: Raised if ticker not yet downloaded.
    ValueError: Raised if date requested has not been downloaded
"""
def getStockPrice(ticker, begin, end):
    begin = getLastTradeDay(begin)
    end = getLastTradeDay(end)
    
    # loads pickled data
    f = open('stockmanager/stock_data/' + ticker, 'rb')
    data = pickle.load(f)
    f.close()
    
    if begin == end:
        # since start == end, only need to look for one of them
        
        # zip list into only date values and reverse list (so earlier dates first)
        dates = list(list(zip(*data))[0])[::-1]
        
        # find index with bisect_left
        i = bisect_left(dates, begin)
        if len(dates)-i-1 < 0:
            raise ValueError('Date range has not been downloaded!')
        if i != len(dates) and dates[i] == begin:
            # return full data with index
            return data[len(dates)-i-1]
        else:
            # also raise error if cannot find correct date
            raise ValueError('Date range has not been downloaded!')
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
        data = data[len(data)-endIndex-1 : len(data)-startIndex][::-1]
        # data = data[::-1][startIndex:endIndex+1][::-1]
    
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
    processed = [[round(float(item), 2) if not isinstance(item, datetime.date) else item for item in r] for r in processed]
    
    f = open('stockmanager/stock_data/' + ticker, 'wb')
    print(len(processed))
    pickle.dump(processed, f)
    f.close()



"""
Generates training data for the neural network.

Generates training data by calculating when to buy and sell based on future
SLOPE_SIZE day stock data.
Calculate buy/sell stock by calculating slope of line with one end at a day.
The line would have length SLOPE_SIZE
Training data: 1 is buy, 0 is sell

Args:
    ticker (str): Ticker of the stock to train
    begin (date): Starting date of training data.
    end (date): Ending date of training data.
    SLOPE_SIZE (number): Optional, defaults to 20. Size of the slope. Has to be > 0
    SMA_DAY (number): Optional, defaults to 1. Number of days for SMA.

Raises:
    ValueError: Throws error if date range is not multiple of 90 days
"""
def createTrainingData(ticker, begin, end, SLOPE_SIZE=20):
    begin = getLastTradeDay(begin)
    end = getLastTradeDay(end)
    
    
    # actual training data to return
    data = []
    # maximum and minimum slope to normalize to 0-1
    minimum = 1000000
    maximum = -1000000
    
    # [0] is date, [1] is close price
    closes = getStockClose(ticker, begin, end)
    # smooth out data
    # closes = calculateSMA(closes, SMA_DAY)
    

    # vision (since we are training optimal strategy, why not use the future?)
    for i in range(len(closes)):
        # if enough room for slope to go SLOPE_SIZE in the left
        if i <= len(closes)-SLOPE_SIZE:
            # rise / run or y2-y1 / x2-x1
            # upper side of slope is date plus SLOPE_SIZE, the smaller side is
            # just date
            slope = (closes[i+SLOPE_SIZE-1] - closes[i]) / SLOPE_SIZE
        # not enough room, just ignore it
        
        if slope < minimum:
            minimum = slope
        elif slope > maximum:
            maximum = slope
        
        data.append(slope)
    
    
    finalData = []
    # normalize to number between 0 and 1
    for d in data:
        finalData.append((d-minimum) / (maximum-minimum))
    
    return finalData



"""
Calculates the simple moving average

Calculates the simple moving average of the *future* for **time** days.

Args:
    data (float[]): Stock prices to calculate sma. Closing prices preferred
    time (number): How many days to be considered in the SMA.

Returns:
    float[]: SMA of the stocks
"""
def calculateSMA(data, time):
    sma = []
    for i in range(len(data)):
        # if i < time:
        #     sma.append(sum([data[j] for j in range(time)]) / time)
        # enough "future" to calculate sma
        if i < len(data) - time:
            sma.append(sum([data[j] for j in range(i, i + time)]) / (time))
        # not enough, so ignore it and just return array w/o last part
    
    return sma



"""
Save training (and testing) data to a file.

Saves training data, which includes the inputs (from getStockPrice) and outputs
(from createTrainingData).

Args:
    ticker (str): Ticker of the stock to train
    begin (date): Starting date of training data.
    end (date): Ending date of training data.
"""
def saveTrainingData():
    pass
