# CFLP School Siting Optimization Model

This script implements a **Capacitated Facility Location Problem (CFLP)** model using linear optimization to determine the optimal placement of a new high school in Durham County. It minimizes the average travel distance for students while ensuring that each school operates between **70% and 100% of its capacity**.

The model uses spatial and demographic data to assign students from planning units to school facilities based on geodesic distances and capacity constraints.

---

## Project Goal

To identify optimal school locations and student assignments that:

- Minimize average geodesic distance from students to their assigned high school.
- Ensure each school remains within 70%–100% of its capacity.
- Limit the total number of open facilities to six, with five fixed (currently existing schools) and one allowed to be added.

---

## Requirements

Install the required Python libraries with:

```bash
pip install pyscipopt geopandas geopy
```

---

## Additional Requirements

You will also need:

- A working **SCIP solver** (used by the PySCIPOpt backend).
- A system capable of running the model for several hours. Depending on solver parameters and your system’s performance, **runtime may range from 5 to 15 hours**.

---

## Input Files

### 1. Planning Units GeoData

A GeoJSON file containing all planning units with student data and geometries. This file should include the following columns:

- `pu_2324_84`: Unique Planning Unit ID
- `basez`: Base enrollment count
- `student_gen`: Student generation count
- `geometry`: Polygon geometry of the planning unit

> **You can generate this input using the script:**  
> `DPS-Planning-Final/Residential Filter/sgr_htype_region.py`

---

### 2. High School Locations

A GeoJSON file containing the locations of all high school sites, represented as **point geometries**.

- Must be in EPSG:4326 projection to match the planning units

---

## Running the Script

Once your inputs are ready and dependencies installed, run:

```bash
python CFLP_model.py
```

## Runtime

The model may take several hours to complete depending on your system specifications and solver parameters.

Log output will be saved to: CFLP_halfSGR_output_v4.log

You may modify the log filename in the script to reflect different SGR scenarios or testing versions.

---

## Outputs

### 1. JSON Summary Report

CFLP_[percent]SGR.json

**Contents:**
- List of feasible solutions
- Opened facilities for each solution
- Planning unit assignments per facility
- Student count per facility (based on base enrollment and SGR factor)

---

### 2. GeoJSON Assignment Maps

CFLP_[percent]SGR_sol[solution_number].geojson

- One file per reported solution (e.g., 5 solutions → 5 GeoJSON files)
- Each file contains:
  - All planning units and their geometries
  - A new `assignment` column indicating the ID of the assigned school facility

These can be loaded into GIS software such as **QGIS** to visualize how planning units are assigned to school sites.
