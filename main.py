import os
import sys
from dataclasses import dataclass
import io
import requests
import arcade
import arcade.gui
from PIL import Image

from addres_searcher import AddressSearcher
from constans import *
from attrs import define


@dataclass(frozen=True)
class Coordinates:
    _lon: float
    _lat: float     #если тебе нужны будут эти корды, то сделай методы как в span

    @property
    def as_string(self) -> str:
        return f"{self._lon},{self._lat}"

    def move(self, dt_lon: float, dt_lat: float) -> "Coordinates":
        new_lon = max(MIN_LON, min(MAX_LON, self._lon + dt_lon))
        new_lat = max(MIN_LAT, min(MAX_LAT, self._lat + dt_lat))
        return Coordinates(new_lon, new_lat)


@dataclass(frozen=True)
class Span:
    _x: float
    _y: float

    @property
    def as_string(self) -> str:
        return f"{self._x},{self._y}"

    @property
    def get_y(self) -> float:
        return self._y

    @property
    def get_x(self) -> float:
        return self._x

    def zoom_in(self) -> "Span":
        return Span(max(MIN_SPN, self._x / ZOOM), max(MIN_SPN, self._y / ZOOM))

    def zoom_out(self) -> "Span":
        return Span(min(MAX_SPN, self._x * ZOOM), min(MAX_SPN, self._y * ZOOM))


@define
class ThemeSwitcher:
    _theme_light: str = 'light'
    _theme_dark: str = 'dark'
    _last_theme: str = 'light'

    @property
    def theme(self) -> str:
        return self._last_theme

    def switch_theme(self) -> None:
        self._last_theme = self._theme_dark if self._last_theme == 'light' else self._theme_light


@dataclass
class MapAPI:
    api_key: str

    def get_map_image(self, coordinates: Coordinates, span: Span, theme: str) -> bytes:
        params = {
            "ll": coordinates.as_string,
            "spn": span.as_string,
            "apikey": self.api_key,
            "theme": theme
        }

        response = requests.get(ADDRESS, params=params)
        response.raise_for_status()
        return response.content


class MapView(arcade.Window):
    def __init__(self, width: int, height: int, title: str, base_coordinates: Coordinates, base_span: Span) -> None:
        super().__init__(width, height, title)
        self._coordinates = base_coordinates
        self._span = base_span
        self._background = None
        self._theme_switcher = ThemeSwitcher()
        self._update_map()

        self._ui_manager = arcade.gui.UIManager()
        self._ui_manager.enable()
        self._anchor_layout = arcade.gui.UIAnchorLayout()

        self._theme_box_layout = arcade.gui.UIBoxLayout()
        self._theme_switch_button = arcade.gui.UIFlatButton(text="🌚", width=25, height=25)
        self._theme_switch_button.on_click = self._switch_theme
        self._theme_box_layout.add(self._theme_switch_button)
        self._anchor_layout.add(
            child=self._theme_box_layout,
            anchor_x="right",
            anchor_y="top",
            align_y=-10,
            align_x=-10
        )

        self._search_address_layout = arcade.gui.UIBoxLayout()
        self._address_inputer = arcade.gui.UIInputText(
            width=300,
            height=40,
            text='Африка',
            text_color=arcade.color.ARCADE_YELLOW
        ).with_border(color=arcade.color.GRAY)

        self._search_address_layout.add(self._address_inputer)
        self._anchor_layout.add(
            child=self._search_address_layout,
            anchor_x="right",
            anchor_y="bottom",
            align_y=25,
            align_x=-10
        )

        self._ui_manager.add(self._anchor_layout)

        self._address_searcher = AddressSearcher(self._read_geocode_api_key())

    @staticmethod
    def _read_static_api_key() -> str:
        with open(API_KEY_FILE, 'r') as file:
            return file.readline().strip()

    @staticmethod
    def _read_geocode_api_key() -> str:
        with open(API_KEY_FILE, 'r') as file:
            _, api = file.readline().strip(), file.readline().strip()
            return api

    def _draw_background(self) -> None:
        x = (self.width - self._background.width) // 2
        y = (self.height - self._background.height) // 2
        arcade.draw_texture_rect(
            self._background,
            arcade.LBWH(x, y, self._background.width, self._background.height)
        )

    def _move(self, dt_lon: float, dt_lat: float) -> None:
        self._coordinates = self._coordinates.move(dt_lon, dt_lat)

    def _zoom_in(self) -> None:
        self._span = self._span.zoom_in()

    def _zoom_out(self) -> None:
        self._span = self._span.zoom_out()

    def _update_map(self) -> None:
        api_key = self._read_static_api_key()
        api = MapAPI(api_key)
        image_data = api.get_map_image(self._coordinates, self._span, self._theme_switcher.theme)
        image = Image.open(io.BytesIO(image_data))
        resized_image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        resized_image.save(MAP_FILE)
        self._background = arcade.load_texture(MAP_FILE)

    def _switch_theme(self, event: arcade.gui.UIOnClickEvent) -> None:
        self._theme_switcher.switch_theme()
        self._theme_switch_button.text = '🌚' if self._theme_switcher.theme == 'light' else '🌝'
        self._update_map()

    def on_draw(self) -> None:
        self.clear()
        self._draw_background()
        self._ui_manager.draw()

    def on_key_press(self, key: int, modifiers: int) -> None:
        move_step_x = self._span.get_x * MOVE_STEP_RATIO
        move_step_y = self._span.get_y * MOVE_STEP_RATIO
        need_update = True

        if key == arcade.key.W:
            self._move(0, move_step_y)
        elif key == arcade.key.S:
            self._move(0, -move_step_y)
        elif key == arcade.key.A:
            self._move(-move_step_x, 0)
        elif key == arcade.key.D:
            self._move(move_step_x, 0)
        elif key == arcade.key.E:
            self._zoom_in()
        elif key == arcade.key.Q:
            self._zoom_out()
        elif key == arcade.key.ENTER:
            self._coordinates = Coordinates(*self._address_searcher.search_address(self._address_inputer.text))
        else:
            need_update = False

        if need_update:
            self._update_map()


def parse_arguments():
    if len(sys.argv) == 5:
        lon = float(sys.argv[1])
        lat = float(sys.argv[2])
        spn_x = float(sys.argv[3])
        spn_y = float(sys.argv[4])

        lon = max(MIN_LON, min(MAX_LON, lon))
        lat = max(MIN_LAT, min(MAX_LAT, lat))
        spn_x = max(MIN_SPN, min(MAX_SPN, spn_x))
        spn_y = max(MIN_SPN, min(MAX_SPN, spn_y))

        return Coordinates(lon, lat), Span(spn_x, spn_y)
    return Coordinates(133.7751, -25.2744), Span(40.0, 40.0)


def main() -> None:
    coordinates, span = parse_arguments()
    MapView(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, coordinates, span)
    arcade.run()
    os.remove(MAP_FILE)


if __name__ == "__main__":
    main()