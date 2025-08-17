# WatershedDelineation
An open source solution that can serve as an alternative way of ArcPy

## Overview

### Definition of Watershed Delineation
Watershed delineation is the process of identifying the boundary of a land area where all precipitation and surface water drain to a single, common outlet, such as a point on a river, a lake, or a reservoir. Think of it as drawing a line around a funnel; everything that falls inside the line will eventually pass through the spout at the bottom. The spout is the "pour point" or outlet.

### Why this project?
There are many commercial and open source tools available for watershed delineation.

[PySheds](https://github.com/mdbartos/pysheds) is a popular open source library for watershed delineation. However, it has some limitations for a regional scale watershed delineation.
- It requires a pre-defined pour point. Although technically only if system converged into one outlet can be called a watershed, in practice, it is often useful to delineate potential multiple watersheds in a region. 

[ArcPy](https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/watershed.htm) is a powerful tool for watershed delineation, but it is a commercial product and requires a license.
- Not only is it licensed, but it is also a Windows-only solution, which limits its accessibility for many users.

This project aims to provide an open source, cross-platform solution for watershed delineation that can handle multiple pour points and is easy to use.

## Main Components
 - `WhiteboxTools` is used for the core hydrological operations.
 - `GDAL/OGR` convert the final raster watershed to polygons
 - `GeoPandas` dissolves the polygons.
 - Uses `rasterstats` to add the zonal statistics

## Acknowledgements
This project utilizes the [whitebox-python package](https://github.com/opengeos/whitebox-python) for geospatial analysis.

## Usage
```bash
conda create -n watershed python=3.10
conda activate watershed
conda install gdal
pip install -r requirements.txt
```


## What's next?
- Rebuild the core hydrological operations using Python.