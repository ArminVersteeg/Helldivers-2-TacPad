from kivy.config import Config
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
Config.set('graphics', 'resizable', '0')

import kivy
kivy.require("2.3.0")

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.stencilview import StencilView
from kivy.clock import Clock
from kivy.graphics import RoundedRectangle, Color, Line
from kivy.core.image import Image as CoreImage
from kivy.animation import Animation
from kivy.core.text import LabelBase
from kivy.uix.widget import Widget

# ==========================================
# Register custom Helldivers font
# ==========================================
LabelBase.register(name="HelldiversFont", fn_regular="fonts/helldivers.otf")

# Import pygame for audio
import pygame
pygame.mixer.init()

# Preload sounds
arrow_sound = pygame.mixer.Sound("audio/arrow.ogg")
boot_sound = pygame.mixer.Sound("audio/boot_track.ogg")


class LoadingBar(Widget):
    """Helldivers-style horizontal loading bar."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0  # 0 → 100%

        with self.canvas:
            # Background bar
            Color(0.1, 0.1, 0.1, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[5])
            # Foreground bar
            Color(0, 0.8, 1, 1)
            self.fg_rect = RoundedRectangle(pos=self.pos, size=(0, self.height), radius=[5])

        self.bind(pos=self.update_rects, size=self.update_rects)

    def update_rects(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.fg_rect.pos = self.pos
        self.fg_rect.size = (self.size[0] * self.progress / 100, self.size[1])

    def set_progress(self, value):
        self.progress = value
        self.update_rects()


class TacPad(FloatLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.arrows_active = False
        self.user_input_sequence = []
        self.inactivity_event = None
        self.strat_image = None
        self.strat_timeout_event = None

        # ==========================================
        # Stratagems dictionary
        # ==========================================
        self.stratagems = {
            ("up", "down", "right", "left", "up"): {
                "name": "Reinforce",
                "image": "images/stratagems/reinforce.png"
            },
            ("down", "down", "up", "right"): {
                "name": "Resupply Pod",
                "image": "images/stratagems/resupply.png"
            },
            ("up", "down", "right", "up"): {
                "name": "SoS Beacon",
                "image": "images/stratagems/sos_beacon.png"
            },
            ("up", "right", "down", "down", "down"): {
                "name": "500KG Bomb",
                "image": "images/stratagems/500kg.png",
            },
        }

        # ==========================================
        # Background
        # ==========================================
        from kivy.uix.image import Image
        self.bg = Image(
            source="images/background/background.png",
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1)
        )
        self.add_widget(self.bg)

        # ==========================================
        # Start Label for "INPUT STRATAGEM"
        # ==========================================
        self.start_label = Label(
            text="INPUT\nSTRATAGEM",
            font_size="80sp",
            bold=True,
            halign="center",
            valign="middle",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            opacity=0,
            font_name="HelldiversFont"
        )
        self.start_label.bind(size=self.start_label.setter('text_size'))
        self.add_widget(self.start_label)

        # ==========================================
        # Startup screen widgets
        # ==========================================
        self.startup_layout = FloatLayout(size_hint=(1, 1))
        self.add_widget(self.startup_layout)

        self.startup_label = Label(
            text="PERSONAL HELLPAD\nSYSTEM",
            font_size="80sp",
            bold=True,
            font_name="HelldiversFont",
            halign="center",
            pos_hint={"center_x":0.5, "center_y":0.5}
        )
        self.startup_layout.add_widget(self.startup_label)

        self.loading_bar = LoadingBar(size_hint=(0.6, 0.05), pos_hint={"center_x":0.5, "center_y":0.205})
        self.startup_layout.add_widget(self.loading_bar)

        # Play boot sound
        boot_sound.play()

        # Animate loading bar over 8.5 seconds
        self.loading_progress = 0
        Clock.schedule_interval(self.update_loading, 8.5/100)

        # Bind touch for arrows / stratagem return
        self.bind(on_touch_down=self.activate_arrows)

    # ==========================================
    # Update the loading bar
    # ==========================================
    def update_loading(self, dt):
        self.loading_progress += 1
        self.loading_bar.set_progress(self.loading_progress)
        if self.loading_progress >= 100:
            self.remove_widget(self.startup_layout)
            self.fade_widget(self.start_label, 1, duration=0.2)
            return False
        return True

    # ==========================================
    # Fade helper
    # ==========================================
    def fade_widget(self, widget, target_opacity, duration=0.2, on_complete=None):
        anim = Animation(opacity=target_opacity, duration=duration)
        if on_complete:
            anim.bind(on_complete=lambda *args: on_complete())
        anim.start(widget)

    # ==========================================
    # Activate arrows on first tap or tap to return from stratagem image
    # ==========================================
    def activate_arrows(self, instance, touch):
        if self.arrows_active:
            self.reset_inactivity_timer()
        if not self.arrows_active:
            self.fade_widget(self.start_label, 0, duration=0.2, on_complete=self.show_arrows)
        elif self.strat_image:
            self.hide_stratagem(timeout=False)

    # ==========================================
    # Show arrows screen with fade-in
    # ==========================================
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

    # ==========================================
    # Create arrow button with rounded border
    # ==========================================
    def create_arrow_button(self, image_path, center_x, center_y, direction):
        btn = Button(
            background_normal=image_path,
            background_down=image_path,
            background_color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(120, 120),
            pos_hint={"center_x": center_x, "center_y": center_y},
            opacity=1
        )
        with btn.canvas.after:
            Color(1, 1, 1, 1)
            border = Line(
                rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, 10),
                width=5
            )
        def update_border(instance, value):
            border.rounded_rectangle = (btn.x, btn.y, btn.width, btn.height, 10)
        btn.bind(pos=update_border, size=update_border)
        btn.bind(on_press=lambda instance: self.button_pressed(direction))
        return btn

    # ==========================================
    # Play arrow sound and record input
    # ==========================================
    def button_pressed(self, direction):
        arrow_sound.play()
        self.record_input(direction)

    # ==========================================
    # Record input from user
    # ==========================================
    def record_input(self, direction):
        self.user_input_sequence.append(direction)
        print("Current sequence:", self.user_input_sequence)
        possible = False
        for code, data in self.stratagems.items():
            if code[:len(self.user_input_sequence)] == tuple(self.user_input_sequence):
                possible = True
                if len(self.user_input_sequence) == len(code):
                    print(f"Stratagem activated: {data['name']}")
                    self.show_stratagem(data['image'])
                break
        if not possible:
            print("Invalid sequence. Resetting...")
            self.user_input_sequence = []

    # ==========================================
    # Show stratagem image
    # ==========================================
    def show_stratagem(self, image_path):
        self.remove_arrows()
        container = StencilView(size_hint=(0.6, 0.6), pos_hint={"center_x":0.5, "center_y":0.5}, opacity=0)
        img = CoreImage(image_path)
        img_ratio = img.width / img.height
        with container.canvas:
            self.rounded_img = RoundedRectangle(
                source=image_path,
                pos=container.pos,
                size=container.size,
                radius=[10]
            )
        def update_image(instance, value):
            cw, ch = container.size
            cr = cw / ch
            if cr > img_ratio:
                new_h = ch
                new_w = new_h * img_ratio
            else:
                new_w = cw
                new_h = new_w / img_ratio
            x = container.x + (cw - new_w) / 2
            y = container.y + (ch - new_h) / 2
            self.rounded_img.pos = (x, y)
            self.rounded_img.size = (new_w, new_h)
        container.bind(pos=update_image, size=update_image)
        update_image(container, None)
        self.strat_image = container
        self.add_widget(self.strat_image)
        self.fade_widget(self.strat_image, 1, duration=0.2)
        self.strat_timeout_event = Clock.schedule_once(lambda dt: self.hide_stratagem(timeout=True), 15)

    # ==========================================
    # Hide stratagem image
    # ==========================================
    def hide_stratagem(self, timeout=False):
        if self.strat_image:
            self.fade_widget(self.strat_image, 0, duration=0.2, on_complete=lambda: self._remove_strat_image(timeout))

    def _remove_strat_image(self, timeout):
        if self.strat_image:
            self.remove_widget(self.strat_image)
            self.strat_image = None
        if self.strat_timeout_event:
            self.strat_timeout_event.cancel()
            self.strat_timeout_event = None
        self.user_input_sequence = []
        if timeout:
            if not self.start_label.parent:
                self.start_label.opacity = 0
                self.add_widget(self.start_label)
                self.fade_widget(self.start_label, 1, duration=0.2)
            self.arrows_active = False
        else:
            self.create_arrows()
            self.arrows_active = True
            self.reset_inactivity_timer()
            for btn_attr in ['up_btn', 'down_btn', 'left_btn', 'right_btn']:
                btn = getattr(self, btn_attr, None)
                if btn:
                    btn.opacity = 0
                    self.fade_widget(btn, 1, duration=0.2)

    # ==========================================
    # Remove arrows
    # ==========================================
    def remove_arrows(self):
        for btn_attr in ['up_btn', 'down_btn', 'left_btn', 'right_btn']:
            btn = getattr(self, btn_attr, None)
            if btn:
                self.remove_widget(btn)
                setattr(self, btn_attr, None)

    # ==========================================
    # Create all arrows
    # ==========================================
    def create_arrows(self):
        if getattr(self, 'up_btn', None):
            return
        self.up_btn = self.create_arrow_button("images/arrows/up.png", 0.5, 0.7, "up")
        self.add_widget(self.up_btn)
        self.left_btn = self.create_arrow_button("images/arrows/left.png", 0.3, 0.4, "left")
        self.add_widget(self.left_btn)
        self.down_btn = self.create_arrow_button("images/arrows/down.png", 0.5, 0.4, "down")
        self.add_widget(self.down_btn)
        self.right_btn = self.create_arrow_button("images/arrows/right.png", 0.7, 0.4, "right")
        self.add_widget(self.right_btn)
        self.reset_inactivity_timer()

    # ==========================================
    # Reset inactivity timer
    # ==========================================
    def reset_inactivity_timer(self):
        if self.inactivity_event:
            self.inactivity_event.cancel()
        self.inactivity_event = Clock.schedule_once(lambda dt: self.show_input_screen(), 30)

    # ==========================================
    # Show "Input Stratagem" screen
    # ==========================================
    def show_input_screen(self):
        self.remove_arrows()
        self.user_input_sequence = []
        if not self.start_label.parent:
            self.start_label.opacity = 0
            self.add_widget(self.start_label)
            self.fade_widget(self.start_label, 1, duration=0.2)
        self.arrows_active = False


class TacPadApp(App):
    def build(self):
        return TacPad()


if __name__ == "__main__":
    TacPadApp().run()
