# Strava-Heatmap
Cleaner Strava heatmap

![](Final.png)

Goal was to take some .fit files and generate a heatmap. Strava already does this, but it just overlays routes on top of each over. 

This project uses osrm to snap routes to roads (this heatmap was only used for road cycling). This creates a really clean heatmap that can be used 
as a poster

This entire project is a bodge and is full of hardcoded things that only make sense on the Orkney map

In short, don't expect to be able to use this project out of the box for generating your own heatmaps. I can't even remember how to to go from scratch 
myself as I generated lots of intermediate cache files to speed up iteration of the graphics. If you really want to try - 

* Get the osm data for the region you want to map
* Get osrm docker container running and forward its port to localhost:5000
* Get some fit files containing the routes you want to map 

You can also generate a coastline - I think I extracted the way out of OSM data in coastline.py. 

