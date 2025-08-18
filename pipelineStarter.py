from pathlib import Path
from catchmentDelineation import WatershedPipeline

dem_path = Path("input/DEM.tif")
output_dir = Path("./output")
threshold_cells = 11111  # Example threshold for stream definition

pipeline = WatershedPipeline(input_dem=dem_path, output_dir=output_dir)
pipeline.run_pipeline(
    esri_pointer=True,  # Use ESRI pointer for flow direction
    threshold_cells=threshold_cells
)
