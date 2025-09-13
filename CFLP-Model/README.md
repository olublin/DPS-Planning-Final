# CFLP School Siting Optimization Model

This object-oriented implementation of a **Capacitated Facility Location Problem (CFLP)** model uses linear optimization to determine the optimal placement of new high schools in Durham County. It minimizes the average travel distance for students while ensuring that each school operates between **70% and 100% of its capacity**.

The model uses spatial and demographic data to assign students from planning units to school facilities based on geodesic distances and capacity constraints.

---

## Project Goal

To identify optimal school locations and student assignments that:

- Minimize average geodesic distance from students to their assigned high school
- Ensure each school remains within 70%–105% of its capacity  
- Respect existing school locations and capacities
- Allow for different Student Growth Rate (SGR) scenarios
- Optionally include Durham School of Arts (DSA)

---

## Requirements

Install the required Python libraries with:

```bash
pip install pyscipopt geopandas geopy pandas numpy
```

**Additional Requirements:**
- A working **SCIP solver** (usually installed with `pyscipopt`)
- **High-performance computing environment recommended**: The model can take several hours to run depending on solver parameters and system performance. **We strongly recommend running on a computing cluster.**

---

## Input File Requirements

### 1. Planning Units GeoJSON (`pu_file`)

A GeoJSON file containing planning units with student data and geometries. **Required columns:**

- `pu_2324_84`: Unique Planning Unit ID (used as index)
- `basez`: Base student enrollment count  
- `student_gen`: Student generation count from SGR projections
- `Region`: Region classification
- `geometry`: Polygon geometry of the planning unit

**Format:** Must be a valid GeoJSON file, will be converted to EPSG:4326 projection

### 2. Schools GeoJSON (`schools_file`)

A GeoJSON file containing school locations as **point geometries**.

- `geometry`: Point geometry for each school location

---

## Model Assumptions

The model is currently built with **fixed capacities corresponding to Durham Public Schools (DPS) base high schools only.**

**Fixed School Capacities:**
- Planning Unit 45: 1,400 students
- Planning Unit 507: 1,510 students  
- Planning Unit 602: 1,340 students
- Planning Unit 566: 1,240 students
- Planning Unit 290: 1,335 students
- Planning Unit 584: 500 students (Durham School of Arts, if `--include-dsa` flag is used)

**Facility Limits:**
- Without DSA: Maximum 6 facilities (5 existing + 1 new)
- With DSA: Maximum 7 facilities (6 existing + 1 new)
- All existing schools must remain open

**Future Development:** We plan to implement functionality that allows users to input a school location file with capacity information, enabling the model to solve problems based on the schools and capacities specified in the input file rather than hardcoded DPS values.

---

## Usage

```bash
python CFLP.py <pu_file> <schools_file> <sgr_level> [--include-dsa]
```

**Parameters:**
- `pu_file`: Filename of planning units GeoJSON (must be in ../data/ directory)
- `schools_file`: Filename of schools GeoJSON (must be in ../data/ directory)  
- `sgr_level`: Student Growth Rate scenario (`none`, `half`, `full`)
  - `none`: 0% SGR (basez only)
  - `half`: 15% SGR (basez + 0.15 * student_gen)
  - `full`: 30% SGR (basez + 0.30 * student_gen)
- `--include-dsa`: Optional flag to include Durham School of Arts

**Example:**
```bash
python CFLP.py hs_full_geo.geojson dps_hs_locations.geojson half --include-dsa
```

---

## Runtime & Performance

⚠️ **Important:** The optimization can take several hours to complete. Runtime varies based on:
- Problem size (number of planning units)  
- System specifications
- Solver parameters

**We strongly recommend running on a computing cluster or high-performance computing environment.**

---

## Outputs

### 1. GeoJSON Assignment Map
`CFLP_[SGR]SGR.geojson`

Contains all planning units with an added `assignment` column indicating which facility each planning unit is assigned to.

### 2. JSON Solution Report  
`CFLP_[SGR]SGR.json`

Contains:
- Solution number
- List of opened facilities (planning unit IDs)
- Planning unit assignments per facility
- Student count per facility (base enrollment only)

**Example output structure:**
```json
{
  "solution_number": 1,
  "facilities": [45, 290, 507, 566, 602, 1234],
  "assignments": {
    "45": [101, 102, 103],
    "290": [201, 202]
  },
  "student_count": {
    "45": 1350,
    "290": 1280
  }
}
```

Output files can be loaded into GIS software such as **QGIS** to visualize school assignments and analyze the solution.
