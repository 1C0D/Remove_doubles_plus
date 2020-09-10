from bpy.props import FloatProperty, BoolProperty
import bmesh
import bpy
import math

bl_info = {
    "name": "remove doubles plus",
    "author": "1C0D",
    "version": (1, 2, 1),
    "blender": (2, 81, 0),
    "category": "Mesh"}


class Remove_doubles_plus(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "remove.doubles_plus"
    bl_label = "remove doubles plus"
    bl_description = 'remove doubles than loose edges and vertices then insidefaces'
    bl_options = {"UNDO", "REGISTER"}

    rmv_doubles: BoolProperty(name="Remove doubles", default=True)
    rmv_doubles_threshold: FloatProperty(
        name="Threshold", default=0.0001, precision=4, step=0.004, min=0)
    zero_surface: BoolProperty(name="Overlapping edges", default=True)
    zero_surface_threshold: FloatProperty(
        name="Threshold", default=0.0001, precision=4, step=0.004, min=0)
    interior_faces: BoolProperty(
        name="int. faces(except selection)", default=True)
    redundant_verts: BoolProperty(name="Redundant verts", default=True)
    straightness: FloatProperty(
        name="Straightness", default=180, min=0, max=180)
    rmv_loose_verts: BoolProperty(name="loose verts", default=True)
    rmv_loose_edges: BoolProperty(name="loose edges", default=True)
    rmv_loose_faces: BoolProperty(name="loose faces", default=False)

    def clean_geometry(self, bm):

        if self.rmv_doubles:
            bmesh.ops.remove_doubles(
                bm, verts=bm.verts, dist=self.rmv_doubles_threshold)

        if self.zero_surface:
            bmesh.ops.dissolve_degenerate(
                bm, edges=bm.edges, dist=self.zero_surface_threshold)

        if self.rmv_loose_verts:
            loose_verts = [v for v in bm.verts if not v.link_edges]
            bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

        if self.rmv_loose_edges:
            loose_edges = [e for e in bm.edges if not e.link_faces]
            bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

        if self.rmv_loose_faces:
            mode = bm.select_mode
            loose_faces = [f for f in bm.faces if all(
                [not e.is_manifold and e.is_boundary for e in f.edges])]
            bmesh.ops.delete(bm, geom=loose_faces, context="FACES")
            bm.select_mode = mode

        if self.interior_faces:
            loose_faces = [e for e in bm.edges if len(e.link_faces) >= 3]
            faces_sel = [f for f in bm.faces if all(
                [e in loose_faces for e in f.edges]) and f.select == False]
            bmesh.ops.delete(bm, geom=faces_sel, context="FACES_ONLY")

        if self.redundant_verts:
            straight_edged = [v for v in bm.verts if len(v.link_edges) == 2 and
                              (self.straightness <
                               math.degrees((v.link_edges[0].other_vert(v).co-v.co)
                                            .angle(v.link_edges[1].other_vert(v).co - v.co)) < 181)]

            bmesh.ops.dissolve_verts(bm, verts=straight_edged)

    def execute(self, context):

        for ob in context.selected_objects:
            if ob.type == "MESH":
                bm = bmesh.from_edit_mesh(ob.data)
                bm.normal_update()
                bm.verts.ensure_lookup_table()
                self.clean_geometry(bm)
                bmesh.update_edit_mesh(ob.data)

        return {'FINISHED'}


def doubles_plus(self, context):

    self.layout.operator("remove.doubles_plus")

    return {'FINISHED'}


def register():
    bpy.utils.register_class(Remove_doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.append(doubles_plus)


def unregister():
    bpy.utils.unregister_class(Remove_doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.remove(doubles_plus)
