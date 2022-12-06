import argparse
import xml.etree.ElementTree as ET
from map import Map, find_all_path_limits
import glob
import os
import pickle
import math

NODE_BLACKLIST = [473825011, 885828038, 473825019, 1906733267, 892250422, 2154875881, 2154895367,
                  1386431595, 2154895359, 1997393804, 1997393824, 1997393826, 2154895478, 2154895574,
                  2154895777, 2154895785, 2154895806, 1997393921, 2153756873, 2153756875, 424463694,
                  1997393867,
                  1997393873,
                  1997393894,
                  340293912,
                  892253337,
                  1997393921, 2153756875, 2153756873, 2153756876, 153756882, 2153756882, 2153756889, 2153756894,
                  2153756895, 2153756871, 340293914,

                  340293906,340293904,
                  427783591,340293904,
                  2154987358,2154987353,2154987340,892259484,
                  2154987685,2154987680,615943113,
                  2514384402,2514384398,2514384394,2514384390,2514384392,2514384396,2514384400,2514384402,
                  2514384402,2514384404,2514384406,2514384408,2514384410,2514384412,2514384413,2514384415,2514384417,2514384419,
                  1893965307,1997393726,2154278294,2154278309,2154278305,
                  2153763530,2153763536,2152393841,
                  503420260,2154987601,883512171,503420261,2154987620,503420263,2154987656,2154987698,

                  881220550, 881220555, 1906845961, 881220559, 1906845962, 881220567, 1906845968, 881220573, 1906845976, 881220575, 1906845993, 881220489, 881220488, 881220491, 1906846034, 881220445, 1906846041, 881220450, 1906846084, 881220454, 1906846093, 1906846096, 881220468,
                  917153648, 1906845876, 836960379,
                  917153609, 917153608, 836960374,
                  4537024801, 4537024796, 881133879, 881133793, 3595463828, 3110214412, 881133791, 881133788, 3110214420, 3110214418, 3595463802, 881133786, 3110214416, 881133785, 3595463836, 881133999, 3595463844, 3595463842, 881133932,
                  881133951, 3110214406, 881133957,
                881133990, 1906846165, 881133975, 1906846168, 881133957,
                836945271, 881133951,
                473824869, 473824867, 473824855,
                473824863, 881220024,
                836975148, 836975262,
                836975262, 836975155,
                881133845, 881797673, 3595463854, 3595434486, 881133842, 3595463818, 881133840, 881133830, 881133832,
                2152371083, 2152371087, 2152371065, 2152371071, 428151985, 2152371083,
                2152371083, 2152371155, 10319581,

6105989409, 6105989410, 6105989411, 6105989412, 6105989413, 6105989406,
7925845339, 1903104663,
836975150, 3110214413,
881133698, 836976293,
7434687707, 836976293,
881133708, 881133948,
836960940, 881134213,
6575596594, 6575596593, 6575596592, 6575596591, 6575596590, 6575596589, 6575596588, 6575596594,
6071687296, 6071687295, 6071687262,
882648174, 882648179, 1906732530, 882648191, 425942328,
1903104377, 3593636265, 31073157,

2154987703, 2154987709, 503420264, 2153760613,
2154987619, 615943114,
615943105, 2154987575,
2154875724, 892251432,
615943110, 615943106,
2154987464, 615943106
                  ]


class OSMFile:

    def __init__(self, path):
        self.path = path
        self.file = None
        self.file = ET.parse(self.path).getroot()

    def get_nodes(self):
        xml_nodes = self.file.findall("node")
        nodes = {}
        for xml_node in xml_nodes:
            nodes[int(xml_node.attrib["id"])] = (float(xml_node.attrib["lon"]), float(xml_node.attrib["lat"]))

        return nodes


def build_weights_for_route(route, freq):
    weights = []
    for i, point in enumerate(route[1:]):
        prev = route[i - 1]
        key = (prev["osm"], point["osm"]) if prev["osm"] < point["osm"] else (point["osm"], prev["osm"])
        f = freq[key]
        weights.append(math.ceil(f / 5.0))

    return weights


def update_freq(nodes, freq):
    for i, node in enumerate(nodes[1:], 1):
        prev = nodes[i - 1]
        key = (prev, node) if prev < node else (node, prev)
        if key not in freq:
            freq[key] = 0
        freq[key] += 1


def load_route_and_update_freq(file, osm_nodes, freq):
    route = []
    points, snapped, nodes_cache = pickle.load(open(file, "rb"))

    nodes = [node for node in nodes_cache if node not in NODE_BLACKLIST]

    for node in nodes:
        if node not in NODE_BLACKLIST:
            route.append({"osm": node, "pos": osm_nodes[node]})
    update_freq(nodes, freq)
    return route


def normalize_freq(freq):
    max_freq = max(freq.values())
    for key in freq:
        freq[key] = freq[key] / max_freq


# Top n% should all equal 1, then rest 0-1
def normalize_freq_squash(freq, squash_top_perc):
    assert 0 <= squash_top_perc <= 1
    sorted_values = sorted(freq.values())
    n_to_squash = int(squash_top_perc * len(sorted_values))
    squash_lower = sorted_values[len(sorted_values) - n_to_squash]
    for key in freq:
        n = freq[key] / squash_lower
        n = 1 if n >= 1 else n
        freq[key] = n

def debug_route(file, osm_nodes):
    points, snapped, nodes = pickle.load(open(file, "rb"))
    map = Map(3000, 3000, 0, 0, 0, 0)

    node_points = []
    for node in nodes:
        lon, lat = osm_nodes[node]
        node_points.append((lon + 0.1, lat))

    map.add_points(node_points, (100, 255, 100))

    # nodes = [nodes[0]] + nodes[len(nodes) - 11:]
    freq = {}
    update_freq(nodes, freq)
    map.plot_from_freq(freq, osm_nodes)

    map.show()


def main():
    parser = argparse.ArgumentParser(description="Generate heatmap from FIT files")
    parser.add_argument("osm_file", metavar="OSM_File", help="OSM file for region")
    parser.add_argument("cache_dir", metavar="cache_dir", help="Location of snapped route cache")
    args = parser.parse_args()

    osm = OSMFile(args.osm_file)
    osm_nodes = osm.get_nodes()

    routes = []
    freq = {}
    files = glob.glob(os.path.join(args.cache_dir, "*.bin"))

    for i, file in enumerate(files):
        routes.append(load_route_and_update_freq(file, osm_nodes, freq))
    normalize_freq_squash(freq, .3)

    a, b, c, d = find_all_path_limits(routes)
    map = Map(1000, 1000, a, b, c, d)
    map.draw_coastline()
    for i, route in enumerate(routes):
        print("Adding route {}/{}".format(i + 1, len(routes)))
        map.add_path([x["osm"] for x in route], freq, osm_nodes)
    map.save("mapmap.svg")


if __name__ == '__main__':
    main()
