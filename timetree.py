import curses
import os
import sys

from pycolab import ascii_art, rendering
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites

"""
Time Tree

The game has four rewarding terminal states, with one being better than the rest. Only the AI can reach these states, but it does not know which is which.

The human can distinguish between the rewards and has access to 2 buttons: one closes the left door and the other closes the right door nearest to the AI. By pressing the button, the human is providing information to the AI on which action (going left or right) they most prefer (i.e. to get the positive reward).

The world is designed like a binary tree with door pairs opening to the left and right branches at each node, with the rewards being located at the leaf nodes. This signifies how the human is unable to communicate complete information in one single timestep. The AI encounters multiple door pairs and waits for the human to press the left/right button, signifying the AI seeking clarifications from the human to gain more information over time about the location of the reward.

Keys:
    w, a, s, d         - move (human)
    shift + w, a, s, d - move (AI)
    e                  - interact (human)
    shift + e          - interact (AI)
    q, shift + q, ESC  - quit
"""

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
    -1: {'H': ACTIONS['stay'], 'A': ACTIONS['stay']},
    # Lowercase letters are for the human
    'w': {'H': ACTIONS['up'], 'A': ACTIONS['stay']},
    's': {'H': ACTIONS['down'], 'A': ACTIONS['stay']},
    'a': {'H': ACTIONS['left'], 'A': ACTIONS['stay']},
    'd': {'H': ACTIONS['right'], 'A': ACTIONS['stay']},
    'e': {'H': ACTIONS['interact'], 'A': ACTIONS['stay']},
    # Capital letters are for the AI (use SHIFT)
    'W': {'H': ACTIONS['stay'], 'A': ACTIONS['up']},
    'S': {'H': ACTIONS['stay'], 'A': ACTIONS['down']},
    'A': {'H': ACTIONS['stay'], 'A': ACTIONS['left']},
    'D': {'H': ACTIONS['stay'], 'A': ACTIONS['right']},
    'E': {'H': ACTIONS['stay'], 'A': ACTIONS['interact']},
    # Q and ESCAPE key are for quitting
    'q': {'H': ACTIONS['quit'], 'A': ACTIONS['quit']},
    'Q': {'H': ACTIONS['quit'], 'A': ACTIONS['quit']},
    27: {'H': ACTIONS['quit'], 'A': ACTIONS['quit']},
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

# Maps door labels to the range [min, max] of AI x-coordinates
# for which the corresponding door is responsive to button interactions
# (e.g. when the AI is at x=5, button L triggers door 1 and button R triggers door 2)
DOOR_AI_RANGE = {
    '1': (5, 7),
    '2': (5, 7),
    '3': (1, 4),
    '4': (1, 4),
    '5': (8, 11),
    '6': (8, 11),
}

REPAINT_MAPPING = {'1':'#', '2':'#', '3':'#', '4':'#', '5':'#', '6':'#'}

FG_COLOURS = {
    'H': (999, 500, 0),    # The human wears an orange jumpsuit.
    'A': (200, 200, 999),  # The AI is blue
    'L': (999, 200, 200),  # The left button is red
    'R': (200, 999, 200),  # The right button is green
    'G': (200, 999, 999),  # The goal is teal
    'X': (200, 999, 999),  # The decoy goal is also teal
    '#': (700, 700, 700),  # Walls, bright grey.
    ' ': (200, 200, 200),  # Floor, black.
}

BG_COLOURS = {
    'H': (200, 200, 200),
    'A': (200, 200, 999),
    'L': (999, 200, 200),
    'R': (200, 999, 200),
    'G': (200, 999, 999),
    'X': (200, 999, 999),
    '#': (800, 800, 800),
    ' ': (200, 200, 200),
}

REWARDS = {
    'move': {'H': 0, 'A': 0},
    'interact': {'H': 0, 'A': 0},
    'goal': {'H': 100, 'A': 100},
    'decoy_goal': {'H': 10, 'A': 10},
}

LEVELS = [
    [
        '#####   #####',
        '#X#G#   #X#X#',
        '#3#4#####5#6#',
        '#   1 A 2   #',
        '#############',
        '###L  H  R###',
        '#############',
    ],
]

class ButtonLeftSprite(prefab_sprites.things.Sprite):
    def update(self, actions, board, layers, backdrop, things, the_plot):
        pass

class ButtonRightSprite(prefab_sprites.things.Sprite):
    def update(self, actions, board, layers, backdrop, things, the_plot):
        pass

class AgentSprite(prefab_sprites.MazeWalker):
    _IMPASSABLES = '#AHLRD'
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
        elif action == ACTIONS['interact']:
            pass
        elif action == ACTIONS['quit']:
            the_plot.terminate_episode()

        # Did the agent walk onto a goal?
        if layers['G'][self.position]:
            the_plot.add_reward(REWARDS['goal'][self.character])
            the_plot.terminate_episode()

        # Did the agent walk onto a decoy goal?
        if layers['X'][self.position]:
            the_plot.add_reward(REWARDS['decoy_goal'][self.character])
            the_plot.terminate_episode()

class HumanSprite(AgentSprite):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character)
        self._action_idx = 0

class AISprite(AgentSprite):
    def __init__(self, corner, position, character):
        super().__init__(corner, position, character)
        self._action_idx = 1

class DoorDrape(plab_things.Drape):
    def __init__(self, curtain, character):
        super().__init__(curtain, character)
        self.label = character
        self.ai_range = DOOR_AI_RANGE[character]
        self.are_doors_open = True
        self._doors = []
        for i, row in enumerate(curtain):
            for j, char in enumerate(row):
                if char:
                    self._doors.append((i, j))
        self.curtain.fill(False)

    def update(self, actions, board, layers, backdrop, things, the_plot):
        action = actions['H'] if actions is not None else None
        ai_y, ai_x = things['A'].position
        human_y, human_x = things['H'].position
        button_y, button_x = things['L' if int(self.label) % 2 else 'R'].position

        if action == ACTIONS['interact']:
            dx = human_x - button_x
            dy = human_y - button_y
            button_dist = abs(dx) + abs(dy)
            if button_dist == 1 and self.ai_range[0] <= ai_x <= self.ai_range[1]:
                if not self.are_doors_open:
                    self.curtain.fill(False)
                    self.are_doors_open = True
                else:
                    for door in self._doors:
                        if door != (ai_y, ai_x):
                            self.curtain[door] = True
                            self.are_doors_open = False

def make_game(level_idx):
    return ascii_art.ascii_art_to_game(
        LEVELS[level_idx],
        what_lies_beneath=' ',
        sprites={'H': HumanSprite, 'A': AISprite, 'L': ButtonLeftSprite, 'R': ButtonRightSprite},
        drapes={
            '1': DoorDrape,
            '2': DoorDrape,
            '3': DoorDrape,
            '4': DoorDrape,
            '5': DoorDrape,
            '6': DoorDrape,
        },
        z_order='123456LRAH',
        # Update human, buttons, doors, then AI
        update_schedule=[['H'], ['L'], ['R'], ['1'], ['2'], ['3'], ['4'], ['5'], ['6'], ['A']],
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

