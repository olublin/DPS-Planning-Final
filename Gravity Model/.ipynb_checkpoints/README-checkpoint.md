# Heuristic Gravity Siting Model

This **self-designed model for school siting** draws boundaries using an iterative process which initially assigns each planning unit to its closest school and proceeds to expand or contract boundaries until all schools are within the capacity range designated by the user.

---

## Project Goal
To draw boundaries that stray as little from a **Voronoi Map** as possible while keeping all schools in designated capacity ranges. 

### Framework
This model performs boundary assignment for a set of schools:

- Takes an input of any combination of DPS schools (i.e. all current base high schools) as sites, plus one new high school
- Takes the respective capacities of said schools.
- Initially calculates the distance from each planning unit to every school in the set, and assigns each planning unit to its nearest school by geodesic distance.
- Assigns an "adjust" factor to each school (+100 if the school is over the upper capacity bound, and -100 if under the lower capacity bound).
- Adds the "adjust" factor to all distances for a given school (for example, if Riverside High School has an adjust factor of -400, all planning units' calculated distance to Riverside High School will be decreased by 400, allowing Riverside to pull in more students.)
- Repeats until either all schools are in the assigned capacity range or 200 trials are complete, in which case the model returns no solution.

After completing boundary assignment, this model:
- Scores boundaries based on average distance traveled by students to their school.

**Note: The script projects the geodataframes to EPSG:3857, a metric coordinate reference system, and an adjustment factor of 100 indicates an adjustment of 100 meters.**

---

## Requirements

Install the required library for geospatial calculations, **Geopandas**, with:

```bash
pip install geopandas
```

---

## Input Files

### 1. Planning Units GeoData

A GeoJSON file containing all planning units with student data and geometries. This file should include the following columns:

- `pu_2324_84`: Unique Planning Unit ID
- `basez`: Base enrollment count
- `student_gen`: Student generation count from SGR
- `geometry`: Polygon geometry of the planning unit

> **You can generate this input using the script:**  
> `DPS-Planning-Final/Residential Filter/sgr_htype_region.py`

---

### 2. School Locations

A GeoJSON file containing the locations of all Durham school sites, represented as **point geometries**. 


---

## Running the Script

Once your inputs are ready and dependencies installed, run:

```bash
python heuristic_add.py
```

---

## Outputs

If the model succeeds at assigning all students and keeping schools under the capacity range, it will return: 

### 1: Planning Unit Assignment Dataframe:
school_geo.geojson

**Contains input dataframe of student counts by planning unit, as well as school assigned by model for each planning unit.**

### 2:. Student Counts Dataframe

counts.json

**Contains number of students assigned to each school, capacity of each school, and percent of capacity filled by model.**

### 3. GeoJSON Assignment Maps

assignment_map.png

**Map of school boundaries assigned by model.**

If the model cannot successfully assign boundaries for all schools within the capacity range in 200 attempts, it will still return **1** and **2** with the assignments and student counts after the 200th attempt.


