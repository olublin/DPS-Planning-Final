#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 19 16:05:54 2025

@author: cameronmoore
"""

import pandas as pd
import geopandas as gpd
import os
import openrouteservice
import time
import folium
from itertools import chain
import matplotlib.pyplot as plt


# %%

class distanceMatrix:
    def __init__(self, pu_path, key):
        self.pu_path = pu_path
        self.key = key
        try:
            self.iso = self.client.isochrones(...)
        except Exception as e:
            print(f"Error computing isochrone: {e}")
            self.client = openrouteservice.Client(key = key)

    def load_data(self):
        self.pu = gpd.read_file(f'{os.getcwd()}/{self.pu_path}').to_crs('EPSG:4326')
        #self.pu['pu_2324_84'] = self.pu['pu_2324_84'] - 1

    def get_pu_centroids(self):
        self.pu['centroid'] = self.pu.geometry.centroid
        self.centroids = self.pu['centroid']

    def isochrone_branching(self, pu = 1, time = 600):      #isochrone branches for pu argument
        centroid = self.centroids.iloc[pu]
        coords = (centroid.x,centroid.y)
        self.iso = self.client.isochrones(
            locations = [coords],
            profile = 'driving-car',
            range = [time]
        )      

        self.iso_geo = gpd.GeoDataFrame.from_features(self.iso['features'], crs = 'EPSG:4326')['geometry']

    def distance_array(self, pu = 1, max_time = 1800, step = 60):
        N = len(self.centroids)
        self.times = [None] * N
        range1 = range(step, int(2*max_time/3) + step, step)               #loop every minute between 1 and 20 min.
        range2 = range(int(2*max_time/3) + step, max_time + step, step*2)  #loop every other minute from 21 to 30 min.
        range_all = chain(range1, range2)
        for t in range_all:                                   #branch isochrones by step
            self.isochrone_branching(pu = pu, time = t)
            isochrone = self.iso_geo.union_all()             #unary_union -> union_all?

            #get what centroids lay within isochrone
            overlap = self.pu[self.pu.intersects(isochrone)]
            indices = overlap.index.to_list()

            #enter new times into list
            for idx in indices:
                if self.times[idx] is None:
                    self.times[idx] = int(t/60)
            
            #break if all centroids have been reached
            if all(time is not None for time in self.times):
                break

            #sleep to avoid surpassing 40/minute quota
            time.sleep(1.5)

    def build(self, pu_lower = 0, pu_upper = 0):
        self.matrix_times = pd.DataFrame()
        for unit in range(pu_lower, pu_upper + 1):
            self.distance_array(pu = unit)                    #get distance array for individual pu
            col = self.times
            self.matrix_times[unit] = col

        self.matrix_times.to_csv('dist_matrix_81_170.csv')
 
    
# %%

matrix = distanceMatrix('pu_split_start_0.geojson', 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRmZGMwZDA3NDVhYzRkNzY5Y2UzN2Q1YTk3MmNlNWQzIiwiaCI6Im11cm11cjY0In0=')
matrix.load_data()
matrix.get_pu_centroids()
#matrix.isochrone_branching()
#matrix.distance_array()
matrix.build(pu_lower = 81, pu_upper = 170)





