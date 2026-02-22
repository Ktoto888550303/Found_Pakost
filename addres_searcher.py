from attrs import define
from requests import get


@define
class AddressSearcher:
    _api_key: str
    _requests_address: str = 'https://geocode-maps.yandex.ru/v1/'

    def search_address(self, address: str) -> dict:
        geocoder_params = {
            "apikey": self._api_key,
            "geocode": address,
            "format": "json"}

        response = get(self._requests_address, params=geocoder_params)
        address = response.json()
        toponym = address["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        toponym_coodrinates = toponym["Point"]["pos"]
        return toponym_coodrinates.split(" ")

