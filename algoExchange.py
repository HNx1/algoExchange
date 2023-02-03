from miniExchange import UtilityExchange, Order
import numpy as np


class AlgoExchange(UtilityExchange):
    def __init__(self, tickRate=75, breadth=100, depth=0.01, fdsCount=10e6):
        super().__init__(1, 1)
        # Starting prices by asset
        self.oraclePrices = [100.0]*self.assetCount
        # Beta for each asset, constant for now but will model evolution of these betas in future update. This just multiplies up for each asset with market vols
        self.betas = [1.0]*self.assetCount
        # Risk Free Rate and market volatility, will model evolution of both in future update. RFR is a per tick rate i.e. annualised rate split over 252*tickRate compounded periods
        self.rfr = 0.03
        self.vol = 0.16
        # Per tick rfr and vols
        self.tickRfr = np.exp(np.log(1+self.rfr)/(252*tickRate))-1
        self.tickVol = self.vol/(np.sqrt(252*tickRate))
        # tickRate is the number of ticks in each trading day, defaults to 75 ticks in 6hr30min trading day = 5 minute per tick
        self.tickRate = tickRate
        # Order book breadth and depth
        self.breadth = breadth
        self.depth = depth
        # fully diluted shares for assets
        self.fdsCount = fdsCount
        self.fds = [self.fdsCount]*self.assetCount
        # Liquidity control parameter
        self.alpha = 5
        # Vol profile - first value is proportion of day, second value is proportion of daily volume during period
        self.volProfile = [(0.05, 0.2), (0.05, 0.1), (0.8, 0.4),
                           (0.05, 0.1), (0.05, 0.2)]

    def addAsset(self):
        # We need to extend the parent method slightly to extend oracle properties to the new asset
        super(AlgoExchange, self).addAsset()

        self.oraclePrices.append(100.0)
        self.betas.append(1.0)
        self.fds.append(self.fdsCount)

    def oracle(self):
        # Runs one tick of the exchange

        # Update oracle prices
        self.oraclePrice()

        # Cancels oracle orders
        for order in self.orderList:
            if order.trader == 0:
                order.quant = 0

        # Build new order book for each asset
        for asset in range(self.assetCount):
            self.oracleBook(asset)

    def oraclePrice(self):
        # Update oracle prices
        vols = [beta*self.tickVol for beta in self.betas]
        # want to get the weighted average of the previous order book at each asset, handling some potential error cases at the same time, and using alpha parameter
        # Note if no order list reduces to just the previous oracle price
        wAvs = [(1+self.alpha)*self.oraclePrices[i] - self.alpha*(self.oraclePrices[i] if not self.orderList else sum(order.quant*order.price for order in self.orderList if order.asset == i)/sum(
            (order.quant for order in self.orderList if order.asset == i))) for i in range(self.assetCount)]
        # Update oracle prices
        self.oraclePrices = [
            wAvs[i]*(1+np.random.normal(self.tickRfr, vols[i])) for i in range(self.assetCount)]

    def oracleBook(self, asset):
        # Here we are going to take the oracle price for each asset and use it to generate an order book for the asset
        # Here's what we'll do- take 0.2*asset.vol either side of the current oracle price, and create a linspace with length self.breadth between those parameters
        # We need to know the total amount of liquidity to create for each asset, and we'll assume 10% of each asset is in the order book at a given time.
        # We'll use a Poisson distribution to generate the order book for each asset across the buy and sell side of the book.
        # Poisson only because its a very simple skewed distribution, with a clipped left tail that can simulate a zero-crossover order book
        # We want very little liquidity very close to the asset (close based on the vol) then a lot of liquidity quite close to the asset, then a fat tail. Poisson is good for this
        # For simplicity we'll make the books symmetric, if we change this, we want the expectation of the order book overall to remain equal to the oracle price so our update process works out
        spread = 0.2*self.betas[asset]*self.vol
        r = [self.oraclePrices[asset]*p for p in [1-spread, 1.0, 1+spread]]
        buyR = np.flip(np.linspace(
            r[0], r[1], self.breadth//2, endpoint=False))
        sellR = np.flip(np.linspace(
            r[2], r[1], self.breadth//2, endpoint=False))
        p1 = np.random.poisson(
            self.breadth//8, int(self.depth*self.fds[asset]))
        p2 = [np.count_nonzero(p1 == i) for i in range(self.breadth//2)]
        for p, r in [(0, sellR), (1, buyR)]:
            for i, v in enumerate(r):
                order = Order(asset, "sell" if p == 0 else "buy", p2[i], v,
                              0, self.orderCount)
                self.orderCount += 1
                self.orderList.append(order)

    # Now we'll build a variety of algorithms to trade with

    def TWAP(self, ticks, asset, type, quant, trader, random=False, lag=1, printing=False):
        slippage = sharesTraded = 0.0
        # Split orders uniformly across {ticks} ticks of the exchange.
        compTarget = orderSize = quant/ticks
        startPrice = self.oraclePrices[asset]
        for _ in range(lag):
            # Run exchange over the lag period
            self.oracle()
        for _ in range(ticks):
            # Order size can't be bigger than remaining shares in order, can't be less than zero,
            # we add a completion target reverting factor and a standard order size randomised in a Gaussian fashion
            if random:
                orderSize = min(quant-sharesTraded, max(0, (compTarget -
                                                            sharesTraded)+(1+np.random.normal(0, 0.1))*quant/ticks))

            # Send a market order to the exchange
            checkVal = self.transact(asset, type, orderSize, trader)
            if checkVal[0] == "fail":
                # If transaction fails, break out of algo (transact returns "fail" if it fails, otherwise it returns shares not traded ).
                break

            # Update completion target/value traded/slippage
            compTarget += quant/ticks
            sharesTraded += (orderSize-checkVal[0])
            slippage += abs(checkVal[1] -
                            startPrice)*(orderSize-checkVal[0])
            # Update prices
            self.oracle()

        # Calculate slippage as percentage of total predicted transaction
        slippage /= (sharesTraded*startPrice*0.01)
        # Calculate market impact in direction of trade (partially influenced by trade)
        m = 100*(self.oraclePrices[asset]/startPrice - 1)
        marketImpact = m if type == "buy" else -m
        if printing:
            print(f"Slippage was {slippage:.2f}%")
            print(f"Market Impact was {marketImpact:.2f}%")
            print(f"Executed {100*sharesTraded/quant:.2f}% of the order")

    def VWAP(self, ticks, asset, type, quant, trader, index=0, volProfile=None, random=False, lag=1, printing=False):
        # Basic idea of VWAP is that we want to follow the typical volatility of a day

        slippage = sharesTraded = 0.0
        startPrice = self.oraclePrices[asset]
        for _ in range(lag):
            # Run exchange over the lag period
            self.oracle()
            index += 1

        if not volProfile:
            volProfile = self.volProfile
        # Now we'll build a volatility profile of the correct length.
        dVolArr = np.array(0)
        for x, y in volProfile:
            l = int(x*self.tickRate)+1
            dVolArr = np.append(dVolArr, np.ones(l)*y/l)
        while len(dVolArr) > self.tickRate:
            dVolArr = np.append(
                dVolArr[:len(dVolArr)//2], dVolArr[len(dVolArr)//2+1:])
        # dVol Arr is now length of the tick rate, telling us how volatility moves during a trading
        # Next, we're going to build a volatility profile for the full length of our trading algorithm
        index = index % self.tickRate
        algoVolArr = dVolArr[index:index+ticks]
        while len(algoVolArr) < ticks:
            z = ticks-len(algoVolArr)
            if z > self.tickRate:
                algoVolArr = np.append(algoVolArr, dVolArr)
            else:
                algoVolArr = np.append(algoVolArr, dVolArr[:z])
        # Normalise vol profile
        algoVolArr = algoVolArr/np.sum(algoVolArr)
        # Reset index
        index = 0
        compTarget = 0
        for i in range(ticks):
            compTarget += algoVolArr[i]*quant
            orderSize = algoVolArr[i]*quant
            # Order size can't be bigger than remaining shares in order, can't be less than zero,
            # we add a completion target reverting factor and standard order size randomised in a Gaussian fashion
            if random:
                orderSize = min(quant-sharesTraded, max(0, (compTarget -
                                                            sharesTraded)+(1+np.random.normal(0, 0.1))*orderSize))

            # Send a market order to the exchange
            checkVal = self.transact(asset, type, orderSize, trader)
            if checkVal[0] == "fail":
                # If transaction fails, break out of algo (transact returns "fail" if it fails, otherwise it returns shares not traded ).
                break

            # Update value traded/slippage
            sharesTraded += (orderSize-checkVal[0])
            slippage += abs(checkVal[1] -
                            startPrice)*(orderSize-checkVal[0])
            # Update prices/completion target if continuing
            self.oracle()

        # Calculate slippage as percentage of total predicted transaction
        slippage /= (sharesTraded*startPrice*0.01)
        # Calculate market impact in direction of trade (partially influenced by trade)
        m = 100*(self.oraclePrices[asset]/startPrice - 1)
        marketImpact = m if type == "buy" else -m
        if printing:
            print(f"Slippage was {slippage:.2f}%")
            print(f"Market Impact was {marketImpact:.2f}%")
            print(f"Executed {100*sharesTraded/quant:.2f}% of the order")
