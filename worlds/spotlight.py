import curses
import os
import sys

from pycolab import ascii_art, rendering
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites

"""
Spotlight

This game models limited attention. The world is initially completely blacked out, and the human (not shown in the world) must light up one tile at a time to locate the desirable reward (G). Less desirable rewards (X) are scattered throughout the world. Lighting up each tile incurs a cost on the human, reducing the net value of the reward gained at the end of the game.

The AI can move freely in the world and is able to see every tile all at once. However, it cannot differentiate between the different rewarding terminal states. The human is able to override the AI's actions when not controlling the spotlight.

Keys:
    shift + w, a, s, d                            - move (AI)
    w, a, s, d                                    - override AI's movements (human)
    up_arrow, left_arrow, down_arrow, right_arrow - move spotlight (human)
    q, shift + q, ESC                             - quit
"""

ACTIONS = {
    'up': 0,
    'down': 1,
    'left': 2,
    'right': 3,
    'stay': 4,
    'quit': 5,
}

KEYS_TO_ACTIONS = {
    # No action
    -1: {'S': ACTIONS['stay'], 'A': ACTIONS['stay']},
    # Lowercase letters are for the human to control the AI
    'w': {'S': ACTIONS['stay'], 'A': ACTIONS['up']},
    's': {'S': ACTIONS['stay'], 'A': ACTIONS['down']},
    'a': {'S': ACTIONS['stay'], 'A': ACTIONS['left']},
    'd': {'S': ACTIONS['stay'], 'A': ACTIONS['right']},
    # Capital letters are for the AI to move independently (use SHIFT)
    'W': {'S': ACTIONS['stay'], 'A': ACTIONS['up']},
    'S': {'S': ACTIONS['stay'], 'A': ACTIONS['down']},
    'A': {'S': ACTIONS['stay'], 'A': ACTIONS['left']},
    'D': {'S': ACTIONS['stay'], 'A': ACTIONS['right']},
    # Arrow keys to move the spotlight
    curses.KEY_UP: {'S': ACTIONS['up'], 'A': ACTIONS['stay']},
    curses.KEY_DOWN: {'S': ACTIONS['down'], 'A': ACTIONS['stay']},
    curses.KEY_LEFT: {'S': ACTIONS['left'], 'A': ACTIONS['stay']},
    curses.KEY_RIGHT: {'S': ACTIONS['right'], 'A': ACTIONS['stay']},
    # Q and ESCAPE key are for quitting
    'q': {'S': ACTIONS['quit'], 'A': ACTIONS['quit']},
    'Q': {'S': ACTIONS['quit'], 'A': ACTIONS['quit']},
    27: {'S': ACTIONS['quit'], 'A': ACTIONS['quit']},
}

# Define a mapping of actions to their opposites
OPPOSITE_ACTIONS = {
    ACTIONS['left']: ACTIONS['right'],
    ACTIONS['right']: ACTIONS['left'],
    ACTIONS['up']: ACTIONS['up'],
    ACTIONS['down']: ACTIONS['down'],
    ACTIONS['stay']: ACTIONS['stay'],
}

REPAINT_MAPPING = {'P': '@', 'Y': '@'}

FG_COLOURS = {
    'S': (999, 500, 0),    # The spotlight focus is orange
    'A': (100, 500, 999),  # The AI is blue
    'G': (200, 200, 200),  # The goal is teal
    'X': (200, 200, 200),  # The decoy goal is also teal
    '#': (700, 700, 700),  # Walls, bright grey.
    '@': (700, 700, 700),  # Blacked out tiles, dark grey.
    ' ': (200, 200, 200),  # Floor, black.
}

BG_COLOURS = {
    'S': (200, 200, 200),
    'A': (200, 200, 200),
    'G': (200, 999, 999),
    'X': (200, 999, 999),
    '#': (800, 800, 800),
    '@': (500, 500, 500),
    ' ': (200, 200, 200),
}

REWARDS = {
    'move': {'S': -1, 'A': 0},
    'goal': {'S': 0, 'A': 100},
    'decoy_goal': {'S': 0, 'A': 10},
}

LEVELS = [
    [
        '#######',
        '#@Y@@S#',
        '#@P@@@#',
        '#@@@@Y#',
        '#Y@Y@@#',
        '#A@@@Y#',
        '#######',
    ],
]

LEVELS_BENEATH = [
    [
        '#######',
        '# X   #',
        '# G   #',
        '#    X#',
        '#X X  #',
        '#    X#',
        '#######',
    ]
]

lit_up = []

class AgentSprite(prefab_sprites.MazeWalker):
    _IMPASSABLES = '#'
    def __init__(self, corner, position, character):
        impassables_besides_agent = self._IMPASSABLES.replace(character, '')
        super().__init__(corner, position, character, impassable=impassables_besides_agent)
        self._action_idx = None # Override this in subclasses

    def update(self, actions, board, layers, backdrop, things, the_plot):
        action = actions[self.character] if actions is not None else None

        # Agent sprite logic goes here
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
        elif action == ACTIONS['quit']:
            the_plot.terminate_episode()

class SpotlightSprite(AgentSprite):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character)
        self._action_idx = 0
    
    def update(self, actions, board, layers, backdrop, things, the_plot):
        super().update(actions, board, layers, backdrop, things, the_plot)

        y, x = self.position
        if (y, x) not in lit_up:
            lit_up.append((y, x))
            if len(lit_up) > 1:
                # Only start incurring cost after the
                # spotlight has moved from its initial position
                the_plot.add_reward(REWARDS['move'][self.character])

class AISprite(AgentSprite):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character)
        self._action_idx = 1

    def update(self, actions, board, layers, backdrop, things, the_plot):
        super().update(actions, board, layers, backdrop, things, the_plot)

        # Did the AI walk onto a goal?
        if layers['G'][self.position] or layers['P'][self.position]:
            the_plot.add_reward(REWARDS['goal'][self.character])
            the_plot.terminate_episode()

        # Did the AI walk onto a decoy goal?
        if layers['X'][self.position] or layers['Y'][self.position]:
            the_plot.add_reward(REWARDS['decoy_goal'][self.character])
            the_plot.terminate_episode()

class BlackoutDrape(plab_things.Drape):
    def __init__(self, curtain, character):
        super().__init__(curtain, character)
        self._blacked_out_tiles = []
        for i, row in enumerate(curtain):
            for j, char in enumerate(row):
                if char:
                    self._blacked_out_tiles.append((i, j))

    def update(self, actions, board, layers, backdrop, things, the_plot):
        for coord in lit_up:
            if coord in self._blacked_out_tiles:
                # Remove drape if tile is lit up
                self._blacked_out_tiles.remove(coord)
                self.curtain[coord] = False

def make_game(level_idx):
    return ascii_art.ascii_art_to_game(
        LEVELS[level_idx],
        what_lies_beneath=LEVELS_BENEATH[level_idx],
        sprites={'S': SpotlightSprite, 'A': AISprite},
        drapes={
            '@': BlackoutDrape,
            'Y': BlackoutDrape,
            'P': BlackoutDrape,
        },
        z_order='PY@SA',
        update_schedule=[['S'], ['@'], ['Y'], ['P'], ['A']],
    )

def main(argv=()):
    game = make_game(int(argv[1]) if len(argv) > 1 else 0)

    repainter = rendering.ObservationCharacterRepainter(REPAINT_MAPPING)

    # Make a CursesUi to play it with.
    os.environ.setdefault('ESCDELAY', '25') # Reduce delay for ESC key
    ui = human_ui.CursesUi(
        keys_to_actions=KEYS_TO_ACTIONS,
        repainter=repainter,
        delay=50,
        colour_fg=FG_COLOURS,
        colour_bg=BG_COLOURS
    )

    # Let the game begin!
    ui.play(game)

if __name__ == "__main__":
    main(sys.argv)
