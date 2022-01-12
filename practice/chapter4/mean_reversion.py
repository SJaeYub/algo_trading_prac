import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
import numpy as np
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import coint
import seaborn
from pandas_datareader import data

symbolsIds = ['SPY', 'AAPL', 'ADBE', 'LUV', 'MSFT', 'SKYW', 'QCOM',
              'HPQ', 'JNPR', 'AMD', 'IBM']


def find_cointegrated_pairs(data):  # 입력받은 금융 상품들 간의 공적분 값 계산 p-값이 0에 가까울수록 공적분 관겨 있음
    n = data.shape[1]
    pvalue_matrix = np.ones((n, n))
    keys = data.keys()
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            result = coint(data[keys[i]], data[keys[j]])
            pvalue_matrix[i, j] = result[1]
            if result[1] < 0.02:
                pairs.append((keys[i], keys[j]))

    return pvalue_matrix, pairs


def load_financial_data(symbols, start_date, end_date, output_file):  # 공적분 된 심벌 데이터 로딩
    try:
        df = pd.read_pickle(output_file)
        print('File data found...reading symbols data')
    except FileNotFoundError:
        print('File not found...downloading the symbols data')
        df = data.DataReader(symbols, 'yahoo', start_date, end_date)
        df.to_pickle(output_file)
    return df


data = load_financial_data(symbolsIds, start_date='2001-01-01',
                           end_date='2018-01-01',
                           output_file='multi_data_large.pkl')

pvalues, pairs, = find_cointegrated_pairs(data['Adj Close'])
print(pairs)

seaborn.heatmap(pvalues, xticklabels=symbolsIds,
                yticklabels=symbolsIds, cmap='RdYlGn_r',
                mask=(pvalues >= 0.98))

plt.show()
print(pairs)

print(data.head(3))

# 심벌1이라는 심벌의 임의의 수익률 생성
np.random.seed(123)

Symbol1_returns = np.random.normal(0, 1, 100)
Symbol1_prices = pd.Series(np.cumsum(Symbol1_returns), name='Symbol1') + 10
Symbol1_prices.plot(figsize=(15,7))
plt.show()

# 심벌1을 기준으로 심벌2의 가격을 구성, 상품간의 상관관계에 따라!
noise = np.random.normal(0, 1, 100)
Symbol2_prices = Symbol1_prices+10+noise
Symbol2_prices.name = 'Symbol2'
plt.title("Symbol 1 and Symbol 2 prices")
Symbol1_prices.plot()
Symbol2_prices.plot()
plt.show()

scores, pvalues, _ = coint(Symbol1_prices, Symbol2_prices)      #공적분 분석하는 함수

def zscore(series):
    return (series - series.mean()) / np.std(series)        #평균으로부터 한 종목의 가격이 멀면 곧 가격이 하락하거나 다른 종목이 상승할 것이라고 예측

ratios = Symbol1_prices/Symbol2_prices          #두 종목 가격사이의 비율 사죵, 주어진 가격이 평균 가격에서 멀어질 때를 정의하는 임계값 설정을 위함
ratios.plot()

train = ratios[:75]
test = ratios[75:]

plt.axhline(ratios.mean())
plt.legend([' Ratio'])
plt.show()

zscore(ratios).plot()
plt.axhline(zscore(ratios).mean(), color ="black")
plt.axhline(1.0, color ="red")
plt.axhline(-1.0, color ="green")
plt.show()

ratios.plot()
buy = ratios.copy()
sell = ratios.copy()
buy[zscore(ratios)>-1] = 0
sell[zscore(ratios)<1] = 0
buy.plot(color="g", linestyle="None", marker="^")
sell.plot(color="r", linestyle="None", marker="v")
x1,x2,y1,y2 = plt.axis()
plt.axis((x1,x2,ratios.min(),ratios.max()))
plt.legend(["Ratio", "Buy Signal", "Sell Signal"])
plt.show()

symbol1_buy=Symbol1_prices.copy()
symbol1_sell=Symbol1_prices.copy()
symbol2_buy=Symbol2_prices.copy()
symbol2_sell=Symbol2_prices.copy()

Symbol1_prices.plot()
symbol1_buy[zscore(ratios)>-1] = 0
symbol1_sell[zscore(ratios)<1] = 0
symbol1_buy.plot(color="g", linestyle="None", marker="^")
symbol1_sell.plot(color="r", linestyle="None", marker="v")

Symbol2_prices.plot()
symbol2_buy[zscore(ratios)<1] = 0
symbol2_sell[zscore(ratios)>-1] = 0
symbol2_buy.plot(color="g", linestyle="None", marker="^")
symbol2_sell.plot(color="r", linestyle="None", marker="v")


x1,x2,y1,y2 = plt.axis()
plt.axis((x1,x2,Symbol1_prices.min(),Symbol2_prices.max()))
plt.legend(["Symbol1", "Buy Signal", "Sell Signal","Symbol2"])
plt.show()

Symbol1_prices = data['Adj Close']['MSFT']
Symbol1_prices.plot(figsize=(15,7))
plt.show()
Symbol2_prices = data['Adj Close']['JNPR']
Symbol2_prices.name = 'JNPR'
plt.title("MSFT and JNPR prices")
Symbol1_prices.plot()
Symbol2_prices.plot()
plt.legend()
plt.show()



