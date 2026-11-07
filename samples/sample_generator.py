"""
Generates initial sample DXF and CAD files into the samples/ folder.
"""

import os
from cad_engine.document import CadDocument
from cad_engine.dxf_io import export_dxf, save_project
from samples.sample_floor_plan import create_sample_floor_plan
from samples.sample_mechanical import create_sample_mechanical_part


def generate_all_samples():
    out_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Architectural Floor Plan
    doc_plan = CadDocument()
    create_sample_floor_plan(doc_plan)
    dxf_plan_path = os.path.join(out_dir, "sample_floor_plan.dxf")
    cad_plan_path = os.path.join(out_dir, "sample_floor_plan.cad")
    export_dxf(doc_plan, dxf_plan_path)
    save_project(doc_plan, cad_plan_path)
    print(f"Generated: {dxf_plan_path}")

    # 2. Mechanical Spur Gear
    doc_mech = CadDocument()
    create_sample_mechanical_part(doc_mech)
    dxf_mech_path = os.path.join(out_dir, "sample_mechanical.dxf")
    cad_mech_path = os.path.join(out_dir, "sample_mechanical.cad")
    export_dxf(doc_mech, dxf_mech_path)
    save_project(doc_mech, cad_mech_path)
    print(f"Generated: {dxf_mech_path}")


if __name__ == "__main__":
    generate_all_samples()

