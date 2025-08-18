import argparse
import os
from pathlib import Path
from typing import Sequence

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterstats as rs
from osgeo import gdal, ogr, osr
from whitebox import WhiteboxTools
import shutil

class WatershedPipeline:
    """
    Run the watershed delineation pipeline.
    """
    def __init__(self, input_dem: Path, output_dir: Path):
        self.input_dem = input_dem
        self.output_dir = output_dir.resolve()
        self.wbt: WhiteboxTools = WhiteboxTools()
        shutil.copy(self.input_dem, self.output_dir / self.input_dem.name) # Copy the input DEM to the output directory
        self.wbt.set_working_dir(os.path.abspath(str(self.output_dir)))
        self.wbt.set_verbose_mode(False)
        self.esri_pointer = True  # Default to ESRI pointer for flow direction

        # Define the filenames for the outputs throughout the pipeline
        self.dem_in = self.input_dem.name
        self.dem_filled = "demFilled.tif"
        self.flow_dir = "flowDir.tif"
        self.flow_acc = "flowAcc.tif"
        self.stream_grid = "streamGrid.tif"
        self.stream_link = "streamLink.tif"
        self.watershed_raster = "watershed.tif"
        self.watershed_vector = "watershed.shp"
        self.catchment_vector = "catchment.shp"
        self.catchmentStats_vector = "catchmentStats.shp"

    def fill_dem(self):
        """
        Step 1: Fill the DEM to remove depressions.
        This is a necessary step before calculating flow direction and flow accumulation.
        """
        self.wbt.fill_depressions(dem=self.dem_in, output=self.dem_filled)
    
    def d8_pointer(self, esri_pointer: bool = True):
        """
        Step 2: Calculate the D8 flow direction.
        This will create a raster that indicates the direction of flow for each cell.
        We can choose if we want to use the ESRI pointer
        """
        self.wbt.d8_pointer(dem=self.dem_filled, output=self.flow_dir, esri_pntr=self.esri_pointer)
    
    def flow_accumulation(self):
        """
        Step 3: Calculate flow accumulation.
        This will create a raster that indicates the number of cells that flow into each cell.
        """
        self.wbt.d8_flow_accumulation(
            i=self.flow_dir,
            output=self.flow_acc,
            pntr=True,
            esri_pntr=self.esri_pointer
        )

    def build_stream_grid(self, threshold_cells: float = 11111):
        """
        Step 4: Build the stream grid.
        This will create a raster that indicates the streams based on a flow accumulation threshold.
        The threshold is in number of cells.
        """
        # Get the cell size from the flow accumulation raster
        src = gdal.Open(str(self.output_dir / self.flow_acc))
        arr = src.GetRasterBand(1).ReadAsArray()
        grid = (arr >= threshold_cells).astype(np.int8)

        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(
            str(self.output_dir / self.stream_grid),
            src.RasterXSize,
            src.RasterYSize,
            1,
            gdal.GDT_Int32,
        )

        dst.SetGeoTransform(src.GetGeoTransform())
        dst.SetProjection(src.GetProjection())
        dst.GetRasterBand(1).WriteArray(grid)
        dst.FlushCache()
        dst = None
        src = None

    def stream_link_identify(self):
        """
        Step 5: Link the streams.
        This will identify the streams and assign a unique identifier to each stream segment.
        """
        self.wbt.stream_link_identifier(
            d8_pntr=self.flow_dir,
            streams=self.stream_grid,
            output=self.stream_link,
            esri_pntr=self.esri_pointer
        )

    def watershed_delineation(self):
        """
        Step 6: Delineate the watersheds.
        This will create a raster that indicates the watershed for each stream segment.
        """
        self.wbt.watershed(
            d8_pntr=self.flow_dir,
            pour_pts=self.stream_link,
            output=self.watershed_raster,
            esri_pntr=self.esri_pointer
        )

    def raster_to_vector(self):
        """
        Step 7: Convert the watershed raster to a vector shapefile.
        This will create a shapefile that contains the watershed polygons.
        """
        src_ds = gdal.Open(str(self.output_dir / self.watershed_raster))
        srcband = src_ds.GetRasterBand(1)

        drv = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(str(self.output_dir / self.watershed_vector)):
            drv.DeleteDataSource(str(self.output_dir / self.watershed_vector))
        out_ds = drv.CreateDataSource(str(self.output_dir / self.watershed_vector))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)

        out_layer = out_ds.CreateLayer("watershed", srs=srs, geom_type=ogr.wkbPolygon)
        new_field = ogr.FieldDefn("gridCode", ogr.OFTInteger)
        out_layer.CreateField(new_field)
        idx = out_layer.GetLayerDefn().GetFieldIndex("gridCode")

        gdal.Polygonize(srcband, srcband, out_layer, idx, [], callback=None)

        src_ds = srcband = out_layer = out_ds = None

    def dissolve_watersheds(self):
        """
        Step 8: Dissolve the watershed polygons based on the gridCode field.
        This will create a shapefile that contains the aggregated catchment polygons.
        """
        watersheds = gpd.read_file(self.output_dir / self.watershed_vector)
        dissolved = watersheds.dissolve(by="gridCode", as_index=False)
        dissolved.to_file(self.output_dir / self.catchment_vector)

    def zonal_stats(self):
        """
        Step 9: Calculate zonal statistics for each catchment.
        This will create a shapefile that contains the catchment polygons with additional statistics fields.
        For a flooding model, we might be interested in the maximum flow accumulation within each catchment.
        """
        stats = ["count", "max"]
        shp = str(self.output_dir / self.catchment_vector)
        gdf = gpd.read_file(shp)

        zs = rs.zonal_stats(
            vectors=gdf.geometry,
            raster = str(self.output_dir / self.flow_acc),
            stats=stats,
            geojson_out = False
        )

        gdf = gdf.join(pd.DataFrame(zs))
        gdf.to_file(self.output_dir / self.catchmentStats_vector)

    def run_pipeline(self, esri_pointer: bool = True, threshold_cells: float = 11111):
        """
        Run the entire watershed delineation pipeline.
        """
        print("Step 1: Filling DEM...")
        self.fill_dem()
        print("Step 2: Calculating Flow Direction...")
        self.d8_pointer(esri_pointer=self.esri_pointer)
        print("Step 3: Calculating Flow Accumulation...")
        self.flow_accumulation()
        print("Step 4: Building Stream Grid...")
        self.build_stream_grid(threshold_cells=threshold_cells)
        print("Step 5: Linking Streams...")
        self.stream_link_identify()
        print("Step 6: Delineating Watersheds...")
        self.watershed_delineation()
        print("Step 7: Converting Raster to Vector...")
        self.raster_to_vector()
        print("Step 8: Dissolving Watersheds...")
        self.dissolve_watersheds()
        print("Step 9: Calculating Zonal Statistics...")
        self.zonal_stats()
        print("Pipeline completed. Outputs are saved in:", self.output_dir)



def main(args: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Watershed Delineation Pipeline")
    parser.add_argument(
        "--input_dem",
        type=Path,
        required=True,
        help="Path to the input DEM file (GeoTIFF format).",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        required=True,
        help="Directory to save the output files.",
    )
    parser.add_argument(
        "--threshold_cells",
        type=float,
        default=11111,
        help="Flow accumulation threshold in number of cells to define streams. Default is 11111 cells (~1 sqkm for 10m cells).",
    )
    parsed_args = parser.parse_args(args)

    pipeline = WatershedPipeline(
        input_dem=parsed_args.input_dem, output_dir=parsed_args.output_dir
    )
    pipeline.run_pipeline(threshold_cells=parsed_args.threshold_cells)

if __name__ == "__main__":
    main()


    