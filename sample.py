import pyvse

if __name__ == "__main__":
    username = "foo@bar.baz"
    password = "hunter2"

    my_session = pyvse.VSESession()
    my_session.login(username, password)

    my_game = my_session.game("mygamename")

    goog = pyvse.Stock("STOCK-NSQ-GOOG")
    my_game.buy(goog, 500)