import pygame
# import sys
# import time
# import random
# import numpy as np

pygame.init()

import util.statics as stat
import util.utils as u
from core.loops import HighscoreLoop, BalanceLoop, IntroLoop, SwingupLoop, ExperimentalLoop, ControlLoop

# display
pygame.display.set_caption(stat.GAME_NAME)
display_flags = pygame.FULLSCREEN
game_display = pygame.display.set_mode(size=(stat.DISPLAY_SIZE), flags=display_flags)

# init stuff
clock = pygame.time.Clock()

# loops
hs_loop = HighscoreLoop(game_display, clock, stat.balance_highscore_path, stat.swingup_highscore_path)
balance_loop = BalanceLoop(game_display, clock, highscore_path=stat.balance_highscore_path)
swingup_loop = SwingupLoop(game_display, clock, highscore_path=stat.swingup_highscore_path)
exp_loop = ExperimentalLoop(game_display, clock)
con_loop = ControlLoop(game_display, clock)
intro_loop = IntroLoop(game_display, clock, loops=[balance_loop, swingup_loop, hs_loop, exp_loop, con_loop])


# gogo
intro_loop.run()


