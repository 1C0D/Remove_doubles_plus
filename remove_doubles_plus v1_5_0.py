import bpy
import bmesh
import math
import mathutils
import sys
from bpy.props import FloatProperty, BoolProperty, EnumProperty

bl_info = {
    "name": "remove doubles plus",
    "author": "1C0D",
    "version": (1, 5, 0),
    "blender": (2, 81, 0),
    "category": "Mesh"}

'''add move to cursor (offset)to menu?'''

def main(self, context):
    me = bpy.context.object.data
    bm = bmesh.from_edit_mesh(me)
    bm.verts.ensure_lookup_table()
    hist = bm.select_history
    history = hist[:]
    len_history = len(history)
    sel = [v for v in bm.verts if v.select]
    len_sel = len(sel)

    for item in hist:
        if not isinstance(item, bmesh.types.BMVert):
            self.report({'ERROR'}, "Select Vertices only")  # or BAD SELECTION?
            return {'CANCELLED'}

    if len_history == 0:
        self.report({'ERROR'}, "Select verts with Shift")
        return {'CANCELLED'}

    if len_sel != len_history:
        self.report({'ERROR'}, "Select verts with Shift")
        return {'CANCELLED'}

#--Sequences--#
    def deselect():
        for f in bm.edges:
            f.select = False
        for e in bm.edges:
            e.select = False
        for v in bm.verts:
            v.select = False
        bm.select_flush(False)

    def path(v1, v2):
        v1.select = True
        v2.select = True
        bpy.ops.mesh.shortest_path_select()
        path = [v for v in bm.verts if v.select]
        path_copy = path.copy()
        return path_copy

    def sorted_path(path_copy, v1, v2,):
        sorted_path = [v1]

        while len(path_copy) > 1:
            v = sorted_path[-1]
            for e in v.link_edges:
                if e.other_vert(v) in path_copy:
                    path_copy.remove(v)
                    sorted_path.append(e.other_vert(v))
        if v2 not in sorted_path:
            sorted_path.append(v2)

        return sorted_path

    if len_history == 4:
        if self.group != 'PAIRS':
            deselect()
            path_1 = path(history[0], history[1])
            sorted_path_1 = sorted_path(path_1, history[0], history[1])
            deselect()
            path_2 = path(history[2], history[3])
            sorted_path_2 = sorted_path(path_2, history[2], history[3])
            deselect()
            history = sorted_path_1+sorted_path_2
            len_history = len(history)
            bm.select_history.clear()
            for v in history:
                v.select = True
                bm.select_history.add(v)
        else:
            pass

#--Pairs--#
    if self.group == 'PAIRS':
        idx_last = len_history-1
        for i, v in enumerate(history):

            if self.target == 'LAST':
                if (i % 2) == 0 and i < idx_last:
                    v.co = v.co.lerp(history[i+1].co, self.distance)
            if self.target == 'FIRST':
                if (i % 2) == 1 and i <= idx_last:
                    v.co = v.co.lerp(history[i-1].co, self.distance)
            if self.target == 'MIDDLE':
                if (i % 2) == 0 and i < idx_last:
                    center = v.co.lerp(history[i+1].co, 0.5)
                    v.co = v.co.lerp(center, self.distance)
                if (i % 2) == 1 and i <= idx_last:
                    v.co = v.co.lerp(center, self.distance)

#--Rows--#
    if self.group == 'ROWS':
        half = len_history // 2

        if self.target == 'LAST':
            for i, v in enumerate(history):
                if i < half:
                    v.co = v.co.lerp(history[i+half].co, self.distance)
        if self.target == 'FIRST':
            for i, v in enumerate(history):
                if i >= half:
                    v.co = v.co.lerp(history[i-half].co, self.distance)

        if self.target == 'MIDDLE':
            for i, v in enumerate(history):
                if i < half:
                    center = v.co.lerp(history[i+half].co, 0.5)
                    history[i].co = history[i].co.lerp(center, self.distance)
                    history[i+half].co = history[i +
                                                 half].co.lerp(center, self.distance)

#--Cluster--#
    if self.group == 'CLUSTER':
        idx_last = len_history-1
        if self.target == 'FIRST':
            for i, v in enumerate(history):
                if i != 0:
                    v.co = v.co.lerp(history[0].co, self.distance)
        elif self.target == 'LAST':
            for i, v in enumerate(history):
                if i != idx_last:
                    v.co = v.co.lerp(history[idx_last].co, self.distance)
        elif self.target == "MIDDLE":
            center = mathutils.Vector((0.0, 0.0, 0.0))
            for i, v in enumerate(history):
                center = center + v.co
            center.x = center.x / len_history
            center.y = center.y / len_history
            center.z = center.z / len_history
            for i, v in enumerate(history):
                v.co = v.co.lerp(center, self.distance)

    if self.merge:
        if self.distance == 1:
            bmesh.ops.remove_doubles(bm, verts=history, dist=0.0001)

    bm.normal_update()
    bmesh.update_edit_mesh(me)

class Multi_OT_Lerp_Merge(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "multi.merge"
    bl_label = "Multi Merge"
    bl_options = {'REGISTER', 'UNDO'}

    group: EnumProperty(
        name="By",
        description="Vertex group",
        default="ROWS",
        items=(
                    ('ROWS', 'Rows(default)',
                     'Between the 2 rows (after selecting 4 extremities)'),
                    ('PAIRS', 'Pairs', 'Following selected Pairs'),
                    ('CLUSTER', 'Every', 'all selected to first,last,center'),
        ))
    target: EnumProperty(
        name="At",
        description="Cinch Target",
        default="MIDDLE",
        items=(
                    ('FIRST', 'First', 'Lerp or merge to First Vertex or Row'),
                    ('MIDDLE', 'Center', 'Lerp or merge to Center'),
                    ('LAST', 'Last', 'Lerp or merge to Last Vertex or Row'),
        ))
    distance: FloatProperty(
        name="Distance",
        description="Cinching Distance",
        min=0, max=1,
        default=1,
    )
    merge: BoolProperty(
        name="Merge",
        description="Merge",
        default=True,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        main(self, context)
        return {'FINISHED'}


class Remove_OT_doubles_plus(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "remove.doubles_plus"
    bl_label = "remove doubles plus"
    bl_description = 'remove doubles than loose edges and vertices then insidefaces'
    bl_options = {"UNDO", "REGISTER"}

    recalc_normals: BoolProperty(name="Recalculate normals", default=True)
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

        if self.recalc_normals:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

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
                verts = len(bm.verts[:])
                edges = len(bm.edges[:])
                faces = len(bm.faces[:])
                self.clean_geometry(bm)
                rmv_verts = verts-len(bm.verts)
                rmv_edges = edges-len(bm.edges)
                rmv_faces = faces-len(bm.faces)
                self.report(
                    {'WARNING'}, f"-[Vert:{rmv_verts}, Edg:{rmv_edges}, Fc:{rmv_faces}]")
                bmesh.update_edit_mesh(ob.data)

        return {'FINISHED'}


def doubles_plus(self, context):

    self.layout.operator("remove.doubles_plus")


def multi_merge(self, context):

    self.layout.operator("multi.merge")


def register():
    bpy.utils.register_class(Remove_OT_doubles_plus)
    bpy.utils.register_class(Multi_OT_Lerp_Merge)
    bpy.types.VIEW3D_MT_edit_mesh_merge.append(doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.prepend(multi_merge)


def unregister():
    bpy.utils.unregister_class(Remove_OT_doubles_plus)
    bpy.utils.unregister_class(Multi_OT_Lerp_Merge)
    bpy.types.VIEW3D_MT_edit_mesh_merge.remove(doubles_plus)
    bpy.types.VIEW3D_MT_edit_mesh_merge.remove(multi_merge)
