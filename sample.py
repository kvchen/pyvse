import pyvse

if __name__ == "__main__":
    username = "foo@bar.baz"
    password = "hunter2"

    my_session = pyvse.VSESession(username, password)
    my_game = pyvse.Game("mygamename", my_session)

    goog = pyvse.Stock("STOCK-NSQ-GOOG")
    my_game.buy(goog, 500)