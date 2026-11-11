"""Synthetic source material topology diagnostics; no original Golf assets."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.surface_footprint_audit import (
    _region, audit_material_footprints)
from wii_ai_golf.inspector.source_connectivity_probe import probe_connectivity
from wii_ai_golf.inspector.scene_alignment_audit import audit_surface_registration


class SourceFootprintAuditTests(unittest.TestCase):
    def test_welds_edges_not_source_vertex_indices(self):
        # Two source triangles share a geometric edge despite deliberately
        # duplicated OBJ vertex records (as in KCL 3-vertices-per-face export).
        pts = (
            (0., 0., 0.), (2., 0., 0.), (0., 0., 2.),
            (2., 0., 0.), (2., 0., 2.), (0., 0., 2.),
        )
        r = _region(pts, ((0,1,2), (3,4,5)), diagonal=4.)
        self.assertEqual(r["source_edge_connected_component_count"], 1)
        self.assertEqual(r["component_count_over_1pct_area"], 1)
        self.assertAlmostEqual(r["largest_component_area_fraction"], 1.)

    def test_distant_source_material_patches_are_not_collapsed_to_one_landmark(self):
        pts = (
            (0., 0., 0.), (2., 0., 0.), (0., 0., 2.),
            (2., 0., 0.), (2., 0., 2.), (0., 0., 2.),
            (200., 0., 200.), (202., 0., 200.), (200., 0., 202.),
        )
        r = _region(pts, ((0,1,2), (3,4,5), (6,7,8)),
                    diagonal=300.)
        self.assertEqual(r["source_edge_connected_component_count"], 2)
        self.assertEqual(r["component_count_over_1pct_area"], 2)
        self.assertEqual(r["top_three_component_triangle_counts"], [2, 1])
        self.assertAlmostEqual(r["largest_component_area_fraction"], 2/3,
                               places=5)
        self.assertGreater(r["component_centroid_dispersion_over_source_diagonal"],
                           0.25)
        self.assertFalse(r["native_topology_or_alignment_proven"])
        # No source original XYZ leak to console output.
        self.assertNotIn("202.", json.dumps(r))

    def test_cross_source_categories_keep_dae_and_kcl_counts_separate(self):
        kverts = ((0., 0., 0.), (10., 0., 0.), (0., 0., 10.),
                  (50., 0., 50.), (60., 0., 50.), (50., 0., 60.))
        kcl = SimpleNamespace(vertices=kverts, faces=((0,1,2),(3,4,5)),
                              face_materials=(6, 6))
        vverts = ((0., 0., 0.), (10., 0., 0.), (0., 0., 10.),
                  (50., 0., 50.), (60., 0., 50.), (50., 0., 60.),
                  (20., 0., 20.), (30., 0., 20.), (20., 0., 30.))
        visual = SimpleNamespace(
            vertices=vverts,
            faces=(SimpleNamespace(vertices=(0,1,2), material="M_Green"),
                   SimpleNamespace(vertices=(3,4,5), material="M_Green"),
                   SimpleNamespace(vertices=(6,7,8), material="M_Fairway")),
        )
        r = audit_material_footprints(kcl, visual)
        self.assertEqual(r["status"], "SOURCE_LOCAL_COMPONENT_INVENTORY_ONLY")
        self.assertEqual(r["categories"]["green"]["kcl"]
                         ["source_edge_connected_component_count"], 2)
        self.assertEqual(r["categories"]["green"]["dae"]
                         ["source_edge_connected_component_count"], 2)
        self.assertEqual(r["categories"]["fairway"]["kcl"]["status"],
                         "NO_SOURCE_FACES")
        self.assertEqual(r["categories"]["fairway"]["dae"]
                         ["source_triangle_count"], 1)
        self.assertFalse(r["same_hole_or_same_source_extent_verified"])
        self.assertFalse(r["source_visual_registration_verified"])

    def test_full_edge_recovered_from_duplicate_per_face_source_vertices(self):
        verts = ((0., 0., 0.), (2., 0., 0.), (0., 0., 2.),
                 (2., 0., 0.), (2., 0., 2.), (0., 0., 2.))
        data = probe_connectivity(verts, ((0,1,2),(3,4,5)), 4.)
        self.assertEqual(data["status"],
                         "SOURCE_LOCAL_CONNECTIVITY_SENSITIVITY_ONLY")
        self.assertTrue(data["one_distinct_source_vertex_index_per_triangle_corner"])
        exact = data["trial_tolerances_relative_to_each_source_mesh"][0]
        self.assertEqual(exact["shared_full_edge_occurrences"], 1)
        self.assertEqual(exact["edge_connected_component_count"], 1)
        self.assertEqual(exact["vertex_touch_component_count"], 1)
        self.assertFalse(data["native_adjacency_verified"])
        self.assertFalse(data["same_original_game_hole_verified"])

    def test_relative_weld_tolerance_distinguishes_near_miss_from_exact_edge(self):
        verts = ((0., 0., 0.), (2., 0., 0.), (0., 0., 2.),
                 (2.00012, 0., 0.), (2., 0., 2.), (0., 0., 2.00012))
        data = probe_connectivity(verts, ((0,1,2),(3,4,5)), 4.)
        results = data["trial_tolerances_relative_to_each_source_mesh"]
        self.assertEqual([a["source_relative_endpoint_tolerance"] for a in results],
                         [0., 1e-8, 1e-6, 1e-4])
        self.assertEqual(results[0]["edge_connected_component_count"], 2)
        self.assertEqual(results[1]["edge_connected_component_count"], 2)
        self.assertEqual(results[2]["edge_connected_component_count"], 2)
        self.assertEqual(results[3]["edge_connected_component_count"], 1)
        self.assertNotIn("2.00012", json.dumps(data))

    def test_original_material_triangles_do_not_implicitly_share_indices(self):
        v = ((0., 0., 0.), (2., 0., 0.), (0., 0., 2.),
             (2., 0., 0.), (2., 0., 2.), (0., 0., 2.))
        kcl = SimpleNamespace(vertices=v, faces=((0,1,2),(3,4,5)),
                              face_materials=(6,1))
        visual = SimpleNamespace(
            vertices=v,
            faces=(SimpleNamespace(vertices=(0,1,2), material="M_Green"),
                   SimpleNamespace(vertices=(3,4,5), material="M_Fairway")))
        data = audit_material_footprints(kcl, visual)
        self.assertEqual(data["whole_mesh_connectivity"]["kcl"]
                         ["trial_tolerances_relative_to_each_source_mesh"][0]
                         ["edge_connected_component_count"], 1)
        self.assertEqual(data["categories"]["green"]
                         ["source_triangle_contact_sensitivity"]["kcl"]
                         ["trial_tolerances_relative_to_each_source_mesh"][0]
                         ["edge_connected_component_count"], 1)
        self.assertEqual(data["categories"]["fairway"]
                         ["source_triangle_contact_sensitivity"]["kcl"]
                         ["source_triangle_count"], 1)
        self.assertTrue(data["whole_mesh_connectivity"]["kcl"]
                        ["one_distinct_source_vertex_index_per_triangle_corner"])
        self.assertFalse(data["whole_mesh_connectivity"]["kcl"]
                         ["native_adjacency_verified"])

    def test_unbounded_probe_abstains_not_guesses(self):
        self.assertEqual(
            probe_connectivity(((0.,0.,0.),), ((0,1,2),), 2.)["status"],
            "ABSTAIN_INVALID_SOURCE_INDEX")
        self.assertEqual(
            probe_connectivity(((0.,0.,0.),), ((0,0,0),), 0.)["status"],
            "ABSTAIN_SOURCE_GEOMETRY_BOUND")

    def test_missing_materials_abstain_and_do_not_produce_pseudolandmarks(self):
        r = _region(((0.,0.,0.),), (), diagonal=1.)
        self.assertEqual(r["status"], "NO_SOURCE_FACES")
        self.assertNotIn("component_centroid_dispersion_over_source_diagonal", r)

    def test_original_alignment_report_retains_no_training_or_world_claim(self):
        from test_p0_inspector_unified_source_view import scene
        visual, terrain = scene()
        r = audit_surface_registration(terrain, visual)
        self.assertEqual(r["source_material_footprints"]["categories"]
                         ["green"]["kcl"]["source_triangle_count"], 1)
        self.assertEqual(r["source_material_footprints"]["categories"]
                         ["green"]["dae"]["source_triangle_count"], 1)
        self.assertFalse(r["source_geometry_identity_proven"])
        self.assertFalse(r["native_game_world_transform_proven"])
        self.assertFalse(r["source_material_footprints"]
                         ["source_visual_registration_verified"])


if __name__ == "__main__":
    unittest.main()
