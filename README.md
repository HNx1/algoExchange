# miniExchange

### Summary

- A light-weight Exchange class that allows bid-ask
  trading of a number of assets between a number of participants
- It supports market and limit orders and fund availability checks

### Interpretation

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
  required - the ability to cancel orders and the getOrderStack method which
  prints a classic bid ask table for the supplied asset. You can supply an
  optional nums argument to show more or fewer items in the table.
- Some examples of simple adaptations you can easily add - storing bid and ask
  order stacks for each asset (this implementation stores one list of all orders
  and fetches from it using conditional list comprehension), adding new assets
  or traders to an existing Exchange, generating a password for each participant on creation that must be supplied to transact using their account, pricing based on spread, transaction fees, a central oracle with unlimited funds that generates a random price series for each assets and hits orders relative to the oracle price
