# !/usr/bin/env python
# coding: utf-8

"""
    pyvse
    ~~~~~
    A high-level API designed for MarketWatch Virtual Stock Exchange games.

    Author: Kevin Chen
    Email: kvchen@berkeley.edu
"""

import requests
import re
import json

from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup

from resources.mw_vars import *


class VSESession():
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


class Game():
    order_headers = {'Content-Type': 'application/json; charset=utf-8'}

    def __init__(self, game_id, vse_session):
        """Creates a Game object, parented to a VSESession."""
        self.game_id = game_id
        self.vse_session = vse_session

    def transaction(self, stock, shares, action):
        """Carries out a transaction on a Stock object. Returns True if
        transaction was carried out successfully, and False otherwise.

        @param shares: Number of shares to be exchanged in this transaction.
        @param action: Type of transaction to be carried out.
        """
        if action not in STOCK_ACTIONS:
            print("Invalid stock action.")
            return

        payload = [{"Fuid": stock.symbol, 
                    "Shares": str(shares), 
                    "Type": action}]

        p = self.vse_session.session.post(mw_url("submit_order", self.game_id), 
            headers = self.order_headers, data=json.dumps(payload))

        resp = json.loads(p.text)
        if resp["succeeded"] == False:
            print("Transaction for {0} failed. {1}"
                .format(stock.symbol, resp["message"]))

    def buy(self, stock, shares):
        self.transaction(stock, shares, "Buy")

    def sell(self, stock, shares):
        self.transaction(stock, shares, "Sell")

    def short(self, stock, shares):
        self.transaction(stock, shares, "Short")

    def cover(self, stock, shares):
        self.transaction(stock, shares, "Cover")


class Stock():
    def __init__(self, symbol):
        """
        @param symbol: Trading ticker symbol of a stock
        """

        self.symbol = symbol
        self.trading_symbol = None
        self.cache = {"timestamp": datetime.now(), "data": None}

        # Get the symbol that MarketWatch uses for trading
        self.get_trading_symbol()

        # Fetch initial data
        self.fetch_data()

    def get_trading_symbol(self):
        payload =  {"search": self.symbol, "view": "grid", "partial": "true"}
        

    def fetch_data(self):
        td = datetime.now() - self.cache["timestamp"]
        if td.seconds > 5:
            return self.cache["data"]
        else:
            try:
                r = requests.get(mw_url("stock_info", self.symbol))
                self.cache["timestamp"] = datetime.now()
                self.cache["data"] = BeautifulSoup(r.text)
                return self.cache["data"]

            except Exception as e:
                print("Fetching data for {0} failed. {1}"
                    .format(self.symbol, e))

    @property
    def price(self):
        data = self.fetch_data()
        raw_price = data.find("p", {"class": "data bgLast"})
        return float(raw_price.getText().replace(",", ""))

    @property
    def change(self):
        return

    @property
    def percent(self):
        data = self.fetch_data()
        raw_percent = data.find("span", {"class": "bgPercentChange"})
        return float(raw_percent.getText().replace("%", ""))

    @property
    def volume(self):
        data = self.fetch_data()
        # raw_volume = data.find()
        return
