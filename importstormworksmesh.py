import struct
from typing import List, Tuple, Set, Any

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
from bpy_types import Operator

from .submesh import Submesh
from .vertex import Vertex


class ImportStormworksMesh(Operator, ImportHelper):
    """Import Stormworks Mesh"""

    bl_idname = "stormworks_mesh_importer.mesh_data"
    bl_label = "Import Mesh"

    filename_ext = ".mesh"

    filter_glob: StringProperty(
        default="*.mesh",
        options={"HIDDEN"},
        maxlen=255,
    )

    @staticmethod
    def _get(bytestring: bytes, structure: str) -> Tuple[bytes, Tuple[Any]]:
        size = struct.calcsize(structure)

        a, bytestring = bytestring[:size], bytestring[size:]

        return bytestring, struct.unpack(structure, a)

    @staticmethod
    def _skip(bytestring: bytes, size: int) -> bytes:
        return bytestring[size:]

    @staticmethod
    def read_mesh(filepath: str) -> Tuple[List[Vertex], List[Tuple[int, int, int]], List[Submesh]]:
        with open(filepath, "rb") as file:
            bytestring = file.read()

        assert bytestring.startswith(b"mesh\x07\x00\x01\x00") and bytestring.endswith(b"\x00\x00")

        bytestring = ImportStormworksMesh._skip(bytestring, 8)
        bytestring, (vertex_count,) = ImportStormworksMesh._get(bytestring, "H")
        bytestring = ImportStormworksMesh._skip(bytestring, 4)

        vertices = []

        for i in range(vertex_count):
            bytestring, position = ImportStormworksMesh._get(bytestring, "fff")

            bytestring, colour = ImportStormworksMesh._get(bytestring, "BBBB")

            bytestring, normal = ImportStormworksMesh._get(bytestring, "fff")

            vertex = Vertex(*position, *colour, *normal)
            vertices.append(vertex)

        bytestring, (triangle_count,) = ImportStormworksMesh._get(bytestring, "I")
        triangle_count = triangle_count // 3

        faces = []

        for i in range(triangle_count):
            bytestring, points = ImportStormworksMesh._get(bytestring, "HHH")

            faces.append(points)

        bytestring, (submesh_count,) = ImportStormworksMesh._get(bytestring, "H")

        submeshes = []

        for i in range(submesh_count):
            bytestring, (vertexStartIndex, vertexCount) = ImportStormworksMesh._get(bytestring, "II")
            endIndex = vertexStartIndex + vertexCount

            bytestring = ImportStormworksMesh._skip(bytestring, 2)

            bytestring, (shader,) = ImportStormworksMesh._get(bytestring, "H")

            bytestring, culling_min = ImportStormworksMesh._get(bytestring, "fff")

            bytestring, culling_max = ImportStormworksMesh._get(bytestring, "fff")

            ImportStormworksMesh._skip(bytestring, 19)

            submesh = Submesh((vertexStartIndex, endIndex), shader)
            submeshes.append(submesh)

        ImportStormworksMesh._skip(bytestring, 2)

        return vertices, faces, submeshes

    @staticmethod
    def add_mesh(name, vertices: List[Vertex], faces: List[Tuple[int, int, int]],
                 submeshes: List[Submesh] = None) -> None:

        if submeshes is None:
            submeshes = [Submesh((0, len(vertices)), 0)]

        for submesh in submeshes:
            start, end = submesh.vertices
            vertices_local = vertices[start:end]

            faces_local = []

            for face in faces:
                for i in range(3):
                    if start <= face[i] < end:
                        faces_local.append(face)
                        break

            name_formatted = f"{name}_{submesh.shader}"

            root_mesh = bpy.data.meshes.new(name_formatted)

            vertices_as_tuple_list = list(map(lambda a: (a.x, a.z, a.y), vertices_local))

            root_mesh.from_pydata(vertices_as_tuple_list, [], faces_local)

            normals = [None] * len(root_mesh.vertices)
            for loop in root_mesh.loops:
                vertex = vertices_local[loop.vertex_index]
                normals[loop.vertex_index] = (vertex.nx, vertex.nz, vertex.ny)

            root_mesh.normals_split_custom_set_from_vertices(normals)
            root_mesh.use_auto_smooth = True

            root_mesh.update()

            colour_layer = root_mesh.vertex_colors.new(name="Col")

            for poly in root_mesh.polygons:
                for loop_index in poly.loop_indices:
                    vertex_index = root_mesh.loops[loop_index].vertex_index

                    colour_layer.data[loop_index].color = vertices_local[vertex_index].r / 255, vertices_local[
                        vertex_index].g / 255, vertices_local[vertex_index].b / 255, vertices_local[
                                                              vertex_index].a / 255

            obj = bpy.data.objects.new(root_mesh.name, root_mesh)

            scene = bpy.context.scene
            scene.collection.objects.link(obj)

    @staticmethod
    def import_mesh(context, filepath: str) -> None:
        print(f"Importing {filepath}")
        vertices, faces, submeshes = ImportStormworksMesh.read_mesh(filepath)
        print(f"Finished Importing")

        ImportStormworksMesh.add_mesh("Imported Mesh", vertices, faces, submeshes)

    def execute(self, context) -> Set[str]:
        ImportStormworksMesh.import_mesh(context, self.filepath)
        return {"FINISHED"}
