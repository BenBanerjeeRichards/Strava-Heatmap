from random import choice


class SVGRenderer:

    def __init__(self, width, height, background_color=(255, 255, 255)):
        self.width = width
        self.height = height
        r, g, b = background_color

        self.svg = '<svg version="1.1" baseProfile="full" xmlns="http://www.w3.org/2000/svg" width="{}pt" height="{}pt" style="background-color: rgb({}, {}, {})">\n' \
            .format(width, height, r, g, b)

    def draw_line(self, x1, y1, x2, y2, color=(255, 50, 0), width=1):
        r, g, b = color
        self.svg += '<line x1="{}" y1="{}" x2="{}" y2="{}" style="stroke:rgb({}, {}, {});stroke-width:{}" />' \
            .format(x1, y1, x2, y2, r, g, b, width)

    def _generate_route_path(self, route):
        path = "M {} {}".format(route[0][0], route[0][1])
        for point in route[1:]:
            path += " L {} {}".format(point[0], point[1])
        return path

    def draw_routes(self, routes):
        for route in routes:
            self.svg += '<path fill="none" stroke="black" stroke-width="2" shape-rendering="crispEdges" d="{}"/>  \n'.format(
                self._generate_route_path(route))

    def draw_path(self, points, color, osm_points=None, count=None, stroke_width=1):
        if len(points) <= 1:
            return
        if osm_points is not None and count is not None:
            self.add_comment(
                "{}{}: ".format(choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), count) + ", ".join([str(x) for x in osm_points]))
        r, g, b = color
        self.svg += '<path fill="none" stroke="black" stroke-width="{}" style="stroke:rgb({}, {}, {})"  shape-rendering="crispEdges" d="{}" />  \n'.format(
            stroke_width, r, g, b, self._generate_route_path(points))

    def add_comment(self, comment):
        self.svg += "<!-- {} -->\n".format(comment)

    def generate(self) -> str:
        self.svg += "</svg>"
        return self.svg
