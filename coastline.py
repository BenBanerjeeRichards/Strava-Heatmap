import os
import pickle
import sys

import lxml.etree


def ref_to_lat_lon(root):
    nodes = root.findall(".//node")
    lookup = {}
    for node in nodes:
        lookup[node.attrib["id"]] = (float(node.attrib["lon"]), float(node.attrib["lat"]))
    return lookup


def extract_coastline(osm_path: str):
    assert os.path.exists(osm_path)

    tree = lxml.etree.parse(osm_path)
    root = tree.getroot()
    print("Loaded OSM file")
    lookup = ref_to_lat_lon(root)
    print("Loaded node lookup")

    ways = root.findall('.//*[@k="natural"][@v="coastline"]/..')
    coastline = []
    for way in ways:
        path = []
        nodes = way.findall(".//nd")
        for node in nodes:
            path.append(lookup[node.attrib["ref"]])
        coastline.append(path)
        print("Parsed path, N nodes = {}".format(len(path)))
    return coastline


def append_coastline(path):
    existing_coastline = pickle.load(open("coastline.bin", "rb"))
    new_coastline = extract_coastline(path)
    write_coastline(existing_coastline + new_coastline)


def write_coastline(coastline):
    with open("coastline.bin", "wb+") as f:
        pickle.dump(coastline, f)


def main():
    assert len(sys.argv) == 2
    osm_path = sys.argv[1]
    coastline = extract_coastline(osm_path)
    # write_coastline(coastline)
    append_coastline("/Users/bbr/Downloads/flotta.osm")

if __name__ == '__main__':
    main()
