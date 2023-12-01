import curses

from pycolab import ascii_art
from pycolab import human_ui
from pycolab.prefab_parts import sprites as prefab_sprites

ACTIONS = {
    'up': 0,
    'down': 1,
    'left': 2,
    'right': 3,
    'stay': 4,
    'interact': 5,
    'quit': 6,
}

KEYS_TO_ACTIONS = {
    curses.KEY_UP: ACTIONS['up'],
    curses.KEY_DOWN: ACTIONS['down'],
    curses.KEY_LEFT: ACTIONS['left'],
    curses.KEY_RIGHT: ACTIONS['right'],
    -1: ACTIONS['stay'],
    ' ': ACTIONS['interact'],
    'q': ACTIONS['quit'],
    'Q': ACTIONS['quit'],
}

# Define a mapping of actions to their opposites
OPPOSITE_ACTIONS = {
    ACTIONS['left']: ACTIONS['right'],
    ACTIONS['right']: ACTIONS['left'],
    ACTIONS['up']: ACTIONS['up'],
    ACTIONS['down']: ACTIONS['down'],
    ACTIONS['stay']: ACTIONS['stay'],
    ACTIONS['interact']: ACTIONS['interact'],
}

FG_COLOURS = {
    'H': (999, 500, 0),    # The human wears an orange jumpsuit.
    'A': (200, 200, 999),  # The AI is blue
    '#': (700, 700, 700),  # Walls, bright grey.
    ' ': (200, 200, 200),  # Floor, black.
}

BG_COLOURS = {
    'H': (200, 200, 200),
    'A': (200, 200, 999),
    '#': (800, 800, 800),
    ' ': (200, 200, 200),
}

class HumanSprite(prefab_sprites.MazeWalker):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character, impassable='#A')

    def update(self, actions, board, layers, backdrop, things, the_plot):
        action = actions

        # Human sprite logic goes here
        if action == ACTIONS['up']:
            self._north(board, the_plot)
        elif action == ACTIONS['down']:
            self._south(board, the_plot)
        elif action == ACTIONS['left']:
            self._west(board, the_plot)
        elif action == ACTIONS['right']:
            self._east(board, the_plot)
        elif action == ACTIONS['stay']:
            self._stay(board, the_plot)
        elif action == ACTIONS['interact']:
            self._interact(board, the_plot)
        elif action == ACTIONS['quit']:
            the_plot.terminate_episode()

    def _interact(self, board, the_plot):
        # Do nothing
        pass

class AISprite(prefab_sprites.MazeWalker):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character, impassable='#H')

    def update(self, actions, board, layers, backdrop, things, the_plot):
        # Get the opposite action
        action = OPPOSITE_ACTIONS.get(actions, ACTIONS['stay'])

        # AI sprite logic goes here
        if action == ACTIONS['up']:
            self._north(board, the_plot)
        elif action == ACTIONS['down']:
            self._south(board, the_plot)
        elif action == ACTIONS['left']:
            self._west(board, the_plot)
        elif action == ACTIONS['right']:
            self._east(board, the_plot)
        elif action == ACTIONS['stay']:
            self._stay(board, the_plot)
        elif action == ACTIONS['interact']:
            self._interact(board, the_plot)

    def _interact(self, board, the_plot):
        # Do nothing
        pass


class SimpleLevel:
    def __init__(self):
        self.level = [
            '############',
            '#          #',
            '#          #',
            '#          #',
            '#          #',
            '#     ##   #',
            '#     ##   #',
            '#          #',
            '#          #',
            '#          #',
            '#H        A#',
            '############'
        ]

    def get_level(self):
        return self.level

def make_game(level):
    return ascii_art.ascii_art_to_game(
        level,
        what_lies_beneath=' ',
        sprites={'H': HumanSprite, 'A': AISprite})


if __name__ == "__main__":
    level = SimpleLevel().get_level()
    game = make_game(level)

    # Make a CursesUi to play it with.
    ui = human_ui.CursesUi(
      keys_to_actions=KEYS_TO_ACTIONS,
      delay=50,
      colour_fg=FG_COLOURS,
      colour_bg=BG_COLOURS)

    # Let the game begin!
    ui.play(game)
