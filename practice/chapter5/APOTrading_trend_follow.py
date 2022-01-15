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

# Variables/constants for EMA Calculation:
NUM_PERIODS_FAST = 10  # Static time period parameter for the fast EMA
K_FAST = 2 / (NUM_PERIODS_FAST + 1)  # Static smoothing factor parameter for fast EMA
ema_fast = 0
ema_fast_values = []  # we will hold fast EMA values for visualization purposes

NUM_PERIODS_SLOW = 40  # Static time period parameter for slow EMA
K_SLOW = 2 / (NUM_PERIODS_SLOW + 1)  # Static smoothing factor parameter for slow EMA
ema_slow = 0
ema_slow_values = []  # we will hold slow EMA values for visualization purposes

apo_values = []  # track computed absolute price oscillator value signals

# Variables for Trading Strategy trade, position & pnl management:
orders = []  # Container for tracking buy/sell order, +1 for buy order, -1 for sell order, 0 for no-action
positions = []  # Container for tracking positions, +ve for long positions, -ve for short positions, 0 for flat/no position
pnls = []  # Container for tracking total_pnls, this is the sum of closed_pnl i.e. pnls already locked in and open_pnl i.e. pnls for open-position marked to market price

last_buy_price = 0  # Price at which last buy trade was made, used to prevent over-trading at/around the same price
last_sell_price = 0  # Price at which last sell trade was made, used to prevent over-trading at/around the same price
position = 0  # Current position of the trading strategy
buy_sum_price_qty = 0  # Summation of products of buy_trade_price and buy_trade_qty for every buy Trade made since last time being flat
buy_sum_qty = 0  # Summation of buy_trade_qty for every buy Trade made since last time being flat
sell_sum_price_qty = 0  # Summation of products of sell_trade_price and sell_trade_qty for every sell Trade made since last time being flat
sell_sum_qty = 0  # Summation of sell_trade_qty for every sell Trade made since last time being flat
open_pnl = 0  # Open/Unrealized PnL marked to market
closed_pnl = 0  # Closed/Realized PnL so far

# Constants that define strategy behavior/thresholds
APO_VALUE_FOR_BUY_ENTRY = -10  # APO trading signal value above which to enter buy-orders/long-position
APO_VALUE_FOR_SELL_ENTRY = 10  # APO trading signal value below which to enter sell-orders/short-position
MIN_PRICE_MOVE_FROM_LAST_TRADE = 10  # Minimum price change since last trade before considering trading again, this is to prevent over-trading at/around same prices
NUM_SHARES_PER_TRADE = 10  # Number of shares to buy/sell on every trade
MIN_PROFIT_TO_CLOSE = 10 * NUM_SHARES_PER_TRADE  # Minimum Open/Unrealized profit at which to close positions and lock profits

close = data['Close']
for close_price in close:
    # This section updates fast and slow EMA and computes APO trading signal
    if (ema_fast == 0):  # first observation
        ema_fast = close_price
        ema_slow = close_price
    else:
        ema_fast = (close_price - ema_fast) * K_FAST + ema_fast
        ema_slow = (close_price - ema_slow) * K_SLOW + ema_slow

    ema_fast_values.append(ema_fast)
    ema_slow_values.append(ema_slow)

    apo = ema_fast - ema_slow
    apo_values.append(apo)

    if((apo < APO_VALUE_FOR_SELL_ENTRY and abs(close_price - last_sell_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)
    or (position > 0 and (apo <= 0 or open_pnl > MIN_PROFIT_TO_CLOSE))):
        orders.append(-1)
        last_sell_price = close_price
        position -= NUM_SHARES_PER_TRADE
        sell_sum_price_qty += (close_price * NUM_SHARES_PER_TRADE)
        sell_sum_qty += NUM_SHARES_PER_TRADE
        print("Sell ", NUM_SHARES_PER_TRADE, " @ ", close_price, "Position: ", position)

    elif ((apo > APO_VALUE_FOR_BUY_ENTRY and abs(close_price - last_buy_price) > MIN_PRICE_MOVE_FROM_LAST_TRADE)
    or (position < 0 and (apo >= 0 or open_pnl > MIN_PROFIT_TO_CLOSE))):
        orders.append(+1)
        position += NUM_SHARES_PER_TRADE
        buy_sum_price_qty += (close_price*NUM_SHARES_PER_TRADE)
        buy_sum_qty += NUM_SHARES_PER_TRADE
        print("Buy ", NUM_SHARES_PER_TRADE, " @ ", close_price, "Position: ", position)

    else:
        orders.append(0)