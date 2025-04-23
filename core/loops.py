from abc import abstractmethod
import pygame
from pygame import gfxdraw
import numpy as np
import math
import sys, os
from scipy.integrate import solve_ivp
import time
from ipydex import IPS
import json
import bisect

import util.statics as stat
import util.utils as u




class Loop():
    def __init__(self, game_display, clock) -> None:
        self.display = game_display
        self.clock = clock
        # define fps
        self.clock.tick(stat.FPS)
        self.row_template = "{:<2}.: {:<5} s,   {}"

    @abstractmethod
    def run(self):
        pass

    def sorting_function(self, item):
        return item[1]

class IntroLoop(Loop):
    def __init__(self, game_display, clock, game_loop, hs_loop) -> None:
        super().__init__(game_display, clock)
        self.game_loop = game_loop
        self.hs_loop = hs_loop
        from_border_x = 150
        from_border_y = 250
        self.button_1_size = self.button_2_size = (400, 50)
        self.button_1_pos = (from_border_x, stat.DISPLAY_SIZE[1] - from_border_y)
        self.button_2_pos = (stat.DISPLAY_SIZE[0] - from_border_x-self.button_2_size[0], stat.DISPLAY_SIZE[1] - from_border_y)




    def run(self):
        b_stabilize = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1], self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Balancieren", stat.BUTTON_FONT, action=self.game_loop)
        b_multi = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1]+self.button_1_size[1]+5, self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Aufschwingen", stat.BUTTON_FONT, action=self.game_loop)
        b_hs = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1]+(self.button_1_size[1]+5)*2, self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Highscore", stat.BUTTON_FONT, action=self.hs_loop)
        b2 = u.Button(self.display, self.button_2_pos[0], self.button_2_pos[1], self.button_2_size[0], self.button_2_size[1], \
                stat.RED, stat.LIGHT_RED, "Exit", stat.BUTTON_FONT, action=u.exit_game)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()


            self.display.fill(stat.WHITE)

            text_surface, text_rect = u.text_objects(stat.GAME_NAME, stat.LARGE_FONT)
            text_rect.center = (stat.DISPLAY_SIZE[0] / 2, stat.DISPLAY_SIZE[1] / 3)
            self.display.blit(text_surface, text_rect)


            # buttons
            b_stabilize.show()
            b_multi.show()
            b_hs.show()
            # b2.show()


            pygame.display.update()


class GameLoop(Loop):
    def __init__(self, game_display, clock, highscore_path) -> None:
        super().__init__(game_display, clock)

        # physics
        self.gravity = 9.8
        self.masscart = 1.0
        self.masspole = 0.1
        self.total_mass = self.masspole + self.masscart
        self.length = 1  # actually half the pole's length
        #! pole has length 2*l
        self.polemass_length = self.masspole * self.length
        self.force_mag = 10.0
        self.tau = 0.01  # seconds between state updates
        self.kinematics_integrator = "solve_ivp"  # "euler"
        self.F = 10

        # Angle at which to fail the episode
        self.theta_threshold_radians = 90 * 2 * math.pi / 360
        self.x_threshold = 2.16

        self.highscore_path = highscore_path

        self.max_tries = 2

        self.init()

    def init(self):
        self.next_action = 0
        self.t0 = time.time()

        self.state = None
        self.action = None
        self.exit = False

        self.times = []
        self.current_best = 0
        self.number_of_tries = 0
        self.countdown = False
        self.countdown_start = None

        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)
        player, p_time = sorted(self.highscore_dict.items(), key=self.sorting_function, reverse=True)[0]
        self.highscore = f"{np.round(p_time, 1)} s, von {player}"
        self.reset()

    def calc_new_state(self, action):
        x, x_dot, theta, theta_dot = self.state
        # based on mathematical pendulum

        def rhs(t, state):
            x, x_dot, theta, theta_dot = state
            x1, x2, x3, x4 = x, theta, x_dot, theta_dot  # change order
            g = self.gravity
            l = self.length
            m1 = self.masscart
            m2 = self.masspole
            u1 = action
            dx1_dt = x3
            dx2_dt = x4
            dx3_dt = (-g * m2 * np.sin(2 * x2) / 2 + l * m2 * theta_dot**2 * np.sin(x2) + u1) / (
                m1 + m2 * np.sin(x2) ** 2
            )
            dx4_dt = (g * (m1 + m2) * np.sin(x2) - (l * m2 * theta_dot**2 * np.sin(x2) + u1) * np.cos(x2)) / (
                l * (m1 + m2 * np.sin(x2) ** 2)
            )

            return [dx1_dt, dx3_dt, dx2_dt, dx4_dt]  # change order back

        tt = np.linspace(0, self.tau, 2)
        xx0 = np.array(self.state).flatten()
        s = solve_ivp(rhs, (0, self.tau), xx0, t_eval=tt)

        x, x_dot, theta, theta_dot = s.y[:, -1].flatten()

        state = (x, x_dot, theta, theta_dot)
        return state

    def step(self):
        action = self.next_action
        self.action = action
        if not self.countdown:
            self.state = self.calc_new_state(action)
        self.render()
        x, x_dot, theta, theta_dot = self.state
        terminated = bool(
            x < -self.x_threshold
            or x > self.x_threshold
            or theta < -self.theta_threshold_radians
            or theta > self.theta_threshold_radians
        )

        return self.state, 0, terminated, False, {}

    def reset(self):
        self.times.append(time.time()- self.t0)
        self.current_best = max(self.times)

        # random state
        self.state = [0, 0, (np.random.random()-0.5)*0.1, 0]
        # self.state = [2.16, 0, 0, 0]
        self.number_of_tries += 1
        self.countdown_start = time.time()
        self.countdown = True
        self.render()

        if self.number_of_tries >= self.max_tries:
            self.exit = True

    def render(self):

        world_width = self.x_threshold * 2
        scale = stat.DISPLAY_SIZE[0] / world_width
        polewidth = 10.0
        polelen = scale * (2 * self.length)
        cartwidth = 50.0
        cartheight = 30.0

        if self.state is None:
            return None

        x = self.state

        self.surf = pygame.Surface(stat.DISPLAY_SIZE)
        self.surf.fill((255, 255, 255))

        l, r, t, b = -cartwidth / 2, cartwidth / 2, cartheight / 2, -cartheight / 2
        axleoffset = cartheight / 4.0
        cartx = x[0] * scale + stat.DISPLAY_SIZE[0] / 2.0  # MIDDLE OF CART
        carty = 100  # TOP OF CART
        cart_coords = [(l, b), (l, t), (r, t), (r, b)]
        cart_coords = [(c[0] + cartx, c[1] + carty) for c in cart_coords]
        gfxdraw.aapolygon(self.surf, cart_coords, (0, 0, 0))
        gfxdraw.filled_polygon(self.surf, cart_coords, (0, 0, 0))

        l, r, t, b = (
            -polewidth / 2,
            polewidth / 2,
            polelen - polewidth / 2,
            -polewidth / 2,
        )

        pole_coords = []
        for coord in [(l, b), (l, t), (r, t), (r, b)]:
            coord = pygame.math.Vector2(coord).rotate_rad(-x[2])
            coord = (coord[0] + cartx, coord[1] + carty + axleoffset)
            pole_coords.append(coord)
        gfxdraw.aapolygon(self.surf, pole_coords, (202, 152, 101))
        gfxdraw.filled_polygon(self.surf, pole_coords, (202, 152, 101))

        gfxdraw.aacircle(
            self.surf,
            int(cartx),
            int(carty + axleoffset),
            int(polewidth / 2),
            (129, 132, 203),
        )
        gfxdraw.filled_circle(
            self.surf,
            int(cartx),
            int(carty + axleoffset),
            int(polewidth / 2),
            (129, 132, 203),
        )

        gfxdraw.hline(self.surf, 0, stat.DISPLAY_SIZE[0], carty, (0, 0, 0))

        # Endanschläge
        h_half = 10
        w = 5
        coords = [(0, carty+h_half), (0, carty-h_half), (w, carty-h_half), (w, carty+h_half)]
        gfxdraw.filled_polygon(self.surf, coords, stat.RED)
        coords = [(stat.DISPLAY_SIZE[0], carty+h_half), (stat.DISPLAY_SIZE[0], carty-h_half), (stat.DISPLAY_SIZE[0]-w, carty-h_half), (stat.DISPLAY_SIZE[0]-w, carty+h_half)]
        gfxdraw.filled_polygon(self.surf, coords, stat.RED)


        # show action
        # if self.action == 0:
        #     gfxdraw.filled_circle(self.surf, int(stat.DISPLAY_SIZE[0] / 2 - 10), 10, 10, (0, 0, 255))
        # elif self.action == 1:
        #     gfxdraw.filled_circle(self.surf, int(stat.DISPLAY_SIZE[0] / 2 + 10), 10, 10, (255, 0, 0))

        # flip coordinates
        self.surf = pygame.transform.flip(self.surf, False, True)

        # show state on screen
        p = precision = 3
        # u.print_on_screen(self.surf, f"pos {np.round(x[0], p)}", (int(stat.DISPLAY_SIZE[0] / 2), 10))
        # u.print_on_screen(self.surf, f"vel {np.round(x[1], p)}", (int(stat.DISPLAY_SIZE[0] / 2), 30))
        # u.print_on_screen(self.surf, f"ang {np.round(x[2], p)}", (int(stat.DISPLAY_SIZE[0] / 2), 50))
        # u.print_on_screen(self.surf, f"ome {np.round(x[3], p)}", (int(stat.DISPLAY_SIZE[0] / 2), 70))
        if self.action is not None:
            u.print_on_screen(self.surf, f"Kraft {np.round(self.action, p)}", (int(stat.DISPLAY_SIZE[0] / 2), 120))
        if self.countdown:
            u.print_on_screen(self.surf, f"Zeit {0.00} s", (10, 10), stat.LARGE_FONT)
        else:
            u.print_on_screen(self.surf, f"Zeit {np.round(time.time()-self.t0, 1)} s", (10, 10), stat.LARGE_FONT)
        u.print_on_screen(self.surf, f"aktuelle Bestzeit {np.round(self.current_best, 1)} s", (10, 120))
        u.print_on_screen(self.surf, f"Highscore: {self.highscore}", (stat.DISPLAY_SIZE[0]-400, 10))
        u.print_on_screen(self.surf, f"Versuch: {self.number_of_tries+1}/{self.max_tries}", (stat.DISPLAY_SIZE[0]-400, 30))
        if self.countdown:
            n = 3-int(time.time() - self.countdown_start)
            if n >= 0:
                u.print_on_screen(self.surf, f"{n}", (int(stat.DISPLAY_SIZE[0] / 2) -100, int(stat.DISPLAY_SIZE[1] / 2)-100), font=stat.HUGE_FONT)
            if n < 0:
                self.t0 = time.time()
                self.countdown = False



        self.display.blit(self.surf, (0, 0))
        pygame.event.pump()

        # some event handling for interactivity
        push_angle = 10.0 / 180 * np.pi
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not self.countdown:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_LEFT:
                        self.next_action = -self.F
                    if ev.key == pygame.K_RIGHT:
                        self.next_action = self.F
                if ev.type == pygame.KEYUP:
                    if ev.key == pygame.K_LEFT:
                        self.next_action = 0
                    if ev.key == pygame.K_RIGHT:
                        self.next_action = 0

        self.clock.tick(stat.FPS)
        pygame.display.flip()




    def run(self):
        self.init()
        self.number_of_tries = 0
        while(not self.exit):
            state, reward, terminated, truncated, info = self.step()
            if terminated or truncated:
                self.reset()

        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)

        def sorting_function2(item):
            return -item
        # bisect only works with ascending lists
        position = bisect.bisect_right(np.array(sorted(self.highscore_dict.values(), key=sorting_function2), dtype=float)*-1, -self.current_best)
        highscores = sorted(self.highscore_dict.items(), reverse=True, key=self.sorting_function)
        highscores.insert(position, ("", self.current_best))

        self.input_box = u.InputBox(100, 127+position*40, 300, 20, "Name")
        pygame.event.pump()
        done = False
        while(not done):
            self.display.fill(stat.WHITE)
            u.print_on_screen(self.display, f"Highscore", (10, 10), stat.LARGE_FONT)
            for i, (player, p_time) in enumerate(highscores):
                y = 130+i*40
                # u.print_on_screen(self.display, f"{i+1}.: {np.round(p_time, 2)} s, {player}", (10, y))
                u.print_on_screen(self.display, self.row_template.format(i+1, np.round(p_time, 2), player), (10, y))

            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN:
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if ev.key == pygame.K_RETURN or ev.key == pygame.K_KP_ENTER:
                        done = True
                        break
                self.input_box.handle_event(ev)
            self.input_box.update()
            self.input_box.show(self.display)
            self.clock.tick(stat.FPS)
            pygame.display.flip()
        self.highscore_dict[self.input_box.text] = self.current_best
        with open(self.highscore_path, "wt") as f:
            json.dump(self.highscore_dict, f)

class BalanceLoop(GameLoop):
    def __init__(self, game_display, clock):
        super().__init__(game_display, clock)


class HighscoreLoop(Loop):
    def __init__(self, game_display, clock, highscore_path):
        super().__init__(game_display, clock)
        self.highscore_path = highscore_path
        self.done = False
        def back(obj):
            obj.done = True
        self.return_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-70, 0, 70, 20, stat.RED, stat.LIGHT_RED, "Zurück", stat.NORMAL_FONT, action=back, action_args=[self])

    def run(self):
        self.done = False
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)

        highscores = sorted(self.highscore_dict.items(), reverse=True, key=self.sorting_function)

        pygame.event.pump()
        while(not self.done):
            self.display.fill(stat.WHITE)
            u.print_on_screen(self.display, f"Highscore", (10, 10), stat.LARGE_FONT)
            for i, (player, p_time) in enumerate(highscores):
                y = 130+i*40
                u.print_on_screen(self.display, self.row_template.format(i+1, np.round(p_time, 2), player), (10, y))


            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN:
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
            self.return_button.show()
            self.clock.tick(stat.FPS)
            pygame.display.flip()

