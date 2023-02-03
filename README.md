# algoExchange

## Summary

- A light-weight Exchange class that allows bid-ask trading of a number of
  assets between a number of participants
- UtilityExchange extends this with order stack printing, adding assets and
  traders, and cancelling orders
- AlgoExchange further extends UtilityExchange to provided a simulated
  environment for analysing liquidity patterns and standard trading execution
  algorithms
- The purpose of this project is 2 fold - it's instructive about the function
  and operation of exchanges, but also to facilitate research I'm doing around
  how real-world order-books are predictive of stock prices, as well as how we
  can measure the performance of various trading execution algorithms under
  re-sampling from real world conditions

## miniExchange.py

- The core functionality of the Exchange class comes from the transact method.
  Supplying an optional price to this method will create a limit order,
  otherwise it will be a market order. Due to the margin treatment described
  below, buys and sells are separated by a supplied type not by positive or
  negative share quantities.
- Trades price at the price of the order already existing in the order book.
- This is a synchronous exchange - there is no time component to it only
  sequential execution and storage of orders. Market orders that are unfilled
  immediately expire.
- When a limit buy is created, it consumes funds of the trader. When a limit
  sell is created, it consumes shares of the trader in that asset. Therefore it
  is not possible to generate margin by placing limit orders. Also, when an
  opposing order hits these orders, we then consequently do not consume
  funds/shares as one might expect as they are already stored in the order.
- In the UtilityExchange class we add some basic utility beyond the minimum
  required - the ability to cancel orders and the printOrderStack method which
  prints a classic bid ask table for the supplied asset, and adding traders and
  assets. You can supply an optional nums argument to show more or fewer items
  in the order stack table.
- Some examples of simple adaptations you can easily add - storing bid and ask
  order stacks for each asset (this implementation stores one list of all orders
  and fetches from it using conditional list comprehension), generating a
  password for each participant on creation that must be supplied to transact
  using their account, pricing based on spread, transaction fees

## algoExchange.py

- algoExchange.py extends the UtilityExchange class to implement some
  interesting market behaviour analysis

### The Oracle

- We implement an Oracle trader to update a central price for each asset. This
  trader will clear its order book and generate a new order book each tick
  reflecting a liquidity spectrum based on the new oracle price.
- This oracle price is calculated using a method that takes into account how
  liquidity has been taken out of or supplied to the market at the previous
  step.
- To calculate the new price, start with the previous oracle price (X). Then
  calculate Y=(X-the weighted average price of the order book for that asset).
- Note that based on how we generate order books from the oracle, X is equal to
  the the expectation of the weighted average of the order book before taking
  into supplied transactions at the previous tick. So if there are no orders
  supplied, E(Y)=0
- If many buy orders are executed at the previous tick, most of the remaining
  will be sell orders, which have a higher price than X. Hence, Y<0. Conversely,
  if there are many sell orders, Y>0. Take Z=X-Y. If we have many sell orders, Z
  is less than X, hence we are pushing down the price. And by analogy, pushing
  up the price for many buy orders.
- Finally, we adapt this outcome using the parameter alpha, which is basically
  designed to make the liquidity behaviour of this simulated model more like
  real markets.
- Now we model the new oracle price O, as O = W_1(1), a single step "de-limited"
  Wiener process, where the underlying distribution are not unit Gaussian but
  rather with our own supplied drift and vol parameters.
- In summary, we update the oracle price, by first taking into account the
  market demand for the asset, then doing a discrete Wiener-like update.

### Execution testing

- This oracle is intended to model a stock market with many participants,
  creating a realistic (but simple) order book for each asset based on a central
  price truth. This gives us a quasi-realistic simulated market to test
  execution strategies into.
- Of course, this market does not carry the fundamentals, auto-correlations and
  meta-properties of the real stock market, so it is really only useful for
  measuring liquidity related properties. You shouldn't test a trading strategy
  against this, only an execution strategy. And even then this is really an
  educational exercise to illustrate liquidity properties
- We implement TWAP and VWAP strategies
- For experimentation simplicity we call a super method that automatically sets
  both asset count and trader count to 1 for an algoExchange. You can still add
  traders and participants to the exchange, but the intended purpose is to test how trades impact the market
- This is a synchronous exchange so you must supply the orders to execute prior
  to running an oracle loop

### The algorithms

- It's important to understand that this is a synchronous exchange, so if we
  call an algorithm that say runs for 50 ticks, and want to measure slippage of
  that algorithm, we're going to run the exchange loop in the algorithm itself
- This is analogous behaviour to the normal asynchronous behaviour of an
  exchange if you call an API to trade it. The exchange continues to operate in
  parallel with your order execution
- TWAP takes a random parameter, which moves the algo from uniform to a
  completion target reverting algo, where the completion target is the process
  of uniform TWAP
- VWAP we supply a basic default volProfile in the AlgoExchange class, but you
  can supply a vol profile directly into the algo

## Upcoming on this repo

- PIM and AIM algos
- Simulating adaptive market behaviour and implementing IS and AS oriented algos
- Persisting limit orders to correctly execute vs the oracle book
- Modelling oracle volatility as GARCH to provide more realism
- Analysing trading execution under different oracle regimes
- Optimisation algorithms over assets seeking best liquidity options
- Testing market maker strategies
- An asynchronous version allowing dynamic order supply
