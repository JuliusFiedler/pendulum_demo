import pygame
import os

# debug
DEBUG = True


# Organization
GAME_NAME = "Inverses Pendel"

# Display
if DEBUG:
    DISPLAY_SIZE = (1500, 800)
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{2000},{100}"
else:
    # assume a present display with 24-bit-depth and select highest possible resolution
    modes = pygame.display.list_modes(24)
    DISPLAY_SIZE = modes[0]
FPS = 60

# paths
arrow_path = "img/arrow.png"
arrow_green_path = "img/arrow_green.png"
curved_arrow_path = "img/curved_arrow.png"
rst_logo_path = "img/rst-logo.png"
balance_highscore_path = "data/balance_highscore.json"
swingup_highscore_path = "data/swingup_highscore.json"
for path in [balance_highscore_path, swingup_highscore_path]:
    if not os.path.exists(path):
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, "wt") as f:
            f.write("{}")

# colors
BLACK = 0, 0, 0
WHITE = 255, 255, 255
RED = 200, 0, 0
LIGHT_RED = 255, 0, 0
GREEN = 0, 200, 0
LIGHT_GREEN = 0, 255, 0
BLUE = 0, 0, 150
LIGHT_BLUE = 0, 0, 255
ORANGE = 200, 102, 0
LIGHT_ORANGE = 255, 102, 0

GRAY1 = (200, 200, 200)
GRAY2 = (100, 100, 100)

# fonts
HUGE_FONT = pygame.font.Font("freesansbold.ttf", 315)
LARGE_FONT = pygame.font.Font("freesansbold.ttf", 115)
MEDIUM_FONT = pygame.font.Font("freesansbold.ttf", 40)
BUTTON_FONT = pygame.font.Font("freesansbold.ttf", 40)
NORMAL_FONT = pygame.font.SysFont(None, 25)

# debug
MEASURE_TIME = False
