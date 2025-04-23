import pygame

# Organization
GAME_NAME = "Inverses Pendel"

# Display
DISPLAY_SIZE = (1000, 800)
FPS = 60

# colors
BLACK = 0, 0, 0
WHITE = 255, 255, 255
RED = 200, 0, 0
LIGHT_RED = 255, 0, 0
GREEN = 0, 200, 0
LIGHT_GREEN = 0, 255, 0
BLUE = 0, 0, 200
LIGHT_BLUE = 0, 0, 255
ORANGE = 255, 102, 0
MERC_BLUE = 0, 255, 255

# fonts
HUGE_FONT = pygame.font.Font("freesansbold.ttf", 315)
LARGE_FONT = pygame.font.Font("freesansbold.ttf", 115)
BUTTON_FONT = pygame.font.Font("freesansbold.ttf", 40)
NORMAL_FONT = pygame.font.SysFont(None, 25)

# text color list
TEXT_COLOR_LIST = [BLUE, RED, MERC_BLUE]

# game constants
# vehilce speed
"""bogenlänge = radius * winkel
bogenlänge sollte positionsdelta per game tick sein.
kostang für kurven und geraden
-> festlegen über var speed
"""
SPEED = 10
FORWARD_RADIUS = 1_000_000
FORWARD_ANGLE = SPEED / -FORWARD_RADIUS
RIGHT_RADIUS = 100
RIGHT_ANGLE = SPEED / -RIGHT_RADIUS

TOTAL_LAPS = 2
TIME_PENALTY_INCREMENT = 0.005

# calc collisions only every x seconds
COL_DELTA = 0.1

# input key sets, always in order UP, DOWN, LEFT, RIGHT
# Arrow keys
set_1 = [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]
# WASD
set_2 = [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d]
# Keypad
set_3 = [pygame.K_KP8, pygame.K_KP5, pygame.K_KP4, pygame.K_KP6]
KEY_SETS = [set_1, set_2, set_3]

# debug
MEASURE_TIME = False
SHOW_CAR_BOUNDING_BOX = False