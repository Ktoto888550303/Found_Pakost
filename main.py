import os
import sys
from dataclasses import dataclass
import io
import requests
import arcade
from PIL import Image
from constans import *


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


@dataclass
class MapAPI:
    api_key: str

    def get_map_image(self, coordinates: Coordinates, span: Span) -> bytes:
        params = {
            "ll": coordinates.as_string,
            "spn": span.as_string,
            "apikey": self.api_key
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
        self._update_map()

    @staticmethod
    def _read_api_key() -> str:
        with open(API_KEY_FILE, 'r') as file:
            return file.readline().strip()

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
        api_key = self._read_api_key()
        api = MapAPI(api_key)
        image_data = api.get_map_image(self._coordinates, self._span)
        image = Image.open(io.BytesIO(image_data))
        resized_image = image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        resized_image.save(MAP_FILE)
        self._background = arcade.load_texture(MAP_FILE)


    def on_draw(self) -> None:
        self.clear()
        self._draw_background()

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