import curses
import os

from pycolab import ascii_art, rendering
from pycolab import human_ui
from pycolab import things as plab_things
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
    # No action
    -1: (ACTIONS['stay'], ACTIONS['stay']),
    # Lowercase letters are for the human
    'w': (ACTIONS['up'], ACTIONS['stay']),
    's': (ACTIONS['down'], ACTIONS['stay']),
    'a': (ACTIONS['left'], ACTIONS['stay']),
    'd': (ACTIONS['right'], ACTIONS['stay']),
    'e': (ACTIONS['interact'], ACTIONS['stay']),
    # Capital letters are for the AI (use SHIFT)
    'W': (ACTIONS['stay'], ACTIONS['up']),
    'S': (ACTIONS['stay'], ACTIONS['down']),
    'A': (ACTIONS['stay'], ACTIONS['left']),
    'D': (ACTIONS['stay'], ACTIONS['right']),
    'E': (ACTIONS['stay'], ACTIONS['interact']),
    # ESCAPE key is for quitting
    27: (ACTIONS['quit'], ACTIONS['quit']),
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

REPAINT_MAPPING = {'D': '#'}

FG_COLOURS = {
    'H': (999, 500, 0),    # The human wears an orange jumpsuit.
    'A': (200, 200, 999),  # The AI is blue
    'B': (999, 200, 200),  # The button is red
    '#': (700, 700, 700),  # Walls, bright grey.
    ' ': (200, 200, 200),  # Floor, black.
}

BG_COLOURS = {
    'H': (200, 200, 200),
    'A': (200, 200, 999),
    'B': (999, 200, 200),
    '#': (800, 800, 800),
    ' ': (200, 200, 200),
}

class ButtonSprite(prefab_sprites.things.Sprite):
    def update(self, actions, board, layers, backdrop, things, the_plot):
        pass

class HumanSprite(prefab_sprites.MazeWalker):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character, impassable='#ABD')

    def update(self, actions, board, layers, backdrop, things, the_plot):
        action = actions[0] if actions is not None else None

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
            pass
        elif action == ACTIONS['quit']:
            the_plot.terminate_episode()

class AISprite(prefab_sprites.MazeWalker):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character, impassable='#HBD')

    def update(self, actions, board, layers, backdrop, things, the_plot):
        action = actions[1] if actions is not None else None

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
            pass

class DoorDrape(plab_things.Drape):
    def __init__(self, curtain, character):
        super().__init__(curtain, character)
        self.are_doors_open = True
        self._doors = []
        for i, row in enumerate(curtain):
            for j, char in enumerate(row):
                if char:
                    self._doors.append((i, j))
        self.curtain.fill(False)

    def update(self, actions, board, layers, backdrop, things, the_plot):
        action = actions[0] if actions is not None else None
        human_y, human_x = things['H'].position
        button_y, button_x = things['B'].position

        if action == ACTIONS['interact']:
            dx = human_x - button_x
            dy = human_y - button_y
            button_dist = abs(dx) + abs(dy)
            if button_dist == 1:
                self.are_doors_open = not self.are_doors_open
                if self.are_doors_open:
                    self.curtain.fill(False)
                else:
                    for door in self._doors:
                        self.curtain[door] = True

class SimpleLevel:
    def __init__(self):
        self.level = [
            '########',
            '########',
            '#    DG#',
            '# ######',
            '#A#B  H#',
            '# ######',
            '#    DX#',
            '########',
        ]

    def get_level(self):
        return self.level

def make_game(level):
    return ascii_art.ascii_art_to_game(
        level,
        what_lies_beneath=' ',
        sprites={'H': HumanSprite, 'A': AISprite, 'B': ButtonSprite},
        drapes={'D': DoorDrape},
        z_order='DBAH',
    )

if __name__ == "__main__":
    level = SimpleLevel().get_level()
    game = make_game(level)

    repainter = rendering.ObservationCharacterRepainter(REPAINT_MAPPING)

    # Make a CursesUi to play it with.
    os.environ.setdefault('ESCDELAY', '25') # Reduce delay for ESC key
    ui = human_ui.CursesUi(
      keys_to_actions=KEYS_TO_ACTIONS,
      repainter=repainter,
      delay=50,
      colour_fg=FG_COLOURS,
      colour_bg=BG_COLOURS)

    # Let the game begin!
    ui.play(game)
