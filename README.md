# WatershedDelineation
An open source solution that can serve as an alternative way of Arcpy

## Main Components
 - `WhiteboxTools` is used for the core hydrological operations.
 - `GDAL/OGR` convert the final raster watershed to polygons
 - `GeoPandas` dissolves the polygons.
 - Uses `rasterstats` to add the zonal statistics

## Acknowledgements
This project utilizes the [whitebox-python package](https://github.com/opengeos/whitebox-python) for geospatial analysis.

## Usage
