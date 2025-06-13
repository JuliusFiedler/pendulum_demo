from abc import abstractmethod
import pygame
from pygame import gfxdraw
import numpy as np
from numpy import sin, cos
import math
import sys, os
from scipy.integrate import solve_ivp
import time
from ipydex import IPS
import json
import bisect
import csv

import util.statics as stat
import util.utils as u

def exit_proxy():
    pygame.quit()
    sys.exit()


class Loop():
    def __init__(self, game_display, clock) -> None:
        self.display = game_display
        self.clock = clock
        # define fps
        self.clock.tick(stat.FPS)
        self.row_template = "{:<2}.  {:<5} s,   {}"

        self.joysticks = {}

    @abstractmethod
    def run(self):
        pass

    def sorting_function(self, item):
        return item[1]

class IntroLoop(Loop):
    def __init__(self, game_display, clock, loops:list) -> None:
        super().__init__(game_display, clock)
        self.loops = loops
        from_border_y = 400
        self.b_size = (400, 50)
        self.b_pos = (stat.DISPLAY_SIZE[0]//2-self.b_size[0]//2, stat.DISPLAY_SIZE[1] - from_border_y)
        self.rst_logo = pygame.transform.scale_by(pygame.image.load(stat.rst_logo_path), 0.2)
        self.logo_pos = (stat.DISPLAY_SIZE[0]//2-self.rst_logo.get_rect().width//2, stat.DISPLAY_SIZE[1] //2)


    def run(self):
        global tb_joyaxis  # Weder gut noch schön, aber gar keine Motivation den Status des ToggleButton durch *alle* Funktionsaufrufe zu ziehen
        tb_joyaxis = u.ToggleButton(self.display, self.b_pos[0], self.b_pos[1]+(self.b_size[1]+5)*5, self.b_size[0], self.b_size[1], \
                stat.RED, stat.LIGHT_RED, stat.GREEN, stat.LIGHT_GREEN, "Gamepad-Eingabe", stat.BUTTON_FONT)
        b_stabilize = u.Button(self.display, self.b_pos[0], self.b_pos[1], self.b_size[0], self.b_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Balancieren", stat.BUTTON_FONT, action=self.loops[0].run)
        b_multi = u.Button(self.display, self.b_pos[0], self.b_pos[1]+self.b_size[1]+5, self.b_size[0], self.b_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Aufschwingen", stat.BUTTON_FONT, action=self.loops[1].run)
        b_hs = u.Button(self.display, self.b_pos[0], self.b_pos[1]+(self.b_size[1]+5)*2, self.b_size[0], self.b_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Highscore", stat.BUTTON_FONT, action=self.loops[2].run)
        b_exp = u.Button(self.display, self.b_pos[0], self.b_pos[1]+(self.b_size[1]+5)*3, self.b_size[0], self.b_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Experiment", stat.BUTTON_FONT, action=self.loops[3].run, action_args=[])
        b_control = u.Button(self.display, self.b_pos[0], self.b_pos[1]+(self.b_size[1]+5)*4, self.b_size[0], self.b_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Regelung", stat.BUTTON_FONT, action=self.loops[4].run)
        b_exit = u.Button(self.display, self.b_pos[0], self.b_pos[1]+(self.b_size[1]+5)*6, self.b_size[0], self.b_size[1], \
                stat.GREEN, stat.LIGHT_GREEN, "Beenden", stat.BUTTON_FONT, action=exit_proxy)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

                # Handle hotplugging
                if event.type == pygame.JOYDEVICEADDED:
                    # This event will be generated when the program starts for every
                    # joystick, filling up the list without needing to create them manually.
                    joy = pygame.joystick.Joystick(event.device_index)
                    self.joysticks[joy.get_instance_id()] = joy
                    print(f"Joystick {joy.get_instance_id()} connected")

                if event.type == pygame.JOYDEVICEREMOVED:
                    del self.joysticks[event.instance_id]
                    print(f"Joystick {event.instance_id} disconnected")
            self.display.fill(stat.WHITE)

            text_surface, text_rect = u.text_objects(stat.GAME_NAME, stat.LARGE_FONT)
            text_rect.center = (stat.DISPLAY_SIZE[0] / 2, stat.DISPLAY_SIZE[1] / 3)
            self.display.blit(text_surface, text_rect)
            self.display.blit(self.rst_logo, self.logo_pos)

            # buttons
            b_stabilize.show()
            b_multi.show()
            b_hs.show()
            b_exp.show()
            b_control.show()
            tb_joyaxis.show()
            b_exit.show()

            pygame.display.update()

class GameLoop(Loop):
    def __init__(self, game_display, clock, highscore_path) -> None:
        super().__init__(game_display, clock)

        # render
        self.cartwidth = 50.0
        self.cartheight = 30.0
        self.polewidth = 10.0

        # physics
        self.gravity = 9.8
        self.masscart = 1.0
        self.masspole = 0.1
        self.tau = 0.01  # seconds between state updates
        self.kinematics_integrator = "solve_ivp"  # "euler"
        self.F_initial = 7

        self.highscore_path = highscore_path

        self.max_tries = 2 #! number of tries before returning to start screen. 2 for testing, ~10 for deployment

        self.x_threshold = 2.16/1000*stat.DISPLAY_SIZE[0] #2.16 this number results in nice ratios on screen
        def back(obj):
            obj.exit = True
        self.return_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-70, 0, 70, 20, stat.RED, stat.LIGHT_RED, "Zurück", stat.NORMAL_FONT, action=back, action_args=[self])
        self.arrow_img = pygame.transform.scale(pygame.image.load(stat.arrow_path), (75,50))
        self.arrow_green_img = pygame.transform.scale(pygame.image.load(stat.arrow_green_path), (75,50))


        self.init()

    def init(self):
        self.success = False

        self.length = 1
        self.F = self.F_initial
        self.my = 0.00 # friction

        self.next_action = 0
        self.t0 = time.time()

        self.state = None
        self.last_state = None
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

    def get_highscore(self):
        return ""

    def calc_new_state(self, action):
        x, x_dot, theta, theta_dot = self.state
        # based on mathematical pendulum

        def rhs(t, state):
            x, x_dot, theta, theta_dot = state
            x1, p1, x3, pdot1 = x, theta, x_dot, theta_dot  # change order
            g = self.gravity
            l = self.length
            m1 = self.masscart
            m2 = self.masspole
            my = self.my
            tau1 = action
            dx1_dt = x_dot
            dx2_dt = theta_dot
            dx3_dt = (-2*g*m2*l*sin(p1)*cos(p1) + m2*pdot1**2*l**2*sin(p1) + 4*pdot1*my*cos(p1) + 2*l*tau1)/(2*m1*l + 2*m2*l*sin(p1)**2)

            dx4_dt = (2*g*m1*m2*l*sin(p1) + 2*g*m2**2*l*sin(p1) - 4*m1*pdot1*my - m2**2*pdot1**2*l**2*sin(p1)*cos(p1) - 4*m2*pdot1*my - 2*m2*l*tau1*cos(p1))/(m1*m2*l**2 + m2**2*l**2*sin(p1)**2)


            return [dx1_dt, dx3_dt, dx2_dt, dx4_dt]  # change order back

        tt = np.linspace(0, self.tau, 2)
        xx0 = np.array(self.state).flatten()
        s = solve_ivp(rhs, (0, self.tau), xx0, t_eval=tt)

        x, x_dot, theta, theta_dot = s.y[:, -1].flatten()

        state = (x, x_dot, theta, theta_dot)
        return state

    def get_action(self):
        return self.next_action

    def step(self):
        action = self.get_action()
        self.action = action
        if not self.countdown:
            self.state = self.calc_new_state(action)
            self.last_state = self.state
        self.render()

        terminated = self.get_terminated()

        return self.state, 0, terminated, False, {}

    @abstractmethod
    def get_terminated(self):
        raise NotImplementedError()

    def reset(self):
        if self.success:
            self.times.append(time.time()- self.t0)
            self.current_best = self.get_current_best()
            self.success = False

        self.action = 0
        self.next_action = 0
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

    def get_current_best(self):
        return None

    def render(self):
        self._render_init()
        self._render_cart()
        self._render_ui()
        self._event_handling()
        self._render_custom()
        self._render_post_pro()

    def _render_custom(self):
        pass

    def _render_init(self):
        self.surf = pygame.Surface(stat.DISPLAY_SIZE)
        self.surf.fill((255, 255, 255))

    def _render_cart(self):
        world_width = self.x_threshold * 2
        scale = stat.DISPLAY_SIZE[0] / world_width
        polelen = scale * (self.length)

        if self.state is None:
            return None

        x = self.state

        l, r, t, b = -self.cartwidth / 2, self.cartwidth / 2, self.cartheight / 2, -self.cartheight / 2
        axleoffset = self.cartheight / 4.0
        cartx = x[0] * scale + stat.DISPLAY_SIZE[0] / 2.0  # MIDDLE OF CART
        carty = 100  # TOP OF CART
        cart_coords = [(l, b), (l, t), (r, t), (r, b)]
        cart_coords = [(c[0] + cartx, c[1] + carty) for c in cart_coords]
        gfxdraw.aapolygon(self.surf, cart_coords, (0, 0, 0))
        gfxdraw.filled_polygon(self.surf, cart_coords, (0, 0, 0))

        l, r, t, b = (
            -self.polewidth / 2,
            self.polewidth / 2,
            polelen - self.polewidth / 2,
            -self.polewidth / 2,
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
            int(self.polewidth / 2),
            (129, 132, 203),
        )
        gfxdraw.filled_circle(
            self.surf,
            int(cartx),
            int(carty + axleoffset),
            int(self.polewidth / 2),
            (129, 132, 203),
        )
        # Center of Mass
        com_x = cartx + sin(x[2]) * polelen/2
        com_y = carty + axleoffset + cos(x[2]) * polelen/2
        gfxdraw.filled_circle(
            self.surf,
            int(com_x),
            int(com_y),
            int(self.polewidth / 2),
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
        #todo transform size proportional to force
        ratio = np.abs(self.action)/self.F_initial
        ratio = np.max((0.1, ratio))
        ratio = np.min((3, ratio))
        img = pygame.transform.scale_by(self.arrow_img, ratio)
        arr_w, arr_h = img.get_size()
        y = carty - arr_h//2
        if self.action > 0:
            self.surf.blit(img, (cartx + self.cartwidth//2, y))
        if self.action < 0:
            self.surf.blit(pygame.transform.flip(img, flip_x=True, flip_y=False), (cartx - self.cartwidth//2 - arr_w, y))

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
        u.print_on_screen(self.surf, f"Nutze die Pfeiltasten um den Wagen zu bewegen.", (10, 200), stat.MEDIUM_FONT)
        if self.countdown:
            n = 3-int(time.time() - self.countdown_start)
            if n >= 0:
                u.print_on_screen(self.surf, f"{n}", (int(stat.DISPLAY_SIZE[0] / 2) -100, int(stat.DISPLAY_SIZE[1] / 2)-100), font=stat.HUGE_FONT)
            if n < 0:
                self.t0 = time.time()
                self.countdown = False

        self.display.blit(self.surf, (0, 0))

    def _event_handling(self):
        self.events = pygame.event.get()
        use_joyaxis = tb_joyaxis.get_active()

        # some event handling for interactivity
        for ev in self.events:
            if ev.type == pygame.QUIT:
                u.exit_game()

            # Handle hotplugging
            if ev.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(ev.device_index)
                self.joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connected", flush=True)

            if ev.type == pygame.JOYDEVICEREMOVED:
                try:
                    del self.joysticks[ev.instance_id]
                except KeyError:
                    pass
                print(f"Joystick {ev.instance_id} disconnected")
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

                if use_joyaxis:
                    if ev.type == pygame.JOYAXISMOTION:
                        if ev.axis == 0:
                            self.next_action = 2*self.F * ev.value

                    if ev.type == pygame.JOYBUTTONDOWN:
                        if ev.button == 1:
                            self.reset()



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

    def get_highscore_and_position(self):
        return None, None

    def enter_name_highscore(self, highscores:list, position:int):
        """highscores is a list of tuples [("1235142561__bob", 1.5), ("1238713812__mob", 2.4)]"""
        self.input_box = u.InputBox(100, 127+position*40, 300, 20, "Name")
        pygame.event.pump()
        done = False
        while(not done):
            # load last state so we can display it after reset during highscore
            self.state = self.last_state
            self._render_init()
            self._render_cart()
            u.print_on_screen(self.display, f"Highscore", (10, 10), stat.LARGE_FONT)
            for i, (player_id, p_time) in enumerate(highscores):
                player = player_id.split("__")[-1]
                y = 130+i*40
                u.print_on_screen(self.display, self.row_template.format(i+1, np.round(p_time, 2), player), (10, y))

            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN:
                    if ev.type == pygame.QUIT:
                        u.exit_game()
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


class ControlLoop(GameLoop):
    def __init__(self, game_display, clock):
        self.mode = 0
        self.K_upper_EQ = np.array([[
            -85.62691131,   # x
            -54.33231397,    # x_dot
            -178.12345566,  # theta
            -40.16615698,   # theta_dot
            ]])
        # self.K_lower_EQ = np.array([[85.62691131499069, 54.332313965344916, 72.8765443425107, -14.166156982672117]])
        self.K_lower_EQ = np.array([[31.622776601683597, 43.28803503081849, 125.73324499512717, 15.65939564338845]])

        super().__init__(game_display, clock, None)
        self.reset_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 50, 120, 30, stat.BLUE, stat.LIGHT_BLUE, "Reset", stat.NORMAL_FONT, text_color=stat.WHITE, action=self.reset, action_args=[])
        self.toggle_mode_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 90, 120, 30, stat.ORANGE, stat.LIGHT_ORANGE, "Aufschwingen", stat.NORMAL_FONT, text_color=stat.BLACK, action=self.toggle_mode, action_args=[])

        self.swingup_actions = []
        # load swingup trajectory
        with open("trajectories/cartpole_swingup.csv", newline="") as csvfile:
            reader = csv.reader(csvfile, delimiter=",")
            for row in reader:
                self.swingup_actions.append(row[0])
        self.swingup_index = 0
        self.save_actions = []
        self.number_of_modes = 2 # set this to 3 to record swing down -> time reversal -> swingup trajectory

    def toggle_mode(self):
        self.mode += 1
        self.mode = self.mode % self.number_of_modes
        # button label opposite (what you click on is what you want)
        if self.mode == 0:
            self.toggle_mode_button.text = "Aufschwingen"
            self.toggle_mode_button.inactive_color = stat.ORANGE
            self.toggle_mode_button.active_color = stat.LIGHT_ORANGE
        elif self.mode == 1:
            self.toggle_mode_button.text = "Balance"
            self.toggle_mode_button.inactive_color = stat.GREEN
            self.toggle_mode_button.active_color = stat.GREEN
        elif self.mode == 2:
            self.toggle_mode_button.text = "Gen Traj"
        self.reset()

    def get_terminated(self):
        x, x_dot, theta, theta_dot = self.state
        terminated = bool(
            x < -self.x_threshold
            or x > self.x_threshold
        )
        if self.mode == 2:
            if np.abs(self.state[2] - np.pi) < 0.01 and np.abs(self.state[0]) < 0.1:
                terminated = True
        return terminated

    def get_action(self):
        if self.mode == 0:
            action = -(self.K_upper_EQ @ (self.state - np.array([self.target_offset, 0,0,0])))[0]
        elif self.mode == 1:
            if self.swingup_index < len(self.swingup_actions):
                action = float(self.swingup_actions[self.swingup_index])
                self.swingup_index += 1
            else:
                self.mode = 0
                self.target_offset = 0
                self.toggle_mode_button.text = "Aufschwingen"
                self.toggle_mode_button.inactive_color = stat.ORANGE
                self.toggle_mode_button.active_color = stat.LIGHT_ORANGE
                action = 0

        elif self.mode == 2:
            if np.abs(self.state[2]) < 0.4:
                action = -50
            else:
                state = np.array(self.state, dtype=float)
                state[2] += np.pi
                state = u.project_to_interval(state)
                action = -(self.K_lower_EQ @ state)[0]
            self.save_actions.append(action)
        action = np.clip(action, -50, 50)
        return action

    def get_start_state(self):
        if self.mode == 0:
            return [0, 0, (np.random.random()-0.5)*0.1, 0]
        elif self.mode == 1:
            return [0, 0, np.pi, 0]
        elif self.mode == 2:
            return [0, 0, 0, 0]

    def reset(self):
        self.action = 0
        # random state
        self.state = self.get_start_state()
        self.swingup_index = 0
        self.target_offset = 0
        if self.mode == 2:
            self.save_actions.reverse()
            with open("trajectories/cartpole_swingup.csv", mode="w", newline="") as csvfile:
                writer = csv.writer(csvfile, delimiter=",")
                for a in self.save_actions:
                    writer.writerow([str(a)])
            self.save_actions = []


    def _render_ui(self):
        self.countdown = False
        u.print_on_screen(self.surf, f"Modus wechseln ->", (500, 83), stat.MEDIUM_FONT)
        u.print_on_screen(self.surf, f"Nutze die Pfeiltasten um das Pendel zu schubsen.", (10, 200), stat.MEDIUM_FONT)
        u.print_on_screen(self.surf, f"Bestimme die Zielposition mit Klicken der Maus.", (10, 250), stat.MEDIUM_FONT)
        if self.mode == 0:
            scale = stat.DISPLAY_SIZE[0] / (self.x_threshold * 2)
            img = self.arrow_green_img
            img = pygame.transform.scale_by(img, 0.8)
            img = pygame.transform.rotate(img, 90)

            self.surf.blit(img, (int(stat.DISPLAY_SIZE[0]//2 + self.target_offset*scale)-img.get_size()[0]//2, int(stat.DISPLAY_SIZE[1]-80)))

        self.display.blit(self.surf, (0,0))

    def _event_handling(self):
        pygame.event.pump()
        world_width = self.x_threshold * 2
        scale = stat.DISPLAY_SIZE[0] / world_width


        # some event handling for interactivity
        push_angle = 10.0 / 180 * np.pi
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                u.exit_game()
            if ev.type == pygame.KEYDOWN:
                # push rod to make cart do something
                if ev.key == pygame.K_LEFT:
                    state = list(self.state)
                    state[2] -= push_angle
                    self.state = state
                if ev.key == pygame.K_RIGHT:
                    state = list(self.state)
                    state[2] += push_angle
                    self.state = state
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                # print(mouse_pos)
                if mouse_pos[1] > 300:
                    target_x = -(stat.DISPLAY_SIZE[0] / 2 - mouse_pos[0]) / scale
                    self.target_offset = target_x

    def _render_custom(self):
        self.reset_button.show()
        self.toggle_mode_button.show()


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
        self.success = True
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
        res = sorted(self.highscore_dict.items(), key=self.sorting_function, reverse=True)
        if res:
            player_id, p_time = res[0]
            player = player_id.split("__")[-1]
            output = f"{np.round(p_time, 1)} s, von {player}"
        else:
            output = ""
        return output

    def _render_custom(self):
        u.print_on_screen(self.surf, f"Halte das Pendel aufrecht. Du hast {self.max_tries} Versuche.", (10, 260), stat.MEDIUM_FONT)
        self.display.blit(self.surf, (0, 0))


class ExperimentalLoop(GameLoop):
    def __init__(self, game_display, clock):
        self.mode = 1 # 1=balance, -1 = swingup
        self.endless_mode = -1 # 1 endless, -1 reset on pendulum fall
        super().__init__(game_display, clock, None)
        # Angle at which to fail the episode
        self.theta_threshold_radians = 90 * 2 * math.pi / 360
        x_pos_sliders = 140
        self.length_slider = u.Slider(game_display, x_pos_sliders, 10, 400, value=self.length, value_range=[0.1, 2])
        self.force_slider = u.Slider(game_display, x_pos_sliders, 70, 400, value=self.F, value_range=[0, 20])
        self.friction_slider = u.Slider(game_display, x_pos_sliders, 130, 400, value=self.my, value_range=[0, 0.1], round_to=4)
        self.max_tries = 999
        self.reset_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 50, 120, 30, stat.BLUE, stat.LIGHT_BLUE, \
            "Reset", stat.NORMAL_FONT, text_color=stat.WHITE, action=self.reset, action_args=[])
        self.toggle_mode_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 90, 120, 30, stat.BLUE, \
            stat.LIGHT_BLUE, "Aufschwingen", stat.NORMAL_FONT, text_color=stat.WHITE, action=self.toggle_mode, action_args=[])
        self.toggle_endless_button = u.Button(self.display, stat.DISPLAY_SIZE[0]-120, 130, 120, 30, stat.BLUE, \
            stat.LIGHT_BLUE, "Endlos", stat.NORMAL_FONT, text_color=stat.WHITE, action=self.toggle_endless_mode, action_args=[])

    def get_terminated(self):
        x, x_dot, theta, theta_dot = self.state
        if self.mode == -1:
            terminated = bool(
                x < -self.x_threshold
                or x > self.x_threshold
            )
        elif self.mode == 1:
            if self.endless_mode == 1:
                terminated = bool(
                    x < -self.x_threshold
                    or x > self.x_threshold
                )
            elif self.endless_mode == -1:
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

    def toggle_endless_mode(self):
        self.endless_mode *= -1
        # button label opposite (what you click on is what you want)
        if self.endless_mode == -1:
            self.toggle_endless_button.inactive_color = stat.BLUE
            self.toggle_endless_button.active_color = stat.LIGHT_BLUE
        elif self.endless_mode == 1:
            self.toggle_endless_button.inactive_color = stat.LIGHT_BLUE
            self.toggle_endless_button.active_color = stat.BLUE
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
        u.print_on_screen(self.display, f"Reibung", (10, 130), stat.NORMAL_FONT)
        u.print_on_screen(self.display, f"im Gelenk", (10, 150), stat.NORMAL_FONT)

    def _render_custom(self):
        self.length_slider.update(self.events)
        self.length = self.length_slider.value
        self.length_slider.show()

        self.force_slider.update(self.events)
        self.F = self.force_slider.value
        self.force_slider.show()

        self.friction_slider.update(self.events)
        self.my = self.friction_slider.value
        self.friction_slider.show()

        self.reset_button.show()
        self.toggle_mode_button.show()
        self.toggle_endless_button.show()

class SwingupLoop(GameLoop):
    def __init__(self, game_display, clock, highscore_path):
        super().__init__(game_display, clock, highscore_path)
        self.theta_threshold_radians = 5 * 2 * math.pi / 360
        self.theta_dot_threshold = 3 * self.theta_threshold_radians
        self.x_dot_threshold = 2.16/10  # 10% of track width per second
        self.success = False


    def get_terminated(self):
        x, x_dot, theta, theta_dot = self.state
        theta = theta % (2*np.pi)
        self.success = bool(  # position check
            theta < self.theta_threshold_radians
            or 2*np.pi-theta < self.theta_threshold_radians
        ) and (abs(theta_dot) < self.theta_dot_threshold) and (abs(x_dot) < self.x_dot_threshold)
        terminated = bool(
            x < -self.x_threshold
            or x > self.x_threshold
            or self.success
        )
        return terminated

    def get_highscore_and_position(self):
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)

        # bisect only works with ascending lists
        position = bisect.bisect_right(sorted(self.highscore_dict.values()), self.current_best)
        highscores = sorted(self.highscore_dict.items(), key=self.sorting_function)
        highscores.insert(position, ("", self.current_best))

        return highscores, position

    def get_current_best(self):
        return min(self.times)

    def get_start_state(self):
        return [0, 0, np.pi + (np.random.random()-0.5)*0.1, 0]

    def get_highscore(self):
        with open(self.highscore_path, "rt") as f:
            self.highscore_dict = json.load(f)
        res = sorted(self.highscore_dict.items(), key=self.sorting_function)
        if res:
            player_id, p_time = res[0]
            player = player_id.split("__")[-1]
            output = f"{np.round(p_time, 1)} s, von {player}"
        else:
            output = ""
        return output

    def render(self):
        self._render_init()
        self._render_custom()
        self._render_cart()
        self._render_ui()
        u.print_on_screen(self.surf, f"Richte das Pendel auf. Du hast {self.max_tries} Versuche.", (10, 260), stat.MEDIUM_FONT)
        self.display.blit(self.surf, (0, 0))
        self._event_handling()
        self._render_post_pro()

    def _render_custom(self):
        x = self.state
        world_width = self.x_threshold * 2
        scale = stat.DISPLAY_SIZE[0] / world_width

        axleoffset = self.cartheight / 4.0
        cartx = x[0] * scale + stat.DISPLAY_SIZE[0] / 2.0  # MIDDLE OF CART
        carty = 100  # TOP OF CART
        p0 = (cartx, carty)
        alpha = self.theta_threshold_radians
        p1 = (cartx + sin(alpha) * scale/2, carty + axleoffset + cos(alpha) * scale/2)
        p2 = (cartx + sin(-alpha) * scale/2, carty + axleoffset + cos(-alpha) * scale/2)
        gfxdraw.filled_polygon(self.surf, (p0, p1, p2), stat.LIGHT_GREEN)
        self.display.blit(self.surf, (0, 0))




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
                    u.exit_game()
            self.return_button.show()
            self.clock.tick(stat.FPS)
            pygame.display.flip()

