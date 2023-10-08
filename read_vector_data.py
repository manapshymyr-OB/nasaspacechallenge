import geopandas as gpd
import psycopg2 as pg
from sqlalchemy import create_engine
import pandas as pd
import json

# conn = pg.connect(
#         host="localhost",
#         database='postgres',
#         user="postgres",
#         password="postgres")
#
# print(conn)

engine = create_engine('postgresql://postgres:postgres@localhost:5432/{}'.format('postgres'))
sql = "select ST_AsGeoJSON(geom), gid FROM public.glf limit 1;"
# df = gpd.GeoDataFrame.from_postgis(sql, engine)
df = pd.read_sql(sql, engine)
print(type(df.iloc[0, 0]))
bbox = json.dumps(df.iloc[0, 0])
print(bbox)
