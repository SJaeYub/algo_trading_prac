import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pandas_datareader import data


def load_financial_data(start_date, end_date, output_file):
    try:
        df = pd.read_pickle(output_file)
        print('File data found...reading GOOG data')
    except FileNotFoundError:
        print('File not found...downloading the GOOG data')
        df = data.DataReader('GOOG', 'yahoo', start_date, end_date)
        df.to_pickle(output_file)
    return df


goog_data = load_financial_data(start_date='2001-01-01', end_date='2018-01-01', output_file='goog_data_large.pkl')


def double_moving_average(financial_data, short_window, long_window):
    signals = pd.DataFrame(index=financial_data.index)
    signals['signal'] = 0.0
    signals['short_mavg'] = financial_data['Close']. \
        rolling(window=short_window,
                min_periods=1, center=False).mean()
    signals['long_mavg'] = financial_data['Close']. \
        rolling(window=long_window,
                min_periods=1, center=False).mean()
    signals['signal'][short_window:] = \
        np.where(signals['short_mavg'][short_window:]
                 > signals['long_mavg'][short_window:], 1.0, 0.0)
    signals['orders'] = signals['signal'].diff()
    return signals


ts = double_moving_average(goog_data, 20, 100)

fig = plt.figure()
ax1 = fig.add_subplot(111, ylabel='Google price in $')
goog_data['Adj Close'].plot(ax=ax1, color='g', lw=.5)
ts['short_mavg'].plot(ax=ax1, color='r', lw=2.)
ts['long_mavg'].plot(ax=ax1, color='b', lw=2.)

ax1.plot(ts.loc[ts.orders == 1.0].index, goog_data['Adj Close'][ts.orders == 1.0], '^', markersize=7, color='k')
ax1.plot(ts.loc[ts.orders == -1.0].index, goog_data['Adj Close'][ts.orders == -1.0], 'v', markersize=7, color='k')

plt.legend(["Price", "Short mavg", "Long mavg", "Buy", "Sell"])
plt.title("Double Moving Average Trading Strategy")

plt.show()


def naive_momentum_trading(financial_data, nb_conseq_days):
    signals = pd.DataFrame(index=financial_data.index)
    signals['orders'] = 0
    cons_day = 0
    prior_price = 0
    init = True
    for k in range(len(financial_data['Adj Close'])):
        price = financial_data['Adj Close'][k]
        if init:
            prior_price = price
            init = False;
        elif price > prior_price:
            if cons_day < 0:
                cons_day = 0
            cons_day += 1
        elif price < prior_price:
            if cons_day > 0:
                cons_day = 0
                cons_day -= 1
        if cons_day == nb_conseq_days:
            signals['orders'][k] = 1
        elif cons_day == -nb_conseq_days:
            signals['orders'][k] = -1

    return signals


ts = naive_momentum_trading(goog_data, 5)

fig = plt.figure()
ax1 = fig.add_subplot(111, ylabel='Google price in $')
goog_data["Adj Close"].plot(ax=ax1, color='g', lw=.5)

ax1.plot(ts.loc[ts.orders == 1.0].index,
         goog_data["Adj Close"][ts.orders == 1],
         '^', markersize=7, color='k')

ax1.plot(ts.loc[ts.orders == -1.0].index,
         goog_data["Adj Close"][ts.orders == -1],
         'v', markersize=7, color='k')

plt.legend(["Price", "Buy", "Sell"])
plt.title("Naive Momentum Trading Strategy")

plt.show()


def turtle_trading(financial_data, window_size):
    signals = pd.DataFrame(index=financial_data.index)
    signals['orders'] = 0

    signals['high'] = financial_data['Adj Close'].shift(1).rolling(window=window_size).max()
    signals['low'] = financial_data['Adj Close'].shift(1).rolling(window=window_size).min()
    signals['avg'] = financial_data['Adj Close'].shift(1).rolling(window=window_size).mean()

    signals['long_entry'] = financial_data['Adj Close'] > signals.high
    signals['short_entry'] = financial_data['Adj Close'] < signals.low

    signals['long_exit'] = financial_data['Adj Close'] < signals.avg
    signals['short_exit'] = financial_data['Adj Close'] > signals.avg

    init = True
    position = 0
    for k in range(len(signals)):
        if signals['long_entry'][k] and position == 0:
            signals.orders.values[k] = 1
            position = 1
        elif signals['short_entry'][k] and position == 0:
            signals.orders.value[k] = -1
            positions = -1
        elif signals['short_exit'][k] and position > 0:
            signals.orders.value[k]=-1
            position = 0
        elif signals['long_exit'][k] and position < 0:
            signals.orders.values[k] = 1
            position=0
        else:
            signals.orders.values[k] = 0
        return signals

ts = turtle_trading(goog_data, 50)

fig = plt.figure()
ax1 = fig.add_subplot(111, ylabel='Google price in $')
goog_data["Adj Close"].plot(ax=ax1, color='g', lw=.5)
ts["high"].plot(ax=ax1, color='g', lw=.5)
ts["low"].plot(ax=ax1, color='r', lw=.5)
ts["avg"].plot(ax=ax1, color='b', lw=.5)

ax1.plot(ts.loc[ts.orders== 1.0].index,
         goog_data["Adj Close"][ts.orders == 1.0],
         '^', markersize=7, color='k')

ax1.plot(ts.loc[ts.orders== -1.0].index,
         goog_data["Adj Close"][ts.orders == -1.0],
         'v', markersize=7, color='k')



ax1.plot(ts.loc[ts.long_entry== True].index,
         goog_data["Adj Close"][ts.long_entry== True],
         '^', markersize=7, color='k')

ax1.plot(ts.loc[ts.short_entry== True].index,
         goog_data["Adj Close"][ts.short_entry== True],
         'v', markersize=7, color='k')

ax1.plot(ts.loc[ts.long_exit == True].index,
         goog_data["Adj Close"][ts.long_exit == True],
         'v', markersize=7, color='k')

ax1.plot(ts.loc[ts.short_exit == True].index,
         goog_data["Adj Close"][ts.short_exit == True],
         'v', markersize=7, color='k')


plt.legend(["Price","Highs","Lows","Average","Buy","Sell"])
plt.title("Turtle Trading Strategy")

plt.show()