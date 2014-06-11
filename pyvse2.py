# !/usr/bin/env python
# coding: utf-8

"""
    pyvse
    ~~~~~
    A high-level API designed for MarketWatch Virtual Stock Exchange games.

    Author: Kevin Chen
    Email: kvchen@berkeley.edu

    Contributor: Andrew Han
    Email: handrew@stanford.edu
"""

import requests
import re
import json
from datetime import datetime, date, timedelta
from time import mktime
from bs4 import BeautifulSoup
from math import fabs

STOCK_ACTIONS = ["Buy", "Sell", "Short", "Cover"]
TIME_DELAY = 5

BASE_URL = "http://www.marketwatch.com"
ID_URL = "https://id.marketwatch.com"

URL_SUFFIX = {
    "status": BASE_URL + "/user/login/status",
    "profile": BASE_URL + "/my",
    "login": ID_URL + "/auth/submitlogin.json",
    "game": BASE_URL + "/game/{0}",
    "trade": BASE_URL + "/game/{0}/trade?week=1", 
    "submit_order": BASE_URL + "/game/{0}/trade/submitorder?week=1",
    "holdings_info": BASE_URL + "/game/{0}/portfolio/Holdings?partial=True",
    "value": BASE_URL + "/game/{0}/portfolio/Holdings"
}

def mw_url(suffix, *args):
    return URL_SUFFIX[suffix].format(*args)


class VSESession(object):
    def __init__(self, delay = 5):
        """Initializes a VSESession, through which all API calls are routed.

        @param delay: Seconds to delay scraping data to prevent rate-limiting
        """
        self.session = requests.Session()
        self.delay = delay
        self.games = {}

    def login(self, username, password):
        """Logs a VSESession into the Marketwatch VSE.

        @param username: email used with the Marketwatch VSE
        @param password: corresponding password
        """
        userdata = {"username": username, "password": password}

        r = self.session.get(mw_url("login"), params=userdata, verify=True)

        # MarketWatch returns a validation URL, which we visit to complete 
        # the login handshake.
        conf_url = json.loads(r.text)["url"]
        
        try:
            self.session.get(conf_url)
        except requests.exceptions.ConnectionError as e:
            print("An error may occur during day trading. This is normal.")
            print(e.args[0].reason)

        # Confirm that we have logged in successfully
        if self.session.get(mw_url("status")).url != mw_url("profile"):
            print("Invalid username/password combination.")
        else:
            print("Successful login!")

    def game(self, game_id):
        """Returns a Game object.

        @param game_id: 
        """
        if game_id in self.games:
            return self.games[game_id]
        else:
            self.games[game_id] = Game(game_id, self)
            return self.games[game_id]


class Game(object):
    order_headers = {'Content-Type': 'application/json; charset=utf-8'}

    def __init__(self, game_id, vse_session):
        """Creates a Game object, parented to a VSESession."""
        self.game_id = game_id
        self.vse_session = vse_session

        self.positions = {} # array of stock objects
        self.__updatePositions()

    @property
    def value(self):
        r = self.vse_session.session.get(mw_url("value", self.game_id))
        soup = BeautifulSoup(r.text)
        worth = soup.find('ul', {"class": "performance"}).li.find('span', {"class": "data"}).getText()
        worth = worth.replace("$", "").replace(",", "")
        return float(worth)

    def transaction(self, ticker, shares, action):
        """Carries out a transaction on a Stock object.

        @param shares: Number of shares to be exchanged in this transaction.
        @param action: Type of transaction to be carried out.
        """

        stock = self.stock(ticker)

        if action not in STOCK_ACTIONS:
            print("Invalid stock action.")
            return

        payload = [{"Fuid": stock.trading_symbol, 
                    "Shares": str(shares), 
                    "Type": action}]

        p = self.vse_session.session.post(mw_url("submit_order", self.game_id), 
            headers = self.order_headers, data=json.dumps(payload))

        resp = json.loads(p.text)
        if resp["succeeded"] == False:
            print("Transaction for {0} failed. {1}"
                .format(stock.symbol, resp["message"]))
            return

        self.__updatePositions()

    def __getNumberOfSharesToInvest(self, ticker, moneyToSpend):
        obj = self.stock(ticker)
        price = obj.price
        numSharesToInvest = int(moneyToSpend / price)
        return numSharesToInvest

    def rebalance(self, stockWeights):
        self.__updatePositions()
        value = self.value

        if (len(self.positions) == 0):
            for ticker in stockWeights:
                weight = stockWeights[ticker]
                moneyToSpend = weight * value
                numSharesToBuy = self.__getNumberOfSharesToInvest(ticker, moneyToSpend)
                self.transaction(ticker, numSharesToBuy, "Buy")
        else:
            # Note that we are assuming some amount of margin.
            ownedTickers = self.__positionNames()
            targetTickers = list(stockWeights.keys())

            """ Positions we currently have that we need to exit completely """
            for ticker in ownedTickers:
                if ticker not in targetTickers:
                    numSharesOwned = self.positions[ticker].position
                    action = "Sell" if numSharesOwned > 0 else "Cover"
                    numSharesOwned = fabs(numSharesOwned)
                    self.transaction(ticker, numSharesOwned, action)

            self.__updatePositions()

            ############################
            ownedTickers = self.__positionNames()
            targetTickers = list(stockWeights.keys())

            """ Overlap between positions we have a little bit of and need to rebalance """
            for ticker in ownedTickers:
                if ticker in targetTickers:
                    weight = stockWeights[ticker]
                    moneyToInvest = weight * value
                    numSharesToHave = self.__getNumberOfSharesToInvest(ticker, moneyToInvest)
                    currentPosition = self.positions[ticker].position

                    action = "Buy"
                    if (currentPosition < 0):
                        if (numSharesToHave > currentPosition):
                            action = "Cover"
                        else:
                            action = "Short"
                    else:
                        if (numSharesToHave > currentPosition):
                            action = "Buy"
                        else:
                            action = "Sell"

                    difference = fabs(currentPosition - numSharesToHave)

                    self.transaction(ticker, difference, action)

            self.__updatePositions()

            ############################
            ownedTickers = self.__positionNames()
            targetTickers = list(stockWeights.keys())

            """ Positions we don't have that we need to initialize """
            for ticker in targetTickers:
                if ticker not in ownedTickers:
                    weight = stockWeights[ticker]
                    moneyToSpend = weight * value
                    numSharesToBuy = self.__getNumberOfSharesToInvest(ticker, moneyToSpend)
                    self.transaction(ticker, numSharesToBuy, "Buy") 

        self.__updatePositions()

    def __updatePositions(self):
        r = self.vse_session.session.get(mw_url("holdings_info", self.game_id))
        soup = BeautifulSoup(r.text)

        try: 
            allRows = soup.find('table', {'class': 'highlight'}).tbody.findAll('tr')
        except AttributeError:
            allRows = []

        for i in range(0, len(allRows)):
            symbol = allRows[i]['data-ticker']
            trading_symbol = allRows[i]['data-symbol']
            numShares = int(float(allRows[i]['data-shares']))
            tradeType = allRows[i]['data-type']
            
            position = numShares
            if (tradeType == "Short"):
                position = numShares * -1

            stockObj = self.stock(symbol, trading_symbol = trading_symbol, position = position)

            self.positions[symbol] = (stockObj)

    def __positionNames(self):
        return list(self.positions.keys())

    def buy(self, ticker, shares):
        self.transaction(ticker, shares, "Buy")

    def sell(self, ticker, shares):
        self.transaction(ticker, shares, "Sell")

    def short(self, ticker, shares):
        self.transaction(ticker, shares, "Short")

    def cover(self, ticker, shares):
        self.transaction(ticker, shares, "Cover")

    def stock(self, symbol, trading_symbol = None, position = 0):
        return Stock(symbol, trading_symbol, position, self)

""" Really only functions so that we can get trading symbol easily for transactions within the Game object """
class Stock():
    def __init__(self, symbol, trading_symbol, position, game):
        """
        @param symbol: Normal ticker symbol of a stock
        @param trading_symbol: the symbol that Marketwatch uses to trade
        """

        self.symbol = symbol
        self.game = game
        self.trading_symbol = trading_symbol if type(trading_symbol) != type(None) else self.get_trading_symbol()

        self.position = position

    def get_trading_symbol(self):
        payload =  {"search": self.symbol, "view": "grid", "partial": True}
        p = self.game.vse_session.session.post(mw_url("trade", self.game.game_id), params=payload)
        
        data = BeautifulSoup(p.text)

        try:
            symbol = data.find("div", {"class": "chip"})['data-symbol']
        except:
            print "Could not find symbol: %s." % self.symbol
            symbol = ""

        self.trading_symbol = symbol
        return symbol

    # Retrieves the price of a stock by scraping Yahoo! Finance. Returns a float.
    @property
    def price(self):
        standardTicker = self.symbol
        yfID = "yfs_l84_" + standardTicker.lower()
        try:
            yfURL = "http://finance.yahoo.com/quotes/" + standardTicker
            r = requests.get(yfURL)
            soup = BeautifulSoup(r.text)
        except:
            yfURL = "http://finance.yahoo.com/q?s=" + standardTicker + "&ql=1"
            r = requests.get(yfURL)
            soup = BeautifulSoup(r.text)

        try:
            price = soup.find("span", {"id": yfID}).getText()
            price = float(price)
        except AttributeError:
            price = self.retrievePrice()
            
        return price
