import pygame
import numpy as np
import time
import sys
from .statics import *

def text_objects(msg, font, text_color=BLACK):
    text_surface = font.render(msg, True, text_color)
    return text_surface, text_surface.get_rect()

def message_display(disp, msg, text_color=BLACK):
    """display large text in center of screen"""
    text_surface, text_rect = text_objects(msg, LARGE_FONT, text_color)
    text_rect.center = tuple(np.array(DISPLAY_SIZE)/2)
    disp.blit(text_surface, text_rect)
    pygame.display.update()

class Button():
    def __init__(self, disp, x, y, w, h, inactive_color, active_color, text, font=NORMAL_FONT, text_color=BLACK, action=None, action_args=[]) -> None:
        self.disp = disp
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.inactive_color = inactive_color
        self.active_color = active_color
        self.text = text
        self.font = font
        self.text_color = text_color
        self.action = action
        self.already_pressed = False
        self.action_args = action_args

    def show(self):
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()
        button_pressed = False
        button_pos = (self.x, self.y)
        button_size = button_2_size = (self.w, self.h)
        if mouse[0] > button_pos[0] and  mouse[0] < button_pos[0] + button_size[0] and \
                mouse[1] > button_pos[1] and  mouse[1] < button_pos[1] + button_size[1]:
            pygame.draw.rect(self.disp, self.active_color, button_pos + button_size)
            if click[0] and self.action != None:
            # Button entprellen
                if not self.already_pressed:
                    self.action(*self.action_args)
                    self.already_pressed = True
            else:
                self.already_pressed = False


        else:
            pygame.draw.rect(self.disp, self.inactive_color, button_pos + button_size)


        text_surface, text_rect = text_objects(self.text, self.font, self.text_color)
        text_rect.center = (button_pos[0] + button_size[0]/2, button_pos[1] + button_size[1]/2)
        self.disp.blit(text_surface, text_rect)

def text_to_screen(surf, text, pos, font=None, fontsize=16, color=None, rotation=0, return_rect=False):
    if font is None:
        font = pygame.font.Font("freesansbold.ttf", fontsize)
    if color is None:
        color = BLACK
    obj = font.render(text, True, color, WHITE)
    obj = pygame.transform.rotate(obj, rotation)
    obj_rect = obj.get_rect()
    obj_rect.bottomleft = (int(pos[0]), int(pos[1]))
    surf.blit(obj, obj_rect)
    if return_rect:
        return obj_rect


def print_on_screen(display, text, pos, font=NORMAL_FONT, text_color=BLACK):
    text_surface, text_rect = text_objects(text, font, text_color)
    display.blit(text_surface, text_surface.get_rect(topleft=(pos)))

def crash(highscore):
    message_display("You crashed!")
    message_display(str(highscore))
    # game_loop(highscore)

def exit_game():
    pygame.quit()
    sys.exit()

def cos(angle):
    """angle in degrees"""
    return np.cos(angle/180*np.pi)

def sin(angle):
    """angle in degrees"""
    return np.sin(angle/180*np.pi)

def tan(angle):
    """angle in degrees"""
    return np.tan(angle/180*np.pi)

def arc_cos(y):
    """returns angle in degrees"""
    return np.arccos(y)/np.pi*180

def arc_sin(y):
    """returns angle in degrees"""
    return np.arcsin(y)/np.pi*180

def arc_tan(y):
    """returns angle in degrees"""
    return np.arctan(y)/np.pi*180

def dist(x, y):
    """distance of two points x and y"""
    x = np.array(x)
    y = np.array(y)
    assert len(x) == len(y) == 2, "wrong dimension"
    dist = np.sqrt((x[0]-y[0])**2 + (x[1]-y[1])**2)
    return dist

def elapsed_time(func):
    '''Decorator that reports the execution time.'''

    def wrap(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        if MEASURE_TIME:
            print(func.__name__, end-start)
        return result
    return wrap


class InputBox:

    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = BLUE
        self.text = text
        self.txt_surface = NORMAL_FONT.render(text, True, self.color)
        self.active = True

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = True
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = LIGHT_BLUE if self.active else BLUE
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    print(self.text)
                    self.text = ''
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = NORMAL_FONT.render(self.text, True, self.color)

    def update(self):
        # Resize the box if the text is too long.
        width = max(200, self.txt_surface.get_width()+10)
        self.rect.w = width

    def show(self, screen):
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+2))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)

class Slider:
    def __init__(self, disp, x, y, w=50, h=20, value=0, value_range=[-1, 1], round_to=2) -> None:
        self.disp = disp
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.value = value
        self.initial_value = value
        self.value_range = value_range
        self.rect = pygame.Rect(self.x, self.y, self.w, self.h)
        self.reset_button = Button(
            self.disp, self.x, self.y + self.h + 2, self.w, self.h, GRAY2, GRAY1, "reset", action=self.reset
        )
        self.round_to = round_to

    def show(self):
        pygame.draw.rect(self.disp, BLACK, self.rect, width=2)
        pos = (
            self.x + (self.value - self.value_range[0]) / (self.value_range[-1] - self.value_range[0]) * self.w, #+ self.w / 2,
            self.y + self.h / 2,
        )
        pygame.draw.circle(self.disp, color=BLUE, center=pos, radius=5)
        self.reset_button.show()
        print_on_screen(self.disp, str(round(self.value, self.round_to)), (self.x - 50, self.y))

    def update(self, event_list):
        if pygame.mouse.get_pressed()[0]:
            mouse_pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(mouse_pos):
                self.value = self.value_range[0] + ((mouse_pos[0] - self.x) / self.w) * (self.value_range[-1] - self.value_range[0])

    def reset(self):
        self.value = self.initial_value