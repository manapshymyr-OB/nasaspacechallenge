import os
import time

import geopandas as gpd
import odc.stac
import planetary_computer
import pystac_client
import rich.table
import rioxarray
from rich.console import Console
from sqlalchemy import create_engine
os.environ["PROJ_LIB"] = 'C:\OSGeo4W\share\proj'
from typing import Dict, Any
from pystac.item import Item
from shapely.geometry import shape
from pyproj import CRS


gid = 'test'
def intersection_percent(item: Item, aoi: Dict[str, Any]) -> float:
    '''The percentage that the Item's geometry intersects the AOI. An Item that
    completely covers the AOI has a value of 100.
    '''
    geom_item = shape(item.geometry)
    geom_aoi = shape(aoi)

    intersected_geom = geom_aoi.intersection(geom_item)

    intersection_percent = (intersected_geom.area * 100) / geom_aoi.area

    return intersection_percent


def table_print(item):
    vi_item = item[0]
    t = rich.table.Table("Key", "Title")
    for key, asset in vi_item.assets.items():
        t.add_row(key, asset.title)
    console = Console()
    console.print(t)


# # create a connection to the database
# engine = create_engine('postgresql://postgres:postgres@localhost:5432/{}'.format('postgres'))
#
# sql = "select geom, gid FROM public.glf where gid = 476 limit 1;"
# df = gpd.GeoDataFrame.from_postgis(sql, engine)



s = {

        "coordinates": [
          [
            [
              80.21564649165578,
              50.485906542147745
            ],
            [
              80.23903336357284,
              50.473896338321964
            ],
            [
              80.28908947539253,
              50.456920194863386
            ],
            [
              80.33011907524497,
              50.481729426091846
            ],
            [
              80.33134996324037,
              50.51852755263252
            ],
            [
              80.36212216313021,
              50.57692804592236
            ],
            [
              80.34447943519308,
              50.58630709335648
            ],
            [
              80.31575871529685,
              50.57640693296244
            ],
            [
              80.28498651540713,
              50.57692804592236
            ],
            [
              80.25503490751544,
              50.59307968820141
            ],
            [
              80.24149513956377,
              50.58292043058606
            ],
            [
              80.25052165153096,
              50.56441974362343
            ],
            [
              80.2304171476029,
              50.550865335038
            ],
            [
              80.19020813974862,
              50.551647426101084
            ],
            [
              80.18036103578322,
              50.546693963579855
            ],
            [
              80.18692577175955,
              50.53417763483736
            ],
            [
              80.21564649165578,
              50.485906542147745
            ]
          ]
        ],
        "type": "Polygon"
      }


# create geodataframe from the geojson
geom = [shape(i) for i in [s]]
df = gpd.GeoDataFrame({'geometry':geom})
df.set_crs(epsg=4326, inplace=True)
catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)


search = catalog.search(
        collections=["modis-13Q1-061", 'modis-11A2-061' ],
        datetime=['2017', None],
        intersects=s,
    )
    # items[name] = search.get_all_items()[0]
items = search.item_collection()

# land surface temperature
lst = []
# vegetation index
vi = []
# select only summer season
for item in items:
    julian_date = int(item.id.split(".")[1][-3:])
    if 151 < julian_date <= 244:
        print(item.id)
        if '11A2' in item.id:
                lst.append(item)
        else:
                vi.append(item)


# print([f"{intersection_percent(item, s):.2f}" for item in search.items()])


# table_print(vi)
print('Print assets')
table_print(lst)
table_print(vi)


# process LST
data = odc.stac.load(
    items=lst,
    crs="EPSG:3857",
    bands="LST_Day_1km",
    resolution=1000,
  geopolygon=df.geometry,
)

# lst scaling
data = data['LST_Day_1km'] * 0.02 - 273.15
# get crs of the raster
# remove 0 values
data = data.where(data > 0)
# get max and min values
lst_max = data.max(skipna=True)
lst_min = data.min(skipna=True)
data_lst = 100 * (lst_max - data) / (lst_max - lst_min)
data = 100 * (lst_max - data) / (lst_max - lst_min)

# save to netcdf
data.to_netcdf(f'{gid}_tci.nc')

# raster = rioxarray.open_rasterio(lst[0].assets["LST_Day_1km"].href)
# raster_crs = raster.rio.crs
# reproject geodataframe to raster crs
df = df.to_crs(3857)
# r = data.mean(dim='time').rio.write_crs(raster_crs, inplace=True)
# r = .rio.write_crs(raster_crs, inplace=True)
raster_clip_box_lst = data.mean(dim='time').rio.clip(df['geometry'])
raster_clip_box_lst.rio.to_raster(f"{gid}_tci_mean.tif")


# process VI

data = odc.stac.load(
    vi,
    crs="EPSG:3857",
    bands="250m_16_days_EVI",
    resolution=250,
    geopolygon=df.geometry,
)

# EVI
raster = vi[0].assets["250m_16_days_EVI"].extra_fields["raster:bands"]
data = data["250m_16_days_EVI"] * raster[0]["scale"]

# remove 0 values
data = data.where(data > 0)
# get max and min values
evi_max = data.max(skipna=True)
evi_min = data.min(skipna=True)
data = ((data - evi_min) / (evi_max - evi_min)) * 100

data.to_netcdf(f'{gid}_vci.nc')

raster_clip_box = data.mean(dim='time').rio.clip(df['geometry'])
raster_clip_box.rio.to_raster(f"{gid}_vci_mean.tif")

# from rasterio.enums import Resampling
#
# xds_upsampled = data_lst.rio.reproject(
#     data_lst.rio.crs,
#     shape=(raster_clip_box.rio.height, raster_clip_box.rio.width),
#     resampling=Resampling.nearest,
# )
#
# xds_upsampled = xds_upsampled.mean(dim='time').rio.clip(df['geometry'])
# xds_upsampled.rio.to_raster(f"{gid}_vci_meansdsada.tif")
#
# vhi = xds_upsampled * 0.5 + raster_clip_box * 0.5
# vhi.rio.to_raster(f"{gid}_vhi.tif")