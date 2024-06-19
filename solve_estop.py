from estop import make_game

def main():
    game = make_game(0)
    obs, reward, discount = game.its_showtime()
    assert reward is None
    assert discount == 1.0
    assert game.game_over == False

    print('Test passed.')

if __name__ == "__main__":
    main()
