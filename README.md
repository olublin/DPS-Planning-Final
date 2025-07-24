# DPS-Planning-Final

![alt text](https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSm6QwtUnefiWRafxJEMVU0DHZuwVuumvxCsA&s)

By Emily Lewis-Farrell (@egl0404), Kevan Wang (@KevanWang05), Leah Wallihan (LtheWall00), Oliver Lublin (@olublin)

This repository contains the necessary scripts and datasets to filter residential developments for relevancy, generate student generation from filtered new developments in Durham County, and apply this to **CFLP linear optimization** and **Gravity** models for optimal boundary and site generation for new public school siting locations

All required input data for the complete workflow process is within the *data* folder in the repository

# Workflow

**Data**
-->
**Residential Filter**
-->
**CFLP Model** + **Gravity Model**

---

## Residential Filter

The **Residential Filter** script filters a developments geodataframe to strictly developments that generate enrollment for DPS. The geodataframe of all Durham County developments within the last 5 years can be accessed at the [Durham Open Data Portal](https://live-durhamnc.opendata.arcgis.com/datasets/c6fdd1f7e6a34bd8bfc78e87b5250f20_17/explore?location=36.050975%2C-78.857950%2C10.04).

A geodataframe containing the columns `basez` and `student_gen` is produced from this script, allowing student enrollment projections to be made at the **planning-unit level** by the following formula:

Enrollment Projection = basez + k * student_gen

---

## Acknowledgements

This project would not be possible without the guidance and work put in by our project lead, Vitaly Radsky, and our project manager, Cameron Moore.