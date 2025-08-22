from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.animation import Animation
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
import openai
from openai import OpenAI
from threading import Thread
from collections import defaultdict
import random #to use weighted probabilities 
from kivy.properties import ListProperty
import pickle


#the data structure holds the following from
#from{
# to: frequency}
class HomeScreen(Screen):
    pass

class HowToPlayScreen(Screen):  # screeeeeeeeeeeem
    pass

from kivy.clock import Clock
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen

class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid_size = 5
        self.correct_predictions = 0
        self.player_pos = (0, 0)
        self.cop_pos = (2, 2)
        self.cells = {}
        self.predicted_move = (5, 5)  # Start with invalid cell
        self.total_time = 5 * 60
        self.remaining_time = self.total_time
        self.timer_event = None
        self.timer_started = False
        self.transition_counts = defaultdict(lambda: defaultdict(int))
        self.previous_player_pos = None
        self.was_random_prediction = False
        self.move_count = 0
        Window.bind(on_key_down=self._on_key_down)
        

    def generate_heatmap(self):
        current_pos = self.player_pos
        transitions = self.transition_counts.get(current_pos, {})
        total = sum(transitions.values())
        if total == 0:
            return {pos: 0 for pos in self.cells}
        heatmap = {pos: transitions.get(pos, 0) / total for pos in self.cells}
        return heatmap

    def open_heatmap(self):
        heatmap_data = self.generate_heatmap()
        app = App.get_running_app()
        heatmap_screen = app.root.get_screen('heatmap')
        heatmap_screen.heat_data = heatmap_data
        heatmap_screen.grid_size = self.grid_size
        app.root.current = 'heatmap'


    def predict_next_move(self, current_player_pos):
        move_dict = self.transition_counts.get(current_player_pos, {})
        
        if not move_dict:
            self.was_random_prediction = True
            return
        self.was_random_prediction = False
        goal_cell = (self.grid_size - 1, self.grid_size - 1)
        possible_moves = [pos for pos in move_dict if pos != goal_cell]
        weights = [move_dict[pos] for pos in possible_moves]

        if not possible_moves:
            self.was_random_prediction = True
            return
        predicted_move = random.choices(possible_moves, weights=weights, k=1)[0]
        return predicted_move

    def on_enter(self):
        self.generate_grid()
        self.update_player_display()
        if not self.timer_started:
            self.start_timer(reset=True)
        else:
            self.resume_timer()

    def on_pre_leave(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None

    def start_timer(self, reset=True):
        if reset:
            self.remaining_time = self.total_time
            self.update_timer_label()
        if self.timer_event:
            self.timer_event.cancel()
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)
        self.timer_started = True

    def update_timer(self, dt):
        self.remaining_time -= 1
        self.update_timer_label()
        if self.remaining_time <= 0:
            self.timer_event.cancel()
            self.timer_event = None
            self.timer_started = False
            App.get_running_app().root.current = 'lost'

    def update_timer_label(self):
        mins, secs = divmod(self.remaining_time, 60)
        self.ids.timer_label.text = f"{mins:02}:{secs:02}"

    def pause_game(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        App.get_running_app().root.current = 'pause'

    def resume_timer(self):
        if not self.timer_event and self.timer_started:
            self.timer_event = Clock.schedule_interval(self.update_timer, 1)

    def reset_game(self):
        self.timer_started = False
        self.start_timer(reset=True)
        self.player_pos = (0, 0)
        self.correct_predictions = 0
        self.previous_player_pos = None
        self.transition_counts.clear()
        self.update_player_display()

    def generate_grid(self):
        grid = self.ids.game_grid
        grid.clear_widgets()
        self.cells = {}
        for y in range(self.grid_size - 1, -1, -1):
            for x in range(self.grid_size):
                btn = Button(background_normal='', background_color=(0.95, 0.95, 0.95, 1))
                self.cells[(x, y)] = btn
                grid.add_widget(btn)
        self.update_player_display()

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        direction = {'w': (0, 1), 's': (0, -1), 'a': (-1, 0), 'd': (1, 0)}.get(codepoint.lower())
        if direction:
            new_x = self.player_pos[0] + direction[0]
            new_y = self.player_pos[1] + direction[1]
            if 0 <= new_x < self.grid_size and 0 <= new_y < self.grid_size:
                prev_pos = self.player_pos
                if self.move_count >= 1:
                    self.predicted_move = self.predict_next_move(prev_pos)
                self.player_pos = (new_x, new_y)
                if self.previous_player_pos:
                    self.transition_counts[self.previous_player_pos][self.player_pos] += 1
                self.previous_player_pos = self.player_pos
                self.move_count += 1
                self.update_player_display()
                if self.move_count > 1:
                    self.check_prediction()
                self.checkWin()

    def check_prediction(self):
        if self.was_random_prediction:
            print("Prediction was random — not counting")
            return
        if self.player_pos == self.predicted_move:
            self.correct_predictions += 1
            print("Correct prediction")
            if self.correct_predictions == 2:
                print("Two correct predictions — game over")
                App.get_running_app().root.current = 'lost'
                self.reset_game()

    def update_player_display(self):
        for pos, btn in self.cells.items():
            if pos == self.player_pos:
                btn.background_color = (1, 0.7, 0.8, 1)
            elif pos == (self.grid_size - 1, self.grid_size - 1):
                btn.background_color = (1, 0.84, 0, 1)
            else:
                btn.background_color = (0.95, 0.95, 0.95, 1)

    def checkWin(self):
        if self.player_pos == (self.grid_size - 1, self.grid_size - 1):
            self.player_pos = (0, 0)
            self.timer_started = False
            App.get_running_app().root.current = 'won'


class HeatmapScreen(Screen):
    heat_data = {}
    grid_size = 5

    def on_enter(self):
        self.display_heatmap()

    def display_heatmap(self):
        grid = self.ids.heatmap_grid
        grid.clear_widgets()

        for y in range(self.grid_size - 1, -1, -1):  # top to bottom
            #kivy inverted grid
            for x in range(self.grid_size):
                pos = (x, y)
                danger = self.heat_data.get(pos, 0)

                color = (
                    1.0,
                    1.0 - danger*0.8,  # more red = more danger
                    1.0 - danger*0.8,
                    1
                )

                btn = Button(
                    text=f"{danger:.2f}" if danger > 0 else "",
                    background_color=color,
                    background_normal='',
                    disabled=True
                )
                grid.add_widget(btn)
class PauseScreen(Screen):
    pass

class CreditsScreen(Screen):
    pass

class LostScreen(Screen):
    pass

class WinScreen(Screen):
    pass

class JailBreakApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition(duration=0.2, direction='left'))

        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(HowToPlayScreen(name="howToPlay"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(PauseScreen(name="pause"))
        sm.add_widget(CreditsScreen(name="credits"))
        sm.add_widget(LostScreen(name="lost"))
        sm.add_widget(WinScreen(name="won"))
        sm.add_widget(HeatmapScreen(name="heatmap"))


        return sm

if __name__ == '__main__':
    JailBreakApp().run()