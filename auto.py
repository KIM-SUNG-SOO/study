import pyupbit
import time
import datetime
import itertools

from collections import deque

def top_tickers_api(count=40):
    tmp = {}
    coins = pyupbit.get_tickers(fiat='KRW')
    for ticker in coins:
        df = pyupbit.get_ohlcv(ticker, "minute60", count=12)
        a0 = df.iloc[0]
        a1 = df.iloc[-1]
        time.sleep(0.2)
        a = sum(df['volume'])
        b = (a0['open'] + a1['close']) // 2
        c = a * b
        tmp[ticker] = c

    rtt = dict(sorted(tmp.items(), key=lambda x: x[1], reverse=True))
    tickers = list(rtt.keys())[:count]

    return tickers

def get_prices(tickers):
    while True:
        prices = pyupbit.get_current_price(tickers)
        if prices == None or len(prices) < 1:
            print("get_price wait...")
            time.sleep(0.2)
            continue
        else:
            return prices

def get_order(uuid):
    while True:
        od = upbit.get_order(uuid)
        if len(od) < 1 or 'error' in od:
            print("get_order wait...", od)
            time.sleep(0.3)
            continue
        else:
            return od

def buy_exe(coin, krw):# 매수
    i = 0
    while True:
        order = upbit.buy_market_order(coin, krw)
        if i <= 3 and order == None or 'error' in order:
            print("buy_exe wait...", coin, krw, order)
            time.sleep(0.3)
            i += 1
            return order
        else:
            return order

def sell_exe(coin):  #매도

    volume = upbit.get_balance(coin)
    time.sleep(0.1)
    if volume > 0:
        i = 0
        while True:
            order = upbit.sell_market_order(coin, volume)
            if i <= 3 and order == None or 'error' in order:
                print("sell_exe wait...", coin, volume, order)
                time.sleep(0.3)
                i += 1
                return order
            else:
                return order
    else:
        return f"{coin} sell_exe 호출 잘못됨"

def sell_limit_order(coin, price, volume):
    price = pyupbit.get_tick_size(price)

    if volume > 0:
        i = 0
        while True:
            order = upbit.sell_limit_order(coin, price, volume)
            if i <= 3 and order == None or "error" in order:
                print("sell_limit_order wait...", coin, price, volume)
                time.sleep(0.3)
                i += 1
                return order
            else:
                 return order
    else:
        return f"{coin} sell_limit_order 호출 잘못됨"


def all_sell():
    hold = upbit.get_balances()
    c = len(hold)  # 현재 보유중 이라면
    tx = "KRW-"
    for i in range(c):
        if hold[i]['unit_currency'] == 'KRW' and hold[i]['currency'] != 'KRW':
            ticker = tx + hold[i]['currency']
            balance = float(hold[i]['balance'])

            if balance > 0:
                upbit.sell_market_order(ticker, balance)
                time.sleep(0.3)

def ck_day():
    t = upbit.get_balances()
    time.sleep(0.2)

    c = len(t)  # 현재 보유중 이라면
    tx = "KRW-"
    for i in range(c):

        if t[i]['unit_currency'] == 'KRW' and t[i]['currency'] != 'KRW' and t[i]['currency'] != 'VTHO':
            coin = tx + t[i]['currency']
            locked = float(t[i]['locked'])
            balance = float(t[i]['balance'])
            buy_price = float(t[i]['avg_buy_price'])

            if locked > 0 and coin != "KRW-VTHO":
                price = pyupbit.get_current_price(coin)
                time.sleep(0.2)
                df = pyupbit.get_ohlcv(coin,"day", count=3)
                time.sleep(0.2)
                cc = sum(df['close']) / 3 / 1.03
                if price <= cc:
                    od = upbit.get_balance(coin)
                    upbit.cancel_order(od[0]['uuid'])
                    time.sleep(0.2)
                    sell_exe(coin)

    targets = top_tickers_api(count=40)

    return targets


def worker(tickers):

    # 매매 초기값 세팅
    lost = []
    stay, ohv, chv = {}, {}, {}

    cash = upbit.get_balance()

    buy_flag = 15

    prices = get_prices(tickers)
    time.sleep(0.2)

    for coin in tickers:

        stay[coin] = [0 for i in range(7)]
        ohv[coin] = deque(maxlen=120)
        chv[coin] = deque(maxlen=120)
        stay[coin][1],stay[coin][2],stay[coin][3],stay[coin][4] = prices[coin],prices[coin],prices[coin],prices[coin]
        df = pyupbit.get_ohlcv(coin, "minute60")
        time.sleep(0.2)
        ohv[coin].extend(df['close'])

        df = pyupbit.get_ohlcv(coin, "minute1")
        time.sleep(0.2)
        chv[coin].extend(df['close'])

        if chv[coin][-3] > prices[coin]:
            stay[coin][3] = prices[coin]

        if chv[coin][-3] < prices[coin]:
            stay[coin][2] = prices[coin]

    t = upbit.get_balances()
    time.sleep(0.2)

    c = len(t)  # 현재 보유중 이라면
    tx = "KRW-"
    for i in range(c):

        if t[i]['unit_currency'] == 'KRW' and t[i]['currency'] != 'KRW' and t[i]['currency'] != 'VTHO':
            coin = tx + t[i]['currency']
            locked = float(t[i]['locked'])
            balance = float(t[i]['balance'])
            buy_price = float(t[i]['avg_buy_price'])

            if coin not in tickers and coin != "KRW-VTHO":
                if balance > 0:
                    sell_exe(coin)
                    time.sleep(0.2)

            if balance > 0 and coin in tickers and coin != "KRW-VTHO":
                stay[coin][0] = 1
                stay[coin][4] = buy_price
                stay[coin][5] = round(((stay[coin][1] / stay[coin][4]) - 1) * 100, 2)  # 매수대비 백분율
                stay[coin][6] = round((stay[coin][3] / stay[coin][2] - 1) * 100, 2)   # 최저대비 백분율
                buy_flag -= 1

                print(f'{coin} {stay[coin]}')

    tic = 1

    umount = round(cash / (buy_flag + 1) / 1000) * 1000  # 15개만사자
    if umount < 6000:
        umount = 6000
    print(f'배팅금액 : {umount}')

    while True:

        now = datetime.datetime.now()

        prices = get_prices(tickers)
        time.sleep(0.2)

        """  하루한번 리셋 START    """

        if now.hour == 1 and now.minute == 59:
            targets = ck_day()
            for ticker in tickers:
                if ticker not in targets:
                    if stay[ticker][0] > 0:
                        sell_exe(ticker)
                        buy_flag += 1
                    del stay[ticker]
                    del ohv[ticker]
                    del chv[ticker]

            for ticker in targets:
                if ticker not in tickers:
                    stay[ticker] = [0 for i in range(7)]
                    ohv[ticker] = deque(maxlen=120)
                    chv[ticker] = deque(maxlen=120)
                    price = pyupbit.get_current_price(ticker)
                    time.sleep(0.2)
                    stay[ticker][1], stay[ticker][2], stay[ticker][3], stay[ticker][4] = price, price, price, price
                    df = pyupbit.get_ohlcv(ticker, "minute60")
                    time.sleep(0.2)
                    ohv[ticker].extend(df['close'])

                    df = pyupbit.get_ohlcv(ticker, "minute1")
                    time.sleep(0.2)
                    chv[ticker].extend(df['close'])

            tickers = targets

        """  리셋 END    """

        for coin in tickers:

            is_buy, is_sell = False, False

            price = prices[coin]

            curr_ma5 = sum(list(itertools.islice(chv[coin],120-5,120))) / 5
            curr_ma15 = sum(list(itertools.islice(chv[coin],120-15,120))) / 15

            hma3 = sum(list(itertools.islice(ohv[coin], 120 - 72, 120))) / 72


            # STAY 업데이트
            stay[coin][1] = price

            if price < stay[coin][2]:
                stay[coin][2] = price

            if price > stay[coin][3]:
                stay[coin][3] = price

            stay[coin][5] = round(((stay[coin][1] / stay[coin][4]) - 1) * 100, 2)

            stay[coin][6] = round((stay[coin][3] / stay[coin][2] - 1) * 100, 2)  # 최저대비 백분율

            if price >= 1000000:
                up_t = 1.01
            elif 1000000 > price >= 100000:
                up_t = 1.015
            else:
                up_t = 1.02

            # 매도/매수 구분
            if stay[coin][0] == 0 and buy_flag > 0 and price >= hma3 * up_t:
                if price >= stay[coin][2] * up_t and price >= chv[coin][-2] and curr_ma5 >= curr_ma15 and curr_ma5 <= curr_ma15 * up_t:
                    is_buy = True

            if stay[coin][0] == 0 and price >= chv[coin][-1] * 1.03:
                is_buy = True

            if is_buy == True:
                if len(lost) > 0:
                    for i in range(len(lost)):
                        if lost[i][0] == coin:
                            is_buy = False


            if stay[coin][0] == 1:
                if price > (stay[coin][4] * 1.012) and price <= (stay[coin][3] / 1.005):
                    is_sell = True
                if price <= hma3 / up_t:
                    is_sell = True

            # 매수
            if is_buy:
                od = buy_exe(coin, umount)
                stay[coin][0] = 1
                buy_flag -= 1
                time.sleep(1)

                if 'uuid' in od:
                    a = list()
                    i_price, qty = 0, 0
                    rf = get_order(od['uuid'])

                    a = rf['trades']
                    c = len(a)

                    for i in range(c):
                        i_price += float(a[i]['price'])
                        qty += float(a[i]['volume'])

                    if i_price == 0:
                        buy_price = price
                    else:
                        buy_price = i_price / c

                    stay[coin][0] = 1
                    stay[coin][2],stay[coin][3],stay[coin][4] = buy_price,buy_price,buy_price

                    print("매수:", coin, stay[coin])

                else:
                    stay[coin][0] = 0
                    buy_flag += 1

            # 매도
            if is_sell:

                sd = sell_exe(coin)
                stay[coin][0] = 0
                buy_flag += 1
                time.sleep(1)

                if 'uuid' in sd:
                    lost.append([coin, now + datetime.timedelta(minutes=5)])
                    stay[coin][2], stay[coin][3], stay[coin][4] = price, price, price
                    cash = upbit.get_balance()
                    time.sleep(0.2)
                    umount = round(cash / (buy_flag + 1) / 1000) * 1000  # 15개만사자
                    if umount < 6000:
                        umount = 6000

                    print(f"매도: {coin} {stay[coin]}")
                else:
                    stay[coin][0] = 1
                    buy_flag -= 1

        if tic % 10 == 0:
            print("\n", now)
            dd_list = []
            for coin in tickers:
                if stay[coin][0] > 0:
                    print(coin, stay[coin])

                    for i in range(len(lost)):
                        if lost[i][0] == coin and lost[i][1] <= now:
                            dd_list.append(i)

            if len(dd_list) > 0:
                for i in dd_list:
                    del lost[i]

        if tic % 50 == 0:
            for coin in tickers:
                chv[coin].append(prices[coin])

                val = upbit.get_balance(coin)
                time.sleep(0.2)
                if val > 0:
                    stay[coin][0] = 1
                else:
                    stay[coin][0] = 0

        if tic == 3000:
            for coin in tickers:
                ohv[coin].append(prices[coin])
                if stay[coin][0] > 0:
                    if stay[coin][5] <= -3.0:
                        hma30 = sum(list(itertools.islice(ohv[coin], 120 - 30, 120))) / 30
                        if prices[coin] >= hma30:
                            val = upbit.get_balance(coin)
                            time.sleep(0.2)
                            sell_limit_order(coin, stay[coin][4]*1.012, val)
                            stay[coin][0] = 0
                        else:
                            sd = sell_exe(coin)
                            stay[coin][0] = 0
                            buy_flag += 1
                            time.sleep(1)

                            if 'uuid' in sd:
                                lost.append([coin, now + datetime.timedelta(minutes=5)])
                                stay[coin][2], stay[coin][3], stay[coin][4] = prices[coin], prices[coin], prices[coin]
                                cash = upbit.get_balance()
                                time.sleep(0.2)
                                umount = round(cash / (buy_flag + 1) / 1000) * 1000  # 15개만사자
                                if umount < 6000:
                                    umount = 6000

                                print(f"매도: {coin} {stay[coin]}")
                            else:
                                stay[coin][0] = 1
                                buy_flag -= 1

                        buy_flag += 1

            tic = 0

        time.sleep(1)  # 틱 업데이트
        tic += 1


if __name__ == '__main__':
    global upbit
    key0 = "SrV35PpqWQpaEnSn6lhTeHExJqqmDHg7G7Om2EXg"
    key1 = "PXR2z4WxtRTonnstYjgSZtUEuJnt1ji3hxxr8ssa"
    upbit = pyupbit.Upbit(key0, key1)

    targets = top_tickers_api()
    worker(targets)

