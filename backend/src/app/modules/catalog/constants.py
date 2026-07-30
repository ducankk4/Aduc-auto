"""Domain Constants and Enums for the Catalog Module."""

from enum import Enum


class VehicleCategory(str, Enum):
    """Vehicle Category Classifications."""

    SEDAN = "sedan"
    SUV = "suv"
    MPV = "mpv"
    CROSSOVER = "crossover"
    EV = "electric_vehicle"
    HYBRID = "hybrid"


DEFAULT_CATALOG_PAGE_SIZE = 20
MAX_CATALOG_PAGE_SIZE = 100
