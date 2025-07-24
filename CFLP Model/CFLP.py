import geopandas as gpd
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from pyscipopt import Model, quicksum, multidict
from pyscipopt import SCIP_PARAMEMPHASIS, SCIP_PARAMSETTING
import json

class CFLPModel:
    def __init__(self, pu_path, schools_path, sgr_level='none', include_dsa=False):
        self.pu_path = pu_path
        self.schools_path = schools_path
        self.sgr_level = self._parse_sgr_level(sgr_level)
        self.include_dsa = include_dsa
        self.existing_site_capacities = {
            45: 1400,
            507: 1510,
            602: 1340,
            566: 1240,
            290: 1335
        }
        if include_dsa:
            self.existing_site_capacities[584] = 500
        self.existing_sites = set(self.existing_site_capacities.keys())
        self.facility_cap = 7 if self.include_dsa else 6

    def _parse_sgr_level(self, level):
        return {'none': 0.0, 'half': 0.15, 'full': 0.3}.get(level.lower(), 0.0)

    def load_data(self):
        self.pu = gpd.read_file(f'../data/{self.pu_path}').set_index('pu_2324_84').to_crs('EPSG:4326')
        self.schools = gpd.read_file(f'../data/{self.schools_path}').to_crs('EPSG:4326')

    def preprocess(self):
        self.pu['basez+gen'] = self.pu['basez'] + self.sgr_level * self.pu['student_gen']
        self.I, self.d = multidict(self.pu['basez+gen'].to_dict())

        # Set planning unit capacities
        not_central = self.pu[self.pu['Region'] != 'Central']
        pu_dict = {idx: 1550 for idx in not_central.index}
        pu_dict.update(self.existing_site_capacities)
        self.J, self.M = multidict(pu_dict)

        # Centroids for geodesic distances
        self.centroids = {
            idx: (geom.y, geom.x) for idx, geom in self.pu.geometry.centroid.items()
        }
        self.c = {
            (i, j): geodesic(self.centroids[i], self.centroids[j]).miles
            for i in self.I for j in self.J
        }

    def build_model(self):
        model = Model("CFLP")

        x, y = {}, {}
        for j in self.J:
            y[j] = model.addVar(vtype="B", name=f"y({j})")
            for i in self.I:
                x[i, j] = model.addVar(vtype="C", name=f"x({i},{j})")

        for i in self.I:
            model.addCons(quicksum(x[i, j] for j in self.J) == self.d[i])

        for j in self.M:
            model.addCons(quicksum(x[i, j] for i in self.I) <= self.M[j] * y[j] * 1.05)
            model.addCons(quicksum(x[i, j] for i in self.I) >= self.M[j] * y[j] * 0.7)

        for i, j in x:
            model.addCons(x[i, j] <= self.d[i] * y[j])

        for j in self.existing_sites:
            model.addCons(y[j] == 1)

        model.addCons(quicksum(y[j] for j in self.J) <= 6)

        model.setObjective(
            quicksum(self.c[i, j] * x[i, j] for i in self.I for j in self.J),
            "minimize")

        model.setParam('limits/solutions', 1)
        model.setParam("presolving/maxrounds", 5)
        model.setEmphasis(SCIP_PARAMEMPHASIS.FEASIBILITY)
        model.setHeuristics(SCIP_PARAMSETTING.AGGRESSIVE)
        model.setParam("limits/gap", 0.01)

        self.model = model
        self.model.data = x, y

    def optimize(self):
        self.model.optimize()
        x, y = self.model.data
        sol = self.model.getBestSol()

        assignments = {}
        for (i, j) in x:
            if self.model.getSolVal(sol, x[i, j]) > 0.5:
                assignments.setdefault(j, []).append(i)

        student_counts = {
            j: sum(self.pu.loc[i, 'basez'] for i in i_list)
            for j, i_list in assignments.items()
        }

        self.solution = {
            'solution_number': 1,
            'facilities': list(assignments.keys()),
            'assignments': assignments,
            'student_count': student_counts
        }

    def export_results(self):
        pu_copy = self.pu.copy()
        pu_to_facility = {
            pu_id: facility
            for facility, pu_list in self.solution['assignments'].items()
            for pu_id in pu_list
        }
        pu_copy['assignment'] = pu_copy.index.map(pu_to_facility)
        sgr_label = f"{int(self.sgr_level * 100)}SGR"
        pu_copy.to_file(f"CFLP_{sgr_label}.geojson", driver="GeoJSON")

        with open(f"CFLP_{sgr_label}.json", "w") as f:
            json.dump(self.solution, f, indent=2)


def main():
    pu_file = input("Enter the filename of the planning units GeoJSON: ").strip()
    schools_file = input("Enter the filename of the schools GeoJSON: ").strip()
    sgr_level = input("Enter the SGR level to use (none, half, full): ").strip()

    model = CFLPModel(pu_file, schools_file, sgr_level)
    model.load_data()
    model.preprocess()
    model.build_model()
    model.optimize()
    model.export_results()

if __name__ == '__main__':
    main()