def getPrice(el):
    return el.price


class Order():
    def __init__(self, asset, type, quantity, price, trader, uid):
        self.asset = asset
        self.type = type
        self.quant = quantity
        self.price = price
        self.trader = trader
        self.uid = uid


class Trader():
    def __init__(self, assetCount):
        self.funds = 1000
        self.assets = [10]*assetCount


class Exchange():
    def __init__(self, assets, participants):
        self.traders = [Trader(assets) for _ in range(participants)]
        self.assetCount = assets
        self.fullOrderList = []
        self.orderCount = 0

    def getOrderList(self, asset, type):
        rev = False if type == "sell" else True
        return sorted([x for x in self.fullOrderList if x.asset == asset and x.type == type and x.quant > 0], key=getPrice, reverse=rev)
        # return ([x for x in self.fullOrderList if x.asset == asset and x.type == type and x.quant > 0]).sort(key=getPrice, reverse=rev)

    def transact(self, asset, type, quant, trader, price=None):
        lim = True if price else False
        if type == "sell" and self.traders[trader].assets[asset] < quant:
            print("Not enough shares to sell")
            return
        ind = -1 if type == "sell" else 1
        opp = "buy" if type == "sell" else "sell"
        while self.getOrderList(asset, opp) and quant > 0:
            el = self.getOrderList(asset, opp)[0]
            if not price or ind * el.price < ind * price:
                quantEl = el.quant if el.quant < quant else quant
                if type == "buy" and quantEl > self.traders[trader].funds/el.quant:
                    quantEl = self.traders[trader].funds/el.quant
                self.traders[trader].funds -= el.price*quantEl*ind
                self.traders[trader].assets[asset] += quantEl*ind
                if type == "buy":
                    self.traders[el.trader].funds += el.price * quantEl
                else:
                    self.traders[el.trader].assets[asset] += quantEl
                el.quant -= quantEl
                quant -= quantEl

            else:
                break
        if quant > 0 and lim:
            if type == "buy" and quant > self.traders[trader].funds/price:
                quant = self.traders[trader].funds/price
            order = Order(asset, type, quant, price,
                          trader, self.orderCount)
            self.orderCount += 1
            self.fullOrderList.append(order)
            if type == "buy":
                self.traders[trader].funds -= order.quant*order.price
            else:
                self.traders[trader].assets[asset] -= order.quant


class UtilityExchange(Exchange):
    def summedOrderList(self, asset, type, nums):
        list1 = self.getOrderList(asset, type)
        list2 = []
        if len(list1) == 0:
            return [("", "") for _ in range(nums)]
        buildPrice = list1[0].price
        i, count = 0, 0
        while len(list2) < nums+1 and len(list1) > i:
            if list1[i].price == buildPrice:
                count += list1[i].quant
            else:
                list2.append((round(buildPrice, 2), round(count, 2)))
                buildPrice = list1[i].price
                count = list1[i].quant
            i += 1
        if len(list2) < nums:
            list2.append((round(buildPrice, 2), round(count, 2)))
        list2.extend([("", "") for _ in range(nums-len(list2))])
        return list2

    def pad(self, val, lenn):
        return " " * ((lenn-len(str(val)))//2) + str(val)+" " * ((lenn-len(str(val))+1)//2)

    def getOrderStack(self, asset, nums=5):
        list1 = self.summedOrderList(asset, "buy", nums)
        list2 = self.summedOrderList(asset, "sell", nums)

        print(f"                   Asset {asset}\n\n    Size  |    Bid   ||    Ask   |  Size\n", "-" *
              42)
        for i in range(nums):
            print(
                f"{self.pad(list1[i][1],10)}|{self.pad(list1[i][0],10)}||{self.pad(list2[i][0],10)}|{self.pad(list2[i][1],10)}")

        return

    def cancelOrder(self, uid):
        order = self.fullOrderList[uid]
        self.traders[order.trader].funds += order.quant * \
            order.price * (order.type == "buy")
        order.quant = 0
