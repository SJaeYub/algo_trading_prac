import pandas as pd
from pandas_datareader import data

# Fetch daily data for 4 years, for 7 major currency pairs
TRADING_INSTRUMENT = 'CADUSD=X'
SYMBOLS = ['AUDUSD=X', 'GBPUSD=X', 'CADUSD=X', 'CHFUSD=X', 'EURUSD=X', 'JPYUSD=X', 'NZDUSD=X']
START_DATE = '2014-01-01'
END_DATE = '2018-01-01'

# DataSeries for each currency
symbols_data = {}
for symbol in SYMBOLS:
    SRC_DATA_FILENAME = symbol + '_data.pkl'

    try:
        data = pd.read_pickle(SRC_DATA_FILENAME)
    except FileNotFoundError:
        data = data.DataReader(symbol, 'yahoo', START_DATE, END_DATE)
        data.to_pickle(SRC_DATA_FILENAME)

    symbols_data[symbol] = data

# Visualize prices for currency to inspect relationship between them
import matplotlib.pyplot as plt
import numpy as np
from itertools import cycle

cycol = cycle('bgrcmky')

price_data = pd.DataFrame()
for symbol in SYMBOLS:
    multiplier = 1.0
    if symbol == 'JPYUSD=X':
        multiplier = 100.0

    label = symbol + ' ClosePrice'
    price_data = price_data.assign(
        label=pd.Series(symbols_data[symbol]['Close'] * multiplier, index=symbols_data[symbol].index))
    ax = price_data['label'].plot(color=next(cycol), lw=2., label=label)
plt.xlabel('Date', fontsize=18)
plt.ylabel('Scaled Price', fontsize=18)
plt.legend(prop={'size': 18})
plt.show()

import statistics as stats

SMA_NUM_PERIODS = 20
price_history = {}

PRICE_DEV_NUM_PRICES = 200
price_deviation_from_sma = {}

num_days = len(symbols_data[TRADING_INSTRUMENT].index)
correlation_history = {}
delta_projected_actual_history = {}
final_delta_projected_history = []

orders = []
positions = []

pnls = []

last_buy_price = 0
last_sell_price = 0
position = 0
buy_sum_price_qty = 0
buy_sum_qty = 0
sell_sum_price_qty = 0
sell_sum_qty = 0
open_pnl = 0
closed_pnl = 0

StatArb_VALUE_FOR_BUY_ENTRY = 0.01
StatArb_VALUE_FOR_SELL_ENTRY = -0.01
MIN_PRICE_MOVE_FROM_LAST_TRADE = 0.01
NUM_SHARES_PER_TRADE = 1000000
MIN_PROFIT_TO_CLOSE = 10

for i in range(0, num_days):
    close_prices = {}

for symbol in SYMBOLS:
    close_prices[symbol] = symbols_data[symbol]['Close'].iloc[i]
    if not symbol in price_history.keys():
        price_history[symbol] = []
        price_deviation_from_sma[symbol] = []

    price_history[symbol].append(close_prices[symbol])
    if len(price_history[symbol]) > SMA_NUM_PERIODS:
        del (price_history[symbol][0])

    sma = stats.mean(price_history[symbol])
    price_deviation_from_sma[symbol].append(close_prices[symbol] - sma)

    if len(price_deviation_from_sma[symbol]) > PRICE_DEV_NUM_PRICES:
        del (price_deviation_from_sma[symbol][0])

    projected_dev_from_sma_using = {}
    for symbol in SYMBOLS:
        if symbol == TRADING_INSTRUMENT:
            continue

        correlation_label = TRADING_INSTRUMENT + '<-' + symbol
        if correlation_label not in correlation_history.keys():
            correlation_history[correlation_label] = []
            delta_projected_actual_history[correlation_label] = []

        if len(price_deviation_from_sma[symbol]) < 2:
            correlation_history[correlation_label].append(0)
            delta_projected_actual_history[correlation_label].append(0)
            continue

        corr = np.corrcoef(price_deviation_from_sma[TRADING_INSTRUMENT], price_deviation_from_sma[symbol])
        cov = np.cov(price_deviation_from_sma[TRADING_INSTRUMENT], price_deviation_from_sma[symbol])
        corr_trading_instrument_lead_instrument = corr[0, 1]
        cov_trading_instrument_lead_instrument = cov[0, 0] / cov[0, 1]
        correlation_history[correlation_label].append(corr_trading_instrument_lead_instrument)

        projected_dev_from_sma_using[symbol] = price_deviation_from_sma[symbol][
                                                   -1] * cov_trading_instrument_lead_instrument
        delta_projected_actual = (
                projected_dev_from_sma_using[symbol] - price_deviation_from_sma[TRADING_INSTRUMENT][-1])
        delta_projected_actual_history[correlation_label].append(delta_projected_actual)

    sum_weights = 0
    for symbol in SYMBOLS:
        if symbol == TRADING_INSTRUMENT:
            continue

        correlation_label = TRADING_INSTRUMENT + '<-' + symbol
        sum_weights += abs(correlation_history[correlation_label][-1])

    final_delta_projected = 0
    close_price = close_prices[TRADING_INSTRUMENT]
    for symbol in SYMBOLS:
        if symbol == TRADING_INSTRUMENT:
            continue

        correlation_label = TRADING_INSTRUMENT + '<-' + symbol

    final_delta_projected += (
            abs(correlation_history[correlation_label][-1]) * delta_projected_actual_history[correlation_label][-1])

    if sum_weights != 0:
        final_delta_projected /= sum_weights
    else:
        final_delta_projected = 0

    final_delta_projected_history.append(final_delta_projected)

    if ((final_delta_projected < StatArb_VALUE_FOR_SELL_ENTRY and abs(
            close_price - last_sell_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)
            or (position > 0 and (open_pnl > MIN_PROFIT_TO_CLOSE))):
        orders.append(-1)
        last_sell_price = close_price
        position -= NUM_SHARES_PER_TRADE
        sell_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
        sell_sum_qty += NUM_SHARES_PER_TRADE
        print("Sell ", NUM_SHARES_PER_TRADE, " @ ", close_price, "Position: ", position)
        print("OpenPnL: ", open_pnl, " ClosedPnL: ", closed_pnl, "TotalPnL: ", (open_pnl + closed_pnl))

    elif ((final_delta_projected > StatArb_VALUE_FOR_BUY_ENTRY and abs(
            close_price - last_buy_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)
          or (position < 0 and (open_pnl > MIN_PROFIT_TO_CLOSE))):
        orders.append(+1)
        last_buy_price = close_price
        position + + NUM_SHARES_PER_TRADE
        buy_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
        buy_sum_qty += NUM_SHARES_PER_TRADE
        print("Buy ", NUM_SHARES_PER_TRADE, " @ ", close_price, "Position: ", position)
        print("OpenPnl: ", open_pnl, " ClosedPnL: ", closed_pnl, "TotalPnL: ", (open_pnl + closed_pnl))

    else:
        orders.append(0)

    positions.append(position)

    open_pnl = 0
    if position > 0:
        if sell_sum_qty > 0:
            open_pnl = abs(sell_sum_qty) * (sell_sum_price_qty / sell_sum_qty - buy_sum_price_qty / buy_sum_qty)

        open_pnl += abs(sell_sum_qty - position) * (close_price - buy_sum_price_qty / buy_sum_qty)

    elif position < 0:
        if buy_sum_qty > 0:
            open_pnl = abs(buy_sum_qty) * (sell_sum_price_qty / sell_sum_qty - buy_sum_price_qty / buy_sum_qty)

        open_pnl += abs(buy_sum_qty - position) * (sell_sum_price_qty / sell_sum_qty - close_price)

    else:
        closed_pnl += (sell_sum_price_qty - buy_sum_price_qty)
        buy_sum_price_qty = 0
        buy_sum_qty = 0
        sell_sum_price_qty = 0
        sell_sum_qty = 0
        last_buy_price = 0
        last_sell_price = 0

    pnls.append(closed_pnl + open_pnl)

correlation_data = pd.DataFrame()
for symbol in SYMBOLS:
    if symbol == TRADING_INSTRUMENT:
        continue

    correlation_label = TRADING_INSTRUMENT + '<-' + symbol
    correlation_data = correlation_data.assign(
        label=pd.Series(correlation_history[correlation_label], index=symbols_data[symbol].index))
    ax = correlation_data['label'].plot(color=next(cycol), lw=2., label='Correlation ' + correlation_label)

for i in np.arange(-1, 1, 0.25):
    plt.axhline(y=i, lw=0.5, color='k')
plt.legend()
plt.show()

# Plot StatArb signal provided by each currency pair
delta_projected_actual_data = pd.DataFrame()
for symbol in SYMBOLS:
    if symbol == TRADING_INSTRUMENT:
        continue

    projection_label = TRADING_INSTRUMENT + '<-' + symbol
    delta_projected_actual_data = delta_projected_actual_data.assign(
        StatArbTradingSignal=pd.Series(delta_projected_actual_history[projection_label],
                                       index=symbols_data[TRADING_INSTRUMENT].index))
    ax = delta_projected_actual_data['StatArbTradingSignal'].plot(color=next(cycol), lw=1.,
                                                                  label='StatArbTradingSignal ' + projection_label)
plt.legend()
plt.show()

delta_projected_actual_data = delta_projected_actual_data.assign(
    ClosePrice=pd.Series(symbols_data[TRADING_INSTRUMENT]['Close'], index=symbols_data[TRADING_INSTRUMENT].index))
delta_projected_actual_data = delta_projected_actual_data.assign(
    FinalStatArbTradingSignal=pd.Series(final_delta_projected_history,
                                        index=symbols_data[TRADING_INSTRUMENT].index))
delta_projected_actual_data = delta_projected_actual_data.assign(
    Trades=pd.Series(orders, index=symbols_data[TRADING_INSTRUMENT].index))
delta_projected_actual_data = delta_projected_actual_data.assign(
    Position=pd.Series(positions, index=symbols_data[TRADING_INSTRUMENT].index))
delta_projected_actual_data = delta_projected_actual_data.assign(
    Pnl=pd.Series(pnls, index=symbols_data[TRADING_INSTRUMENT].index))

plt.plot(delta_projected_actual_data.index, delta_projected_actual_data.ClosePrice, color='k', lw=1.,
         label='ClosePrice')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Trades == 1].index,
         delta_projected_actual_data.ClosePrice[delta_projected_actual_data.Trades == 1], color='r', lw=0,
         marker='^', markersize=7, label='buy')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Trades == -1].index,
         delta_projected_actual_data.ClosePrice[delta_projected_actual_data.Trades == -1], color='g', lw=0,
         marker='v', markersize=7, label='sell')
plt.legend()
plt.show()

plt.plot(delta_projected_actual_data.index, delta_projected_actual_data.FinalStatArbTradingSignal, color='k', lw=1.,
         label='FinalStatArbTradingSignal')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Trades == 1].index,
         delta_projected_actual_data.FinalStatArbTradingSignal[delta_projected_actual_data.Trades == 1], color='r',
         lw=0, marker='^', markersize=7, label='buy')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Trades == -1].index,
         delta_projected_actual_data.FinalStatArbTradingSignal[delta_projected_actual_data.Trades == -1], color='g',
         lw=0, marker='v', markersize=7, label='sell')
plt.axhline(y=0, lw=0.5, color='k')
for i in np.arange(StatArb_VALUE_FOR_BUY_ENTRY, StatArb_VALUE_FOR_BUY_ENTRY * 10, StatArb_VALUE_FOR_BUY_ENTRY * 2):
    plt.axhline(y=i, lw=0.5, color='r')
for i in np.arange(StatArb_VALUE_FOR_SELL_ENTRY, StatArb_VALUE_FOR_SELL_ENTRY * 10,
                   StatArb_VALUE_FOR_SELL_ENTRY * 2):
    plt.axhline(y=i, lw=0.5, color='g')
plt.legend()
plt.show()

plt.plot(delta_projected_actual_data.index, delta_projected_actual_data.Position, color='k', lw=1.,
         label='Position')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Position == 0].index,
         delta_projected_actual_data.Position[delta_projected_actual_data.Position == 0], color='k', lw=0,
         marker='.', label='flat')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Position > 0].index,
         delta_projected_actual_data.Position[delta_projected_actual_data.Position > 0], color='r', lw=0,
         marker='+', label='long')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Position < 0].index,
         delta_projected_actual_data.Position[delta_projected_actual_data.Position < 0], color='g', lw=0,
         marker='_', label='short')
plt.axhline(y=0, lw=0.5, color='k')
for i in range(NUM_SHARES_PER_TRADE, NUM_SHARES_PER_TRADE * 5, NUM_SHARES_PER_TRADE):
    plt.axhline(y=i, lw=0.5, color='r')
for i in range(-NUM_SHARES_PER_TRADE, -NUM_SHARES_PER_TRADE * 5, -NUM_SHARES_PER_TRADE):
    plt.axhline(y=i, lw=0.5, color='g')
plt.legend()
plt.show()

plt.plot(delta_projected_actual_data.index, delta_projected_actual_data.Pnl, color='k', lw=1., label='Pnl')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Pnl > 0].index,
         delta_projected_actual_data.Pnl[delta_projected_actual_data.Pnl > 0], color='g', lw=0, marker='.')
plt.plot(delta_projected_actual_data.loc[delta_projected_actual_data.Pnl < 0].index,
         delta_projected_actual_data.Pnl[delta_projected_actual_data.Pnl < 0], color='r', lw=0, marker='.')
plt.legend()
plt.show()

delta_projected_actual_data.to_csv("statistical_arbitrage.csv", sep=",")
