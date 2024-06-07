import geopandas as gpd
import osmnx as ox
from shapely.geometry import Polygon
import os
import pandas as pd

def generate_polygons(boundary_shp, output_dir, buffer_distance=50):
    boundary_gdf = gpd.read_file(boundary_shp)
    all_parking_lots = []
    all_walkways = []
    for index, row in boundary_gdf.iterrows():
        print(f"Processing polygon {index}...")
        boundary_polygon = row.geometry
        centroid = boundary_polygon.centroid
        utm_crs = boundary_gdf.crs
        boundary_polygon_gdf = gpd.GeoDataFrame(geometry=[boundary_polygon], crs=boundary_gdf.crs)
        projected_boundary = boundary_polygon_gdf.to_crs(utm_crs).geometry[0]
        buffered_boundary = projected_boundary.buffer(buffer_distance)
        wgs84_buffered_boundary = gpd.GeoDataFrame(geometry=[buffered_boundary], crs=utm_crs).to_crs("epsg:4326").geometry[0]

        print(f"  - Querying for parking lots...")
        try:
            parking_lots = ox.features_from_polygon(wgs84_buffered_boundary, tags={"amenity": "parking"})
            if not parking_lots.empty:
                parking_lots = parking_lots.to_crs(boundary_gdf.crs)
                print(f"  - Found {len(parking_lots)} parking lot features.")
        except ox._errors.InsufficientResponseError:
            print(f"  - Warning: No OSM parking lot data found for polygon {index}. Skipping.")
            parking_lots = gpd.GeoDataFrame(columns=['geometry', 'amenity', 'area_sqft'], crs=boundary_gdf.crs)
        except Exception as e:
            print(f"  - Error querying parking lots for polygon {index}: {e}")
            continue

        print(f"  - Querying for walkways...")
        try:
            walkways = ox.features_from_polygon(
                wgs84_buffered_boundary,
                tags={"highway": "footway", "area": "yes"}
            )
            if not walkways.empty:
                walkways = walkways.to_crs(boundary_gdf.crs)
                print(f"  - Found {len(walkways)} walkway features.")
        except ox._errors.InsufficientResponseError:
            print(f"  - Warning: No OSM walkway data found for polygon {index}. Skipping.")
            walkways = gpd.GeoDataFrame(columns=['geometry', 'highway', 'area_sqft'], crs=boundary_gdf.crs)
        except Exception as e:
            print(f"  - Error querying walkways for polygon {index}: {e}")
            continue

        print(f"  - Filtering and processing...")
        try:
            parking_lots = parking_lots[parking_lots.intersects(boundary_polygon)].copy()
            walkways = walkways[walkways.intersects(boundary_polygon)].copy()

            parking_lots["area_sqft"] = parking_lots.to_crs(utm_crs).area * 10.7639
            walkways["area_sqft"] = walkways.to_crs(utm_crs).area * 10.7639

            for col in parking_lots.columns:
                parking_lots[col] = parking_lots[col].apply(lambda x: ', '.join([str(i) for i in x]) if isinstance(x, list) else x)
            for col in walkways.columns:
                walkways[col] = walkways[col].apply(lambda x: ', '.join([str(i) for i in x]) if isinstance(x, list) else x)

            all_parking_lots.append(parking_lots)
            all_walkways.append(walkways)
        except Exception as e:
            print(f"  - Error processing features for polygon {index}: {e}")
            continue

    all_parking_lots = pd.concat(all_parking_lots, ignore_index=True)
    all_walkways = pd.concat(all_walkways, ignore_index=True)

    # Filter for Polygons before saving
    all_parking_lots = all_parking_lots[all_parking_lots.geometry.type == 'Polygon']

    all_parking_lots.to_file(os.path.join(output_dir, "parking_lots.shp"))
    all_walkways.to_file(os.path.join(output_dir, "walkways.shp"))
    print(f"Total parking lot area: {all_parking_lots['area_sqft'].sum():.2f} square feet")
    print(f"Total walkway area: {all_walkways['area_sqft'].sum():.2f} square feet")

boundary_shp = "PPM_Sites.shp"
output_dir = "."
generate_polygons(boundary_shp, output_dir)