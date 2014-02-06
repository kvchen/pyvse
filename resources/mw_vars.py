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
    "stock_info": BASE_URL + "/investing/stock/{0}",
    
}

def mw_url(suffix, *args):
    return URL_SUFFIX[suffix].format(*args)