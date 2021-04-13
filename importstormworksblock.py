import math
import os
import re
import xml.etree.ElementTree as ET
from typing import Set, Tuple

import numpy as np
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
from bpy_types import Operator

from .block import Block
from .importstormworksmesh import ImportStormworksMesh
from .shapedefs import SHAPES, TRANSFORMATIONS
from .vertex import Vertex


def findNormal(p1: Tuple[float, float, float], p2: Tuple[float, float, float],
               p3: Tuple[float, float, float], ) -> Tuple[float, float, float]:
    p1 = np.array(p1)
    p2 = np.array(p2)
    p3 = np.array(p3)

    edge1 = p2 - p1
    edge2 = p2 - p3

    normal = np.cross(edge1, edge2)

    normalisedNormal = normal / np.linalg.norm(normal)

    return (*normalisedNormal,)


class ImportStormworksBlock(Operator, ImportHelper):
    bl_idname = "stormworks_block_importer.block_data"
    bl_label = "Import Block"

    filename_ext = ".xml"

    filter_glob: StringProperty(
        default="*.xml",
        options={"HIDDEN"},
        maxlen=255,
    )

    @staticmethod
    def read_block(filepath: str, meshfolder: str) -> None:
        with open(filepath, "r") as file:
            xmlstring = file.read()

        xmlstring = re.sub(r"(\d\d=)", r"t\1", xmlstring)
        parsedContent = ET.fromstring(xmlstring)

        block = Block(parsedContent)

        print(block.meshname)

        if block.meshname != "":
            meshpath = os.path.join(meshfolder, block.meshname)
            vertices, faces = ImportStormworksMesh.read_mesh(meshpath)

            ImportStormworksMesh.add_mesh(block.meshname, vertices, faces)

        print(block.surfaces)

        for surface in block.surfaces:
            extrafaces = SHAPES[surface.shape]

            if len(extrafaces) == 0:
                continue

            transformations = TRANSFORMATIONS[surface.orientation]

            triangle = extrafaces[0]

            x, y, z = findNormal(*map(lambda a: a[0], triangle))

            transformation = [((x, y, z), surface.rotation / 2 * math.pi)]

            vertices = []
            faces = []

            indexCount = 0
            for face in extrafaces:
                for i in range(3):
                    position, normal = face[i]

                    print(position, normal)

                    vertex = Vertex(*position, 255, 255, 255, 255, *normal)

                    vertex.transform(transformation, (0, 0, 0))
                    vertex.transform(transformations, surface.position)

                    vertices.append(vertex)

                faces.append((indexCount, indexCount + 1, indexCount + 2))
                indexCount += 3

                ImportStormworksMesh.add_mesh(f"surface_{surface.shape}", vertices, faces)

    @staticmethod
    def import_tile(context, filepath: str) -> None:
        print(f"Importing {filepath}")
        ImportStormworksBlock.read_block(filepath, context.preferences.addons[__package__].preferences.meshfolderpath)
        print(f"Finished Importing")

    def execute(self, context) -> Set[str]:
        ImportStormworksBlock.import_tile(context, self.filepath)
        return {"FINISHED"}