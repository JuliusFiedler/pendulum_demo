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
        self.row_template = "{:<2}.  {:<5} s,   {}"

    @abstractmethod
    def run(self):
        pass

    def sorting_function(self, item):
        return item[1]

class IntroLoop(Loop):
    def __init__(self, game_display, clock, loops:list) -> None:
        super().__init__(game_display, clock)
        self.loops = loops
        from_border_x = 150
        from_border_y = 250
        self.button_1_size = self.button_2_size = (400, 50)
        self.button_1_pos = (from_border_x, stat.DISPLAY_SIZE[1] - from_border_y)
        self.button_2_pos = (stat.DISPLAY_SIZE[0] - from_border_x-self.button_2_size[0], stat.DISPLAY_SIZE[1] - from_border_y)




    def run(self):
        b_stabilize = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1], self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Balancieren", stat.BUTTON_FONT, action=self.loops[0].run)
        b_multi = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1]+self.button_1_size[1]+5, self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Aufschwingen", stat.BUTTON_FONT, action=self.loops[1].run)
        b_hs = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1]+(self.button_1_size[1]+5)*2, self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Highscore", stat.BUTTON_FONT, action=self.loops[2].run)
        b_exp = u.Button(self.display, self.button_1_pos[0], self.button_1_pos[1]+(self.button_1_size[1]+5)*3, self.button_1_size[0], self.button_1_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Experiment", stat.BUTTON_FONT, action=self.loops[3].run)
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
            b_exp.show()
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
        self.tau = 0.01  # seconds between state updates
        self.kinematics_integrator = "solve_ivp"  # "euler"

        self.highscore_path = highscore_path

        self.max_tries = 1

        self.x_threshold = 2.16
        def back(obj):
            obj.exit = True
        self.return_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-70, 0, 70, 20, stat.RED, stat.LIGHT_RED, "Zurück", stat.NORMAL_FONT, action=back, action_args=[self])

        self.init()

    def init(self):
        self.length = 1  # actually half the pole's length
        #! pole has length 2*l
        self.polemass_length = self.masspole * self.length
        self.F = 10
        self.next_action = 0
        self.t0 = time.time()

        self.state = None
        self.action = None
        self.exit = False

        self.times = []
        self.current_best = None
        self.number_of_tries = -1
        self.countdown = False
        self.countdown_start = None

        self.highscore = self.get_highscore()
        self.reset()
        self.times = []
        self.current_best = None

    @abstractmethod
    def get_highscore(self):
        raise NotImplementedError()

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

        terminated = self.get_terminated()

        return self.state, 0, terminated, False, {}

    @abstractmethod
    def get_terminated(self):
        raise NotImplementedError()

    def reset(self):
        self.times.append(time.time()- self.t0)
        self.current_best = self.get_current_best()

        # random state
        self.state = self.get_start_state()
        # self.state = [2.16, 0, 0, 0]
        self.number_of_tries += 1
        self.countdown_start = time.time()
        self.countdown = True
        # self.render()

        if self.number_of_tries >= self.max_tries:
            self.exit = True

    @abstractmethod
    def get_start_state(self):
        raise NotImplementedError()

    @abstractmethod
    def get_current_best(self):
        raise NotImplementedError()

    def render(self):
        self._render_base()
        self._render_ui()
        self._event_handling()
        self._render_custom()
        self._render_post_pro()

    def _render_custom(self):
        pass

    def _render_base(self):
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
        self.display.blit(self.surf, (0, 0))

    def _render_ui(self):
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
        cb = np.round(self.current_best, 1) if self.current_best is not None else "-"
        u.print_on_screen(self.surf, f"aktuelle Bestzeit {cb} s", (10, 120))
        u.print_on_screen(self.surf, f"Highscore: {self.highscore}", (stat.DISPLAY_SIZE[0]-400, 40))
        u.print_on_screen(self.surf, f"Versuch: {self.number_of_tries+1}/{self.max_tries}", (stat.DISPLAY_SIZE[0]-400, 60))
        if self.countdown:
            n = 3-int(time.time() - self.countdown_start)
            if n >= 0:
                u.print_on_screen(self.surf, f"{n}", (int(stat.DISPLAY_SIZE[0] / 2) -100, int(stat.DISPLAY_SIZE[1] / 2)-100), font=stat.HUGE_FONT)
            if n < 0:
                self.t0 = time.time()
                self.countdown = False

        self.display.blit(self.surf, (0, 0))

    def _event_handling(self):
        pygame.event.pump()
        self.events = pygame.event.get()

        # some event handling for interactivity
        for ev in self.events:
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

    def _render_post_pro(self):
        self.return_button.show()
        self.clock.tick(stat.FPS)
        pygame.display.flip()

    def run(self):
        self.init()
        while(not self.exit):
            state, reward, terminated, truncated, info = self.step()
            if terminated or truncated:
                self.reset()
        if self.current_best:
            hs, pos = self.get_highscore_and_position()
            # low results will not be shown
            if pos <= 17:
                self.enter_name_highscore(highscores=hs, position=pos)

    @abstractmethod
    def get_highscore_and_position(self):
        raise NotImplementedError()

    def enter_name_highscore(self, highscores:list, position:int):
        """highscores is a list of tuples [("1235142561__bob", 1.5), ("1238713812__mob", 2.4)]"""
        self.input_box = u.InputBox(100, 127+position*40, 300, 20, "Name")
        pygame.event.pump()
        done = False
        while(not done):
            self.display.fill(stat.WHITE)
            u.print_on_screen(self.display, f"Highscore", (10, 10), stat.LARGE_FONT)
            for i, (player_id, p_time) in enumerate(highscores):
                player = player_id.split("__")[-1]
                y = 130+i*40
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
        player_id = f"{time.time()}__{self.input_box.text}"
        self.highscore_dict[player_id] = self.current_best
        with open(self.highscore_path, "wt") as f:
            json.dump(self.highscore_dict, f)


class BalanceLoop(GameLoop):
    def __init__(self, game_display, clock, highscore_path):
        super().__init__(game_display, clock, highscore_path)
        # Angle at which to fail the episode
        self.theta_threshold_radians = 90 * 2 * math.pi / 360

    def get_terminated(self):
        x, x_dot, theta, theta_dot = self.state
        terminated = bool(
            x < -self.x_threshold
            or x > self.x_threshold
            or theta < -self.theta_threshold_radians
            or theta > self.theta_threshold_radians
        )
        return terminated

    def get_highscore_and_position(self):
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)

        def sorting_function2(item):
            return -item
        # bisect only works with ascending lists
        position = bisect.bisect_right(np.array(sorted(self.highscore_dict.values(), key=sorting_function2), dtype=float)*-1, -self.current_best)
        highscores = sorted(self.highscore_dict.items(), reverse=True, key=self.sorting_function)
        highscores.insert(position, ("", self.current_best))

        return highscores, position

    def get_current_best(self):
        return max(self.times)

    def get_start_state(self):
        return [0, 0, (np.random.random()-0.5)*0.1, 0]

    def get_highscore(self):
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)
        player_id, p_time = sorted(self.highscore_dict.items(), key=self.sorting_function, reverse=True)[0]
        player = player_id.split("__")[-1]
        return f"{np.round(p_time, 1)} s, von {player}"

class ExperimentalLoop(GameLoop):
    def __init__(self, game_display, clock):
        self.mode = 1 # 1=balance, -1 = swingup
        super().__init__(game_display, clock, None)
        # Angle at which to fail the episode
        self.theta_threshold_radians = 90 * 2 * math.pi / 360
        self.length_slider = u.Slider(game_display, 120, 10, 400, value=self.length, value_range=[0.1, 2])
        self.force_slider = u.Slider(game_display, 120, 70, 400, value=self.F, value_range=[0.1, 20])
        self.max_tries = 999
        self.reset_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 50, 120, 30, stat.BLUE, stat.LIGHT_BLUE, "Reset", stat.NORMAL_FONT, text_color=stat.WHITE, action=self.reset, action_args=[])
        self.toggle_mode_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 90, 120, 30, stat.BLUE, stat.LIGHT_BLUE, "Aufschwingen", stat.NORMAL_FONT, text_color=stat.WHITE, action=self.toggle_mode, action_args=[])

    def get_terminated(self):
        x, x_dot, theta, theta_dot = self.state
        if self.mode == -1:
            terminated = bool(
                x < -self.x_threshold
                or x > self.x_threshold
            )
        elif self.mode == 1:
            terminated = bool(
                x < -self.x_threshold
                or x > self.x_threshold
                or theta < -self.theta_threshold_radians
                or theta > self.theta_threshold_radians
            )

        return terminated

    def toggle_mode(self):
        self.mode *= -1
        # button label opposite (what you click on is what you want)
        if self.mode == -1:
            self.toggle_mode_button.text = "Balance"
        elif self.mode == 1:
            self.toggle_mode_button.text = "Aufschwingen"
        self.reset()

    def get_highscore_and_position(self):
        return 0, None

    def get_current_best(self):
        return None

    def get_start_state(self):
        if self.mode == 1:
            return [0, 0, (np.random.random()-0.5)*0.1, 0]
        elif self.mode == -1:
            return [0, 0, np.pi+(np.random.random()-0.5)*0.1, 0]

    def get_highscore(self):
        return ""

    def _render_ui(self):
        self.countdown = False
        u.print_on_screen(self.display, f"Länge", (10, 10), stat.NORMAL_FONT)
        u.print_on_screen(self.display, f"Kraft", (10, 70), stat.NORMAL_FONT)

    def _render_custom(self):
        self.length_slider.update(self.events)
        self.length = self.length_slider.value
        self.length_slider.show()

        self.force_slider.update(self.events)
        self.F = self.force_slider.value
        self.force_slider.show()

        self.reset_button.show()
        self.toggle_mode_button.show()

class SwingupLoop(GameLoop):
    def __init__(self, game_display, clock, highscore_path):
        super().__init__(game_display, clock, highscore_path)
        self.theta_threshold_radians = 10 * 2 * math.pi / 360


    def get_terminated(self):
        return False

    def get_highscore_and_position(self):
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)

        def sorting_function2(item):
            return -item
        # bisect only works with ascending lists
        position = bisect.bisect_right(np.array(sorted(self.highscore_dict.values(), key=sorting_function2), dtype=float)*-1, -self.current_best)
        highscores = sorted(self.highscore_dict.items(), reverse=True, key=self.sorting_function)
        highscores.insert(position, ("", self.current_best))

        return highscores, position

    def get_current_best(self):
        return min(self.times)

    def get_start_state(self):
        return [0, 0, np.pi + (np.random.random()-0.5)*0.1, 0]

    def get_highscore(self):
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)
        player_id, p_time = sorted(self.highscore_dict.items(), key=self.sorting_function)[0]
        player = player_id.split("__")[-1]
        return f"{np.round(p_time, 1)} s, von {player}"



class HighscoreLoop(Loop):
    def __init__(self, game_display, clock, balance_highscore_path, swingup_highscore_path):
        super().__init__(game_display, clock)
        self.balance_highscore_path = balance_highscore_path
        self.swingup_highscore_path = swingup_highscore_path
        self.done = False
        def back(obj):
            obj.done = True
        self.return_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-70, 0, 70, 20, stat.RED, stat.LIGHT_RED, "Zurück", stat.NORMAL_FONT, action=back, action_args=[self])

    def run(self):
        self.done = False
        with open(self.balance_highscore_path, "rt") as f:
            self.balance_highscore_dict = json.load(f)
        balance_highscores = sorted(self.balance_highscore_dict.items(), reverse=True, key=self.sorting_function)

        with open(self.swingup_highscore_path, "rt") as f:
            self.swingup_highscore_dict = json.load(f)
        swingup_highscores = sorted(self.swingup_highscore_dict.items(), key=self.sorting_function)

        pygame.event.pump()
        while(not self.done):
            self.display.fill(stat.WHITE)
            u.print_on_screen(self.display, f"Highscore", (10, 10), stat.LARGE_FONT)
            u.print_on_screen(self.display, f"Balance", (10, 140), stat.MEDIUM_FONT)
            u.print_on_screen(self.display, f"Aufschwingen", (20+stat.DISPLAY_SIZE[0]//2, 140), stat.MEDIUM_FONT)
            for i, (player_id, p_time) in enumerate(balance_highscores):
                player = player_id.split("__")[-1]
                y = 180+i*40
                u.print_on_screen(self.display, self.row_template.format(i+1, np.round(p_time, 2), player), (10, y))
            for i, (player_id, p_time) in enumerate(swingup_highscores):
                player = player_id.split("__")[-1]
                y = 180+i*40
                u.print_on_screen(self.display, self.row_template.format(i+1, np.round(p_time, 2), player), (20+stat.DISPLAY_SIZE[0]//2, y))


            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.return_button.show()
            self.clock.tick(stat.FPS)
            pygame.display.flip()

