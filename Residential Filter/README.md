# Residential Filter

This script **projects DPS enrollment** at the **planning unit level** as a combination of current students and students generated from residential developments. 
In order to do this, the script:

## A: Projects Student Generation by Filtering Developoments

### 1: Filters for residential developments 
This script filters all Durham developments over the last 5 years that contribute to DPS enrollment by using regular expressions and sorting for relevant development types.

### 2: Extracts the **quantity** and **type of units** for each development. 
The 5 unit types included in the script are:
    - `sf_detach`: Single Family Detatched homes
    - `sf_attach`: Single Family Attatched homes (such as townhomes)
    - `du_tri`: Duplexes and Triplexes
    - `mf_apt`: Multifamily Apartments
    - `condo`: Condos
The script maps the geodataframe of all developments to recognize these development types.

### 3: Calculates generated students by planning unit
Multiplies the quantity of developments with the corresponding **student generation rate**, matched by housing type and region of Durham, to project the number of students generated at a planning unit level.

## B: Combines Student Generation with Current Enrollment in a Geodataframe

1: Aggregates current elementary, middle, or high school enrollment by planning unit.
2: Adds student generation by planning unit as a column in the geodataframe.

### Input Files

**1: Durham Developments File**

**2: Student Generation Rates File**

**3: Durham Regions Shapefile**

**4: Current Enrollment/Marketshare File**


## Output

This script outputs a single file that contains the columns:
- `pu_2324_84`: Unique Planning Unit ID

- `basez`: Base enrollment count

- `student_gen`: Student generation count from SGR

- `geometry`: Polygon geometry of the planning unit

This file, as well as a file with current DPS schools, are the only two required files to run both the CFLP and gravity models. 
