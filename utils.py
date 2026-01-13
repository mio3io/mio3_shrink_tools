import sys
import time
import bpy
import bmesh
from mathutils import Vector, kdtree
from collections import deque

DEBUG = bool("--python" in sys.argv)


class Mio3ShrinkToolsBase:
    _start_time = 0

    def start_time(self):
        if DEBUG:
            self._start_time = time.time()

    def print_time(self):
        if DEBUG:
            print("Time: {:.5f}".format(time.time() - self._start_time))
            pass


def find_islands(selected_verts, selected_edges) -> list:
    islands = []
    while selected_verts:
        v = selected_verts.pop()
        island = {v}
        stack = [v]
        while stack:
            v = stack.pop()
            for e in v.link_edges:
                if e in selected_edges:
                    ov = e.other_vert(v)
                    if ov not in island:
                        island.add(ov)
                        stack.append(ov)
                        selected_verts.remove(ov)
        islands.append(list(island))
    return islands


def find_x_mirror_verts(bm, selected_verts) -> set:
    kd = kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    mirror_verts = set()
    for v in selected_verts:
        mirror_co = v.co.copy()
        mirror_co.x = -mirror_co.x
        _, index, dist = kd.find(mirror_co)
        if dist < 0.0001:
            mirror_vert = bm.verts[index]
            if mirror_vert not in selected_verts:
                mirror_verts.add(mirror_vert)

    return mirror_verts


def find_x_mirror_vert_pairs(bm, selected_verts) -> dict:
    """X軸に対称な頂点のペアを見つける"""
    kd = kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    mirror_verts = {}
    for v in selected_verts:
        mirror_co = v.co.copy()
        mirror_co.x = -mirror_co.x
        _, index, dist = kd.find(mirror_co)
        if dist < 0.0001:
            mirror_vert = bm.verts[index]
            if mirror_vert not in selected_verts:
                mirror_verts[v] = mirror_vert

    return mirror_verts


def find_x_mirror_edges(bm, selected_edges) -> list:
    symm_edges = []

    kd = kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    threshold_sq = 0.0001**2
    for e in selected_edges:
        mirror_co1 = e.verts[0].co.copy()
        mirror_co2 = e.verts[1].co.copy()
        mirror_co1.x *= -1
        mirror_co2.x *= -1

        loc1, index1, _ = kd.find(mirror_co1)
        loc2, index2, _ = kd.find(mirror_co2)

        if ((mirror_co1 - loc1).length_squared < threshold_sq) and (
            (mirror_co2 - loc2).length_squared < threshold_sq
        ):
            v1 = bm.verts[index1]
            v2 = bm.verts[index2]

            for edge in v1.link_edges:
                if v2 in edge.verts and edge not in selected_edges:
                    symm_edges.append(edge)
                    break

    return symm_edges


def find_edge_loops_by_edges(selected_edges) -> list:
    """選択されたエッジからエッジループを見つける"""
    edge_loops = []
    vertex_to_edge = {}

    for edge in selected_edges:
        for vert in edge.verts:
            if vert not in vertex_to_edge:
                vertex_to_edge[vert] = []
            vertex_to_edge[vert].append(edge)

    unprocessed = set(selected_edges)
    while unprocessed:
        edge_loop = []
        current_edge = unprocessed.pop()
        edge_loop.append(current_edge)

        processed_verts = set()
        queue = set(current_edge.verts)
        processed_verts.update(current_edge.verts)
        while queue:
            vert = queue.pop()
            for edge in vertex_to_edge[vert]:
                if edge in unprocessed:
                    unprocessed.remove(edge)
                    edge_loop.append(edge)

                    new_verts = [v for v in edge.verts if v not in processed_verts]
                    queue.update(new_verts)
                    processed_verts.update(new_verts)

        edge_loops.append(edge_loop)
    return edge_loops


def find_bone_by_weight(obj, armature, selected_verts) -> object:
    max_weight = 0
    result_bone = None

    for vert in selected_verts:
        mesh_vert = obj.data.vertices[vert.index]
        for group in mesh_vert.groups:
            if group.group < len(obj.vertex_groups):
                weight = group.weight
                if weight > max_weight:
                    bone_name = obj.vertex_groups[group.group].name
                    bone = armature.data.bones.get(bone_name)
                    if bone and bone.use_deform and not bone.hide:
                        max_weight = weight
                        result_bone = bone
    return result_bone

