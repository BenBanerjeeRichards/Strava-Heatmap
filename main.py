import argparse
import glob
import os
import fitparse
from math import pow
import osrm
import sys
from map import Map, find_path_limits, find_all_path_limits
from cache import RouteCache

CLEAN_NODES_ROLLING_NUM = 10


def extract_timestamps_and_locations(fit_path):
    file = fitparse.FitFile(fit_path)
    semi_const = 180.0 / pow(2, 31)
    timestamps = []
    positions = []
    for record in file.get_messages("record"):
        lat = record.get("position_lat")
        long = record.get("position_long")
        lat = 0 if lat is None else lat.value * semi_const
        long = 0 if long is None else long.value * semi_const
        timestamp = record.get("timestamp")

        if timestamp is not None and lat != 0 and long != 0:
            timestamps.append(int(timestamp.value.timestamp()))
            positions.append([long, lat])

    return timestamps, positions


def get_fit_file_paths(root_dir: str):
    return glob.glob(os.path.join(root_dir, "*.fit"))


def snap_to_roads(osrm_client: osrm.Client, fit_file_path: str, cache: RouteCache, cache_only=False, ignore_cache=False):
    if not ignore_cache:
        cache_attempt = cache.get_from_cache(fit_file_path)
        if cache_attempt is not None:
            return cache_attempt
        if cache_only:
            print("{} - Skipping as not in cache and cache_only=True".format(fit_file_path))
            return None, None, None

    timestamps, positions = extract_timestamps_and_locations(fit_file_path)
    resp = osrm_client.match(timestamps=timestamps, coordinates=positions, annotations=True)
    snapped = []

    for waypoint in resp["tracepoints"]:
        if waypoint is None:
            print("Failed to snap location", file=sys.stderr)
            continue

        snapped.append(waypoint["location"])

    osm_nodes = get_osm_nodes(resp["matchings"])

    if not ignore_cache:
        cache.save_to_cache(fit_file_path, positions, snapped, osm_nodes)
    return positions, snapped, osm_nodes


def get_osm_nodes(matchings):
    osm_nodes = []
    curr_first = None
    curr_last = None

    for route in matchings:
        for leg in route["legs"]:
            nodes = leg["annotation"]["nodes"]
            assert len(nodes) >= 2
            if nodes[0] != curr_first or nodes[-1] != curr_last:
                for node in nodes:
                    osm_nodes.append(node)
                curr_first = nodes[0]
                curr_last = nodes[-1]

    # Now clean to remove duplicates (of which there will be lots of)
    cleaned_nodes = []
    for i, node in enumerate(osm_nodes):
        min_idx = i - CLEAN_NODES_ROLLING_NUM
        min_idx = 0 if min_idx < 0 else min_idx
        if node in osm_nodes[min_idx:i]:
            continue

        cleaned_nodes.append(node)
    return cleaned_nodes


def build_cache(osrm_client, fit_files, cache: RouteCache):
    for fit_file in fit_files:
        try:
            snap_to_roads(osrm_client, fit_file, cache)
        except osrm.OSRMClientException as e:
            print("{} - Failed as outside of osrm map".format(fit_file))
            continue


def main():
    parser = argparse.ArgumentParser(description="Generate heatmap from FIT files")
    parser.add_argument("fit_file_root", metavar="fit_file_path", help="Root directory of FIT files")
    parser.add_argument("--osrm", help="OSRM backend server url")
    parser.add_argument("--cache-dir", help="Location of snapped route cache")
    parser.add_argument("--cached-only", help="Only load routes that are cached", action="store_true")
    parser.add_argument("--ignore-cache", help="Ignore cache", action="store_true")

    args = parser.parse_args()

    if args.ignore_cache and args.cached_only:
        print("Incompatible options --ignore-cache and --cached-only")
        sys.exit(1)

    osrm_url = "http://localhost:5000" if args.osrm is None else args.osrm
    cache_dir = "cache" if args.cache_dir is None else args.cache_dir

    osrm_client = osrm.Client(host=osrm_url)
    fit_file_path = args.fit_file_root
    fit_files = get_fit_file_paths(fit_file_path)
    cache = RouteCache(cache_dir)

    snapped_paths = []
    old_paths = []

    for fit_file in fit_files:
        try:
            old, snapped, nodes = snap_to_roads(osrm_client, fit_file, cache, args.cached_only, args.ignore_cache)
        except osrm.OSRMClientException as e:
            print("{} - Failed as outside of osrm map".format(fit_file))
            continue
        if snapped:
            snapped_paths.append(snapped)
            old_paths.append(old)

    min_x, max_x, min_y, max_y = find_all_path_limits(snapped_paths)
    map = Map(2400, 2400, min_x, max_x, min_y, max_y)

    for i, path in enumerate(snapped_paths):
        print("Adding path {}/{}".format(i, len(snapped_paths)))
        map.add_points(path)

    map.save("mapmap.svg")

    # min_x, max_x, min_y, max_y = find_all_path_limits(old_paths)
    # map2 = Map(2400, 2400, min_x, max_x, min_y, max_y)
    #
    # for path in old_paths:
    #     map2.add_points(path)
    #
    # map2.show()


if __name__ == '__main__':
    main()
