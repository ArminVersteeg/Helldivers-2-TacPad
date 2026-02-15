from kivy.config import Config
Config.set('graphics', 'width', '750')
Config.set('graphics', 'height', '470')
Config.set('graphics', 'resizable', '0')

import kivy
kivy.require("2.3.0")

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image as uixImage
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.graphics import RoundedRectangle, Color, Line
from kivy.animation import Animation
from kivy.core.text import LabelBase

from stratagems import STRATAGEMS

# ==========================================
# Register custom Helldivers font
# ==========================================
LabelBase.register(name="HelldiversFont", fn_regular="fonts/helldivers.otf")


# ==========================================
# Audio
# ==========================================
import pygame
pygame.mixer.init()
arrow_sound = pygame.mixer.Sound("audio/arrow.ogg")
boot_sound = pygame.mixer.Sound("audio/boot_track.ogg")


# ==========================================
# Loading Bar
# ==========================================
class LoadingBar(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0
        with self.canvas:
            Color(0.1, 0.1, 0.1, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[5])
            Color(0, 0.8, 1, 1)
            self.fg_rect = RoundedRectangle(pos=self.pos, size=(0, self.height), radius=[5])
        self.bind(pos=self.update_rects, size=self.update_rects)

    def update_rects(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.fg_rect.pos = self.pos
        self.fg_rect.size = (self.width * self.progress / 100, self.height)

    def set_progress(self, value):
        self.progress = value
        self.update_rects()


# ==========================================
# Main TacPad
# ==========================================
class TacPad(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.booting = True
        self.arrows_active = False
        self.user_input_sequence = []
        self.inactivity_event = None
        self.strat_image = None
        self.strat_timeout_event = None

        # Stratagems
        self.stratagems = STRATAGEMS

        # Background (boot background first)
        from kivy.uix.image import Image
        self.bg = Image(
            source="images/background/boot_background.png",
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1)
        )
        self.add_widget(self.bg)

        # INPUT STRATAGEM label
        self.start_label = Label(
            text="INPUT\nSTRATAGEM",
            font_size="80sp",
            halign="center",
            valign="middle",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            opacity=0,
            font_name="HelldiversFont"
        )
        self.start_label.bind(size=self.start_label.setter('text_size'))
        self.add_widget(self.start_label)

        # Arrow Image Sequence Display (top-left)
        self.sequence_display = BoxLayout(
            orientation="horizontal",
            spacing=8,
            size_hint=(None, None),
            height=60,
            pos_hint={"x": 0.02, "top": 0.98},
            opacity=0
        )
        self.add_widget(self.sequence_display)

        # Startup screen
        self.startup_layout = FloatLayout(size_hint=(1, 1))
        self.add_widget(self.startup_layout)

        self.startup_label = Label(
            text="PERSONAL HELLPAD\nSYSTEM",
            font_size="70sp",
            font_name="HelldiversFont",
            halign="center",
            pos_hint={"center_x": 0.5, "center_y": 0.5}
        )
        self.startup_layout.add_widget(self.startup_label)

        self.loading_bar = LoadingBar(
            size_hint=(0.6, 0.05),
            pos_hint={"center_x": 0.5, "center_y": 0.205}
        )
        self.startup_layout.add_widget(self.loading_bar)

        boot_sound.play()
        self.loading_progress = 0
        self.loading_event = Clock.schedule_interval(self.update_loading, 8.5 / 100)
        self.bind(on_touch_down=self.activate_arrows)

    # ===============================
    # Sequence Display Helpers
    # ===============================
    def add_arrow_to_display(self, direction):
        arrow_img = uixImage(
            source=f"images/arrows/{direction}.png",
            size_hint=(None, None),
            size=(45, 45),
            allow_stretch=True,
            keep_ratio=True
        )
        self.sequence_display.add_widget(arrow_img)

        if self.sequence_display.opacity == 0:
            self.fade_widget(self.sequence_display, 1, duration=0.15)

    def clear_sequence_display(self):
        self.user_input_sequence = []
        self.sequence_display.clear_widgets()
        self.fade_widget(self.sequence_display, 0, duration=0.15)

    # ===============================
    # Loading logic
    # ===============================
    def update_loading(self, dt):
        self.loading_progress += 1
        self.loading_bar.set_progress(self.loading_progress)
        if self.loading_progress >= 100:
            self.remove_widget(self.startup_layout)

            # Switch to main background after boot
            self.bg.source = "images/background/background.png"

            self.booting = False
            self.fade_widget(self.start_label, 1, duration=0.2)
            return False
        return True

    # Fade helper
    def fade_widget(self, widget, target_opacity, duration=0.2, on_complete=None):
        anim = Animation(opacity=target_opacity, duration=duration)
        if on_complete:
            anim.bind(on_complete=lambda *args: on_complete())
        anim.start(widget)

    # Touch handler
    def activate_arrows(self, instance, touch):
        if self.booting:
            return
        if not self.arrows_active:
            self.fade_widget(self.start_label, 0, duration=0.2, on_complete=self.show_arrows)
        elif self.strat_image:
            if self.strat_timeout_event:
                self.strat_timeout_event.cancel()
                self.strat_timeout_event = None
            self.hide_stratagem(timeout=False)
        else:
            self.reset_inactivity_timer()

    # Arrow screen
    def show_arrows(self):
        if self.start_label.parent:
            self.remove_widget(self.start_label)

        self.create_arrows()
        self.arrows_active = True
        self.reset_inactivity_timer()

        for btn_attr in ['up_btn', 'down_btn', 'left_btn', 'right_btn']:
            btn = getattr(self, btn_attr, None)
            if btn:
                btn.opacity = 0
                self.fade_widget(btn, 1, duration=0.2)

    def create_arrow_button(self, image_path, center_x, center_y, direction):
        btn = Button(
            background_normal=image_path,
            background_down=image_path,
            background_color=(1,1,1,1),  # white tint won't affect much
            size_hint=(None, None),
            size=(120, 120),
            pos_hint={"center_x": center_x, "center_y": center_y},
        )

        # Draw thick white rounded border
        with btn.canvas.before:
            Color(1, 1, 1, 1)  # White
            btn.border_line = Line(
                rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, 10),
                width=4
            )

        # Update border on move/resize
        def update_border(instance, *args):
            instance.border_line.rounded_rectangle = (
                instance.x, instance.y, instance.width, instance.height, 10
            )
        btn.bind(pos=update_border, size=update_border)

        btn.bind(on_press=lambda instance: self.button_pressed(direction))
        return btn

    def create_arrows(self):
        if getattr(self, 'up_btn', None):
            return
        self.up_btn = self.create_arrow_button("images/arrows/up.png", 0.5, 0.7, "up")
        self.left_btn = self.create_arrow_button("images/arrows/left.png", 0.3, 0.4, "left")
        self.down_btn = self.create_arrow_button("images/arrows/down.png", 0.5, 0.4, "down")
        self.right_btn = self.create_arrow_button("images/arrows/right.png", 0.7, 0.4, "right")
        self.add_widget(self.up_btn)
        self.add_widget(self.left_btn)
        self.add_widget(self.down_btn)
        self.add_widget(self.right_btn)

    def remove_arrows(self):
        for btn_attr in ['up_btn', 'down_btn', 'left_btn', 'right_btn']:
            btn = getattr(self, btn_attr, None)
            if btn:
                self.remove_widget(btn)
                setattr(self, btn_attr, None)

    # Stratagem logic
    def button_pressed(self, direction):
        arrow_sound.play()
        self.record_input(direction)

    def record_input(self, direction):
        self.user_input_sequence.append(direction)
        self.add_arrow_to_display(direction)

        possible = False
        for code, data in self.stratagems.items():
            if code[:len(self.user_input_sequence)] == tuple(self.user_input_sequence):
                possible = True
                if len(self.user_input_sequence) == len(code):
                    self.show_stratagem(data["name"], data["image"])
                break

        if not possible:
            self.clear_sequence_display()

    def show_stratagem(self, strat_name, image_path):
        self.clear_sequence_display()
        self.remove_arrows()

        container = FloatLayout(size_hint=(1, 1), opacity=0)

        icon = uixImage(
            source=image_path,
            size_hint=(None, None),
            size=(150, 150),
            pos_hint={"center_x": 0.5, "center_y": 0.65},
            allow_stretch=True,
            keep_ratio=True
        )
        container.add_widget(icon)

        label = Label(
            text=f"REQUESTING:\n{strat_name}",
            font_size="60sp",
            font_name="HelldiversFont",
            halign="center",
            valign="middle",
            pos_hint={"center_x": 0.5, "center_y": 0.35},
            color=(1, 1, 1, 1)
        )
        label.bind(size=label.setter("text_size"))
        container.add_widget(label)

        self.strat_image = container
        self.add_widget(container)
        self.fade_widget(container, 1, duration=0.2)

        if self.inactivity_event:
            self.inactivity_event.cancel()
            self.inactivity_event = None

        self.strat_timeout_event = Clock.schedule_once(
            lambda dt: self.hide_stratagem(timeout=True), 10
        )

    def hide_stratagem(self, timeout=False):
        if self.strat_image:
            self.fade_widget(
                self.strat_image, 0, duration=0.2,
                on_complete=lambda: self._remove_strat_image(timeout)
            )

    def _remove_strat_image(self, timeout):
        if self.strat_image:
            self.remove_widget(self.strat_image)
            self.strat_image = None

        self.clear_sequence_display()

        if timeout:
            self.start_label.opacity = 0
            if not self.start_label.parent:
                self.add_widget(self.start_label)
            self.fade_widget(self.start_label, 1, duration=0.2)
            self.arrows_active = False
            self.reset_inactivity_timer()
        else:
            self.create_arrows()
            self.arrows_active = True

    # Inactivity timer
    def reset_inactivity_timer(self):
        if self.inactivity_event:
            self.inactivity_event.cancel()
        self.inactivity_event = Clock.schedule_once(lambda dt: self.show_input_screen(), 20)

    def show_input_screen(self):
        self.remove_arrows()
        self.clear_sequence_display()
        self.start_label.opacity = 0
        if not self.start_label.parent:
            self.add_widget(self.start_label)
        self.fade_widget(self.start_label, 1, duration=0.2)
        self.arrows_active = False


# ==========================================
# Kivy App
# ==========================================
class TacPadApp(App):
    def build(self):
        self.tacpad = TacPad()
        return self.tacpad

    def on_stop(self):
        if hasattr(self.tacpad, 'loading_event') and self.tacpad.loading_event:
            self.tacpad.loading_event.cancel()
        if self.tacpad.inactivity_event:
            self.tacpad.inactivity_event.cancel()
        if self.tacpad.strat_timeout_event:
            self.tacpad.strat_timeout_event.cancel()


if __name__ == "__main__":
    TacPadApp().run()
