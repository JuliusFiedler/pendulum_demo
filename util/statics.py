import pygame

# Organization
GAME_NAME = "Inverses Pendel"

# Display
DISPLAY_SIZE = (1000, 800)
FPS = 60

# paths
arrow_path = "img/arrow.png"
balance_highscore_path = "data/balance_highscore.json"
swingup_highscore_path = "data/swingup_highscore.json"

# colors
BLACK = 0, 0, 0
WHITE = 255, 255, 255
RED = 200, 0, 0
LIGHT_RED = 255, 0, 0
GREEN = 0, 200, 0
LIGHT_GREEN = 0, 255, 0
BLUE = 0, 0, 200
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
