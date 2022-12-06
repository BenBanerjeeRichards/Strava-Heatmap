import math
import pickle
from random import randint

from svg import SVGRenderer


def find_path_limits(locations):
    max_x = locations[0]["pos"][0]
    min_x = locations[0]["pos"][0]

    max_y = locations[0]["pos"][1]
    min_y = locations[0]["pos"][1]

    for location in locations:
        if location["pos"][0] > max_x:
            max_x = location["pos"][0]
        if location["pos"][0] < min_x:
            min_x = location["pos"][0]
        if location["pos"][1] > max_y:
            max_y = location["pos"][1]
        if location["pos"][1] < min_y:
            min_y = location["pos"][1]

    return min_x, max_x, min_y, max_y


def find_all_path_limits(list_of_locations):
    max_x = -1000
    min_x = 10000
    max_y = -1000
    min_y = 1000

    for locations in list_of_locations:
        if len(locations) == 0:
            continue
        min_xl, max_xl, min_yl, max_yl = find_path_limits(locations)
        if min_xl < min_x:
            min_x = min_xl
        if max_xl > max_x:
            max_x = max_xl
        if min_yl < min_y:
            min_y = min_yl
        if max_yl > max_y:
            max_y = max_yl

    return max_x, min_x, max_y, min_y


class Map:

    def __init__(self, width, height, x_min, x_max, y_min, y_max):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.width = width
        self.height = height
        self.line_color = (255, 0, 0)
        self.svg = SVGRenderer(self.width, self.height, (0, 0, 0))
        self.count = 1
        self.completed_paths = {}

    def path_id(self, osm_path):
        return ",".join([str(x) for x in osm_path])

    def save(self, path):
        svg = self.svg.generate()
        open(path, "w+").write(svg)

    def draw_line(self, x1, y1, x2, y2, width=1, color=None):
        color = self.line_color if color is None else color
        self.svg.draw_line(x1, y1, x2, y2, width=width, color=color)

    def project(self, point):
        high_x = self.x_max + -1 * self.x_min
        prop = float(point[0] + -1 * self.x_min) / high_x
        x = prop * self.width

        high_y = self.y_max + -1 * self.y_min
        prop = float(point[1] + -1 * self.y_min) / high_y
        y = prop * self.height

        assert 0 <= x <= self.width
        assert 0 <= y <= self.height

        return (x, y)

    def mercator(self, point):
        lat_min = 58.74
        mapLonLeft = -3.443673
        long_max = -2.5
        mapLonDelta = long_max - mapLonLeft
        mapLatBottomDegree = math.radians(lat_min)

        longitude, latitude = point

        x = (longitude - mapLonLeft) * (self.width / mapLonDelta)
        latitude = latitude * math.pi / 180
        worldMapWidth = ((self.width / mapLonDelta) * 360) / (2 * math.pi)
        mapOffsetY = (worldMapWidth / 2 * math.log(
            (1 + math.sin(mapLatBottomDegree)) / (1 - math.sin(mapLatBottomDegree))))
        y = self.height - (
                (worldMapWidth / 2 * math.log((1 + math.sin(latitude)) / (1 - math.sin(latitude)))) - mapOffsetY)
        return x, y

    def add_points(self, points, color=None):
        past_point = points[0]
        for point in points[1:]:
            x2, y2 = self.mercator(point)
            x1, y1 = self.mercator(past_point)
            self.draw_line(x1, y1, x2, y2, color=color, width=1)
            past_point = point

    def add_weighed_points(self, points, weights):
        assert len(points) - 1 == len(weights)
        for i, point in enumerate(points[1:]):
            past_point = points[i - 1]
            x2, y2 = self.mercator(point["pos"])
            x1, y1 = self.mercator(past_point["pos"])
            self.draw_line(x1, y1, x2, y2, width=weights[i])

    def add_routes(self, routes):
        for route in routes:
            for i, point in enumerate(route):
                route[i] = self.mercator(point)

        self.svg.draw_routes(routes)

    def plot_from_freq(self, freq, osm_to_lat_long):
        for key in freq:
            assert freq[key] <= 1.0  # Ensure freq is normalized
            p1, p2 = osm_to_lat_long[key[0]], osm_to_lat_long[key[1]]
            x1, y1 = self.mercator(p1)
            x2, y2 = self.mercator(p2)
            self.draw_line(x1, y1, x2, y2, 5, color=(randint(0, 200), randint(0, 200), randint(0, 100)))

    def logistic(self, frequency):
        m = 0.3
        l = 1.5
        k = 5.9
        return self.clamp(l / (1 + math.pow(math.e, -k * (frequency - m))))

    def tanform(self, freq):
        k = 0.8
        s = 2
        return self.clamp(s * math.atan(((k * freq) ** (1 / 3)) / (0.5 * math.pi)))

    def clamp(self, x):
        if x < 0:
            return 0
        if x > 1:
            return 1
        return x

    def ln(self, frequency):
        log_base = math.e
        assert 0 <= frequency <= 1
        # Freq is linearly normalized between 0 and 1
        log_x = log_base * frequency - frequency + 1
        assert 1 <= log_x <= log_base
        return math.log(log_x, log_base)

    def prop(self, freq):
        return freq

    def determine_path_color(self, frequency, fn=ln) -> (int, int, int):
        f = fn(frequency)
        return 70 + 185 * f, 70 + 185 * f, 0 + 185 * f

    def add_path(self, osm_path, freq_lookup, osm_to_lat_long):
        if len(osm_path) < 2:
            return
        p1 = osm_path[0]
        curr_freq = None
        curr_path = [p1]
        for i, p2 in enumerate(osm_path[1:]):
            freq = freq_lookup[(p1, p2)] if (p1, p2) in freq_lookup else freq_lookup[(p2, p1)]
            assert 0 <= freq <= 1
            curr_freq = freq if curr_freq is None else curr_freq

            if freq != curr_freq or i == len(osm_path) - 2:
                pid = self.path_id(curr_path)
                if pid not in self.completed_paths:
                    points = list(map(lambda x: self.mercator(osm_to_lat_long[x]), curr_path))
                    self.svg.draw_path(points, self.determine_path_color(curr_freq, self.prop), curr_path,
                                       self.count, stroke_width=1)
                    self.count += 1
                self.completed_paths[pid] = True
                curr_path = [p1, p2]
                curr_freq = freq
            else:
                curr_path.append(p2)

            p1 = p2

    def draw_coastline(self):
        self.svg.add_comment("The Coastline")
        with open("coastline.bin", "rb") as f:
            for path in pickle.load(f):
                self.svg.draw_path([self.mercator(p) for p in path], (50, 50, 50))
        self.svg.add_comment("End Coastline")
