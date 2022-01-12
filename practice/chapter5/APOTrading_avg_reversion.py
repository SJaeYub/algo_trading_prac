import pandas as pd
from pandas_datareader import data

# Fetch daily data for 4 years
SYMBOL = 'GOOG'
start_date = '2014-01-01'
end_date = '2018-01-01'
SRC_DATA_FILENAME = SYMBOL + '_data.pkl'

try:
    data = pd.read_pickle(SRC_DATA_FILENAME)
except FileNotFoundError:
    data = data.DataReader(SYMBOL, 'yahoo', start_date, end_date)
    data.to_pickle(SRC_DATA_FILENAME)

NUM_PERIODS_FAST = 10  # 빠른EMA 정적 기간 파라미터
K_FAST = 2 / (NUM_PERIODS_FAST + 1)  # 정적 평활화 팩터
ema_fast = 0
ema_fast_values = []

NUM_PERIODS_SLOW = 40
K_SLOW = 2 / (NUM_PERIODS_SLOW + 1)
ema_slow = 0
ema_slow_values = []
apo_values = []

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

APO_VALUE_FOR_BUY_ENTRY = -10
APO_VALUE_FOR_SELL_ENTRY = 10
MIN_PRICE_MOVE_FROM_LAST_TRADE = 10
MIN_PROFIT_TO_CLOSE = 10
NUM_SHARES_PER_TRADE = 10

close = data['Close']
for close_price in close:
    if (ema_fast == 0):
        ema_fast = close_price
        ema_slow = close_price
    else:
        ema_fast = (close_price - ema_fast) * K_FAST + ema_fast
        ema_slow = (close_price - ema_slow) * K_SLOW + ema_slow

    ema_fast_values.append(ema_fast)
    ema_slow_values.append(ema_slow)

    apo = ema_fast - ema_slow
    apo_values.append(apo)

    if ((apo > APO_VALUE_FOR_SELL_ENTRY and abs(close_price - last_sell_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)
            or (position > 0 and (apo >= 0 or open_pnl > MIN_PROFIT_TO_CLOSE))):
        orders.append(-1)
        last_sell_price = close_price
        position -= NUM_SHARES_PER_TRADE
        sell_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
        sell_sum_qty += NUM_SHARES_PER_TRADE
        print("Sell ", NUM_SHARES_PER_TRADE, " @ ", close_price, "Position: ", position)

    elif ((apo < APO_VALUE_FOR_BUY_ENTRY and abs(close_price - last_buy_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)
          or (position < 0 and (apo <= 0 or open_pnl > MIN_PROFIT_TO_CLOSE))):
        orders.append(+1)
        last_buy_price = close_price
        position += NUM_SHARES_PER_TRADE
        buy_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
        buy_sum_qty += NUM_SHARES_PER_TRADE
        print("Buy ", NUM_SHARES_PER_TRADE, " @ ", close_price, "Positions: ", position)

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
            open_pnl = abs(buy_sum_qty) * (sell_sum_price_qty / sell_sum_qty / buy_sum_qty)
            open_pnl += abs(buy_sum_qty - position) * (sell_sum_price_qty / sell_sum_qty - close_price)
    else:
        closed_pnl += (sell_sum_price_qty - buy_sum_price_qty)
        buy_sum_price_qty = 0
        buy_sum_qty = 0
        sell_sum_price_qty = 0
        sell_sum_qty = 0
        last_buy_price = 0
        last_sell_price = 0

    print("OpenPnL: ", open_pnl, " ClosedPnL: ", closed_pnl)
    pnls.append(closed_pnl + open_pnl)

data = data.assign(ClosePrice=pd.Series(close, index=data.index))
data = data.assign(Fast10DayEMA=pd.Series(ema_fast_values, index=data.index))
data = data.assign(Slow40DayEMA=pd.Series(ema_slow_values, index=data.index))
data = data.assign(APO=pd.Series(apo_values, index=data.index))
data = data.assign(Trades=pd.Series(orders, index=data.index))
data = data.assign(Position=pd.Series(positions, index=data.index))
data = data.assign(Pnl=pd.Series(pnls, index=data.index))

import matplotlib.pyplot as plt

data['ClosePrice'].plot(color='blue', lw=3., legend=True)
data['Fast10DayEMA'].plot(color='y', lw=1., legend=True)
data['Slow40DayEMA'].plot(color='m', lw=1., legend=True)
plt.plot(data.loc[data.Trades == 1].index, data.ClosePrice[data.Trades == 1], color='r', lw=0, marker='^', markersize=7,
         label='buy')
plt.plot(data.loc[data.Trades == -1].index, data.ClosePrice[data.Trades == -1], color='g', lw=0, marker='v',
         markersize=7, label='sell')
plt.legend()
plt.show()

data['APO'].plot(color='k', lw=3., legend=True)
plt.plot(data.loc[data.Trades == 1].index, data.APO[data.Trades == 1], color='r', lw=0, marker='^', markersize=7,
         label='buy')
plt.plot(data.loc[data.Trades == -1].index, data.APO[data.Trades == -1], color='g', lw=0, marker='v', markersize=7,
         label='sell')
plt.axhline(y=0, lw=0.5, color='k')
for i in range(APO_VALUE_FOR_BUY_ENTRY, APO_VALUE_FOR_BUY_ENTRY * 5, APO_VALUE_FOR_BUY_ENTRY):
    plt.axhline(y=i, lw=0.5, color='r')
for i in range(APO_VALUE_FOR_SELL_ENTRY, APO_VALUE_FOR_SELL_ENTRY * 5, APO_VALUE_FOR_SELL_ENTRY):
    plt.axhline(y=i, lw=0.5, color='g')
plt.legend()
plt.show()


data['Position'].plot(color='k', lw=1., legend=True)
plt.plot(data.loc[ data.Position == 0 ].index, data.Position[ data.Position == 0 ], color='k', lw=0, marker='.', label='flat')
plt.plot(data.loc[ data.Position > 0 ].index, data.Position[ data.Position > 0 ], color='r', lw=0, marker='+', label='long')
plt.plot(data.loc[ data.Position < 0 ].index, data.Position[ data.Position < 0 ], color='g', lw=0, marker='_', label='short')
plt.axhline(y=0, lw=0.5, color='k')
for i in range( NUM_SHARES_PER_TRADE, NUM_SHARES_PER_TRADE*25, NUM_SHARES_PER_TRADE*5 ):
  plt.axhline(y=i, lw=0.5, color='r')
for i in range( -NUM_SHARES_PER_TRADE, -NUM_SHARES_PER_TRADE*25, -NUM_SHARES_PER_TRADE*5 ):
  plt.axhline(y=i, lw=0.5, color='g')
plt.legend()
plt.show()

data['Pnl'].plot(color='k', lw=1., legend=True)
plt.plot(data.loc[ data.Pnl > 0 ].index, data.Pnl[ data.Pnl > 0 ], color='g', lw=0, marker='.')
plt.plot(data.loc[ data.Pnl < 0 ].index, data.Pnl[ data.Pnl < 0 ], color='r', lw=0, marker='.')
plt.legend()
plt.show()
