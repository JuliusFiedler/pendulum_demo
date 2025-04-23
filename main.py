import pygame
import sys
import time
import random
import numpy as np
from ipydex import IPS

pygame.init()

import util.statics as stat
import util.utils as u
from core.loops import HighscoreLoop, GameLoop, IntroLoop


# display
pygame.display.set_caption(stat.GAME_NAME)
game_display = pygame.display.set_mode((stat.DISPLAY_SIZE))

# init stuff
clock = pygame.time.Clock()

balance_highscore_path = "balance_highscore.json"
swingup_highscore_path = "swingup_highscore.json"

# loops
hs_loop = HighscoreLoop(game_display, clock, highscore_path=balance_highscore_path)
game_loop = GameLoop(game_display, clock, highscore_path=balance_highscore_path)
intro_loop = IntroLoop(game_display, clock, game_loop=game_loop.run, hs_loop=hs_loop.run)

# gogo
intro_loop.run()
# game_loop.run()

