import geopandas as gpd
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from pyscipopt import Model, quicksum, multidict
from pyscipopt import SCIP_PARAMEMPHASIS, SCIP_PARAMSETTING
import json
import argparse
import sys

class CFLPModel:
    def __init__(self, pu_path, schools_cap_path, sgr_level='none', new_site=False):
        self.pu_path = pu_path
        self.schools_cap_path = schools_cap_path
        self.school_type = self.extract_school_type(schools_cap_path)
        self.sgr_level = self.parse_sgr_level(sgr_level)
        self.new_site = new_site
        self.option = self.extract_option(schools_cap_path)

    def parse_sgr_level(self, level):
        sgr_mappings = {
            'ES': {'none': 0.0, 'half': 0.25, 'full': 0.5},
            'MS': {'none': 0.0, 'half': 0.1, 'full': 0.2},
            'HS': {'none': 0.0, 'half': 0.15, 'full': 0.3}
        }
        return sgr_mappings.get(self.school_type, {}).get(level.lower(), 0.0)

    def extract_school_type(self, filename):
        """Extract school type (ES, MS, HS) from filename."""
        filename_upper = filename.upper()
        if 'ES' in filename_upper:
            return 'ES'
        elif 'MS' in filename_upper:
            return 'MS'
        elif 'HS' in filename_upper:
            return 'HS'
        return 'Unknown'
    
    
    def extract_option(self, filename):
        """Extract option type (option1, option2, option3) from filename."""
        filename_lower = filename.lower()
        if 'option1' in filename_lower:
            return 'option1'
        elif 'option2' in filename_lower:
            return 'option2'
        elif 'option3' in filename_lower:
            return 'option3'
        return 'Unknown'

    def load_data(self):
        self.pu = gpd.read_file(f'data/{self.pu_path}').set_index('pu_2324_84').to_crs('EPSG:4326')

        # load school capacities from JSON
        with open(f'data/{self.schools_cap_path}') as f:
            school_config = json.load(f)

        self.existing_site_capacities = {
            school['planning_unit']: school['capacity']
            for school in school_config['schools']
        }
        self.existing_sites = set(self.existing_site_capacities.keys())

        # use --new-site flag
        self.facility_cap = len(self.existing_sites) + (1 if self.new_site else 0)

    def preprocess(self):
        # Select the appropriate basez column based on school type
        basez_column = f'basez_{self.school_type.lower()}'
        self.pu['basez+gen'] = self.pu[basez_column] + self.sgr_level * self.pu['master_proj_23']
        self.I, self.d = multidict(self.pu['basez+gen'].to_dict())

        # Set planning unit capacities
        not_central = self.pu[self.pu['Region'] != 'Central']
        pu_dict = {idx: 1530 for idx in not_central.index}
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
            model.addCons(quicksum(x[i, j] for i in self.I) <= self.M[j] * y[j] * 1.00)
            model.addCons(quicksum(x[i, j] for i in self.I) >= self.M[j] * y[j] * 0.7)

        for i, j in x:
            model.addCons(x[i, j] <= self.d[i] * y[j])

        for j in self.existing_sites:
            model.addCons(y[j] == 1)

        model.addCons(quicksum(y[j] for j in self.J) <= self.facility_cap)

        model.setObjective(
            quicksum(self.c[i, j] * x[i, j] for i in self.I for j in self.J),
            "minimize")

        model.setParam('limits/solutions', 5)
        model.setParam("presolving/maxrounds", 10)
        model.setEmphasis(SCIP_PARAMEMPHASIS.OPTIMALITY)
        model.setHeuristics(SCIP_PARAMSETTING.DEFAULT)
        model.setParam("limits/gap", 0.01)

        self.model = model
        self.model.data = x, y

    def optimize(self):
        self.model.optimize()
        x, y = self.model.data

        # Collect all solutions
        sols = self.model.getSols()
        self.solutions = []

        for sol_idx, sol in enumerate(sols, start=1):
            assignments = {}
            for (i, j) in x:
                if self.model.getSolVal(sol, x[i, j]) > 0.5:
                    assignments.setdefault(j, []).append(i)

            basez_column = f'basez_{self.school_type.lower()}'
            student_counts = {
                j: sum(self.pu.loc[i, basez_column] for i in i_list)
                for j, i_list in assignments.items()
            }

            self.solutions.append({
                'solution_number': sol_idx,
                'facilities': list(assignments.keys()),
                'assignments': assignments,
                'student_count': student_counts
            })

    def export_results(self):
        """Export all solutions with labeled file naming."""
        sgr_label = f"{int(self.sgr_level * 100)}SGR"
        newsite_label = "newsite" if self.new_site else "noNewSite"

        for solution in self.solutions:
            pu_copy = self.pu.copy()
            pu_to_facility = {
                pu_id: facility
                for facility, pu_list in solution['assignments'].items()
                for pu_id in pu_list
            }
            pu_copy['assignment'] = pu_copy.index.map(pu_to_facility)

            # Enhanced filename: CFLP_ES_0SGR_newsite_sol1
            filename_base = f"CFLP_{self.school_type}_{sgr_label}_{newsite_label}_{self.option}_sol{solution['solution_number']}"

            # Export GeoJSON
            pu_copy.to_file(f"{filename_base}.geojson", driver="GeoJSON")

            # Export JSON
            with open(f"{filename_base}.json", "w") as f:
                json.dump(solution, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Durham School Planning CFLP Model')
    parser.add_argument('pu_file', help='Filename of the planning units GeoJSON')
    parser.add_argument('schools_cap_file', help='Filename of the schools capacity JSON')
    parser.add_argument('sgr_level', choices=['none', 'half', 'full'],
                        help='SGR level to use (none, half, full)')
    parser.add_argument('--new-site', action='store_true', default=False,
                        help='Allow model to select one additional facility site beyond existing schools (default: False)')

    args = parser.parse_args()

    print(f"Starting CFLP optimization with:")
    print(f"Planning Units: {args.pu_file}")
    print(f"Schools Capacity: {args.schools_cap_file}")
    print(f"SGR Level: {args.sgr_level}")
    print(f"Allow New Site: {args.new_site}")
    print()

    model = CFLPModel(args.pu_file, args.schools_cap_file, args.sgr_level, args.new_site)
    model.load_data()
    model.preprocess()
    model.build_model()

    model.optimize()
    model.export_results()

    sgr_label = f"{int(model.sgr_level * 100)}SGR"
    newsite_label = "newsite" if model.new_site else "noNewSite"
    print(f"\nOptimization complete!")
    print(f"Found {len(model.solutions)} solution(s)")
    print(f"Results saved with pattern: CFLP_{model.school_type}_{sgr_label}_{newsite_label}_sol[N].geojson and .json")

if __name__ == '__main__':
    main()