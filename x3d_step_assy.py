from __future__ import division
from __future__ import print_function
'''
# Copyright (C) 2015, Elphel.inc.
# File: x3d_step_assy.py
# Generate x3d model from STEP parts models and STEP assembly
# by matching each solid in the assembly to the parts.
# Work in progress, not yet handles parts with symmetries
#
# Uses code from https://gist.github.com/hyOzd/2b38adff6a04e1613622
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http:#www.gnu.org/licenses/>.

@author:     Andrey Filippov
@copyright:  2015 Elphel, Inc.
@license:    GPLv3.0+
@contact:    andrey@elphel.coml
@deffield    updated: Updated
'''
__author__ = "Andrey Filippov"
__copyright__ = "Copyright 2015, Elphel, Inc."
__license__ = "GPL"
__version__ = "3.0+"
__maintainer__ = "Andrey Filippov"
__email__ = "andrey@elphel.com"
__status__ = "Development"

import FreeCAD
import Part
import os
import time
import pickle
import math

import xml.etree.ElementTree as et
from xml.dom import minidom
from FreeCAD import Base


ROOT_DIR = '~/parts/0393/export'
DIR_LIST = ["parts","subassy_flat"]
INFO_DIR = "info"
X3D_DIR = "x3d"
X3D_EXT = ".x3d"
INFO_EXT = ".pickle"
PRECISION = 0.0001
PRECISION_INSIDE = 0.03
COLOR_PER_VERTEX = True
if ROOT_DIR[0] == "~":
    ROOT_DIR = os.path.join(os.path.expanduser('~'),ROOT_DIR[2:])
def get_step_list(dir_list):
    step_files = []
    for rpath in dir_list:
        apath = os.path.join(ROOT_DIR,rpath)
        step_files += [os.path.join(rpath, f) for f in os.listdir(apath) if os.path.isfile(os.path.join(apath, f)) and f.endswith((".step",".stp"))]
    return step_files
def vector_to_tuple(v):
    return((v.x,v.y,v.z))

def repair_solids_from_shells(shape):
    solids = shape.Solids
    new_solids = []
    for sh in shape.Shells:
        #find same shell in solids
        for sld in solids:
            if sh.isEqual(sld.Shells[0]):
                new_solids.append(sld)
                break
        else:
            new_solids.append(Part.Solid(sh))
    return new_solids

#Find Vertex indices with maximal/minima  X,Y,Z to check orientation(Still does not check for holes - Add them somehow?
def verticesToCheck(solid):
    l=[[],[],[],[],[],[],[],[],[]]
    for v in solid.Vertexes:
       l[0].append(v.X)
       l[1].append(v.Y)
       l[2].append(v.Z)
       l[3].append(v.X + v.Y)
       l[4].append(v.X - v.Y)
       l[5].append(v.X + v.Z)
       l[6].append(v.X - v.Z)
       l[7].append(v.Y + v.Z)
       l[8].append(v.Y - v.Z)
    sind=set()
    for lst in l:
        sind.add(lst.index(min(lst)))
        sind.add(lst.index(max(lst)))
    lv=[]
    for vi in sind:
        v=solid.Vertexes[vi]
        lv.append((v.X,v.Y,v.Z))
    return lv

def create_file_info(shape, fname=""):
        objects = []
        #repairing open shells
        solids = shape.Solids
        if len(solids) != len(shape.Shells):
            print ("Repairing open shells that are not solids for %s"%(fname))
            solids = repair_solids_from_shells(shape)            
            fromShell=True
        else:
            fromShell=False                    
        for s in (solids):
            pp=s.PrincipalProperties
            objects.append({
              "rpath":  fname,  
              "shell":  fromShell,
              "volume": s.Volume,
              "area":   s.Area,
              "center": vector_to_tuple(s.CenterOfMass),
              "principal": {'RadiusOfGyration':    pp['RadiusOfGyration'],
                            'FirstAxisOfInertia':  vector_to_tuple(pp['FirstAxisOfInertia']),
                            'SecondAxisOfInertia': vector_to_tuple(pp['SecondAxisOfInertia']),
                            'ThirdAxisOfInertia':  vector_to_tuple(pp['ThirdAxisOfInertia']),
                            'Moments':             pp['Moments'],
                            'SymmetryPoint':       pp['SymmetryPoint'],
                            'SymmetryAxis':        pp['SymmetryAxis']},
              "vertices": verticesToCheck(s)
              })
        return objects
  
def get_info_files(dir_list = DIR_LIST):
    start_time=time.time()
    sl = get_step_list(dir_list = dir_list)
#    print ("Step files:")
#    for i,f in enumerate (sl):
#        print("%d: %s"%(i,f))
    if not INFO_DIR in os.listdir(ROOT_DIR):
        os.mkdir(os.path.join(ROOT_DIR,INFO_DIR))
    todo_list = []
    for f in sl:
        fname,_ =  os.path.splitext(os.path.basename(f))
#        print("%s -> %s"%(f,fname))
        if not os.path.isfile(os.path.join(ROOT_DIR,INFO_DIR,fname+INFO_EXT)):
            todo_list.append(f)
#    for i,f in enumerate (todo_list):
#        print("%d: %s"%(i,f))

    for i, f in enumerate(todo_list):
        apath=os.path.join(ROOT_DIR,f)
        rslt_path = os.path.join(ROOT_DIR,INFO_DIR, os.path.splitext(os.path.basename(f))[0] + INFO_EXT)

        print("%d: Reading %s @%f"%(i,apath, time.time()-start_time), end="...")
        shape = Part.read(apath)
        print(" got %d solids @%f"%(len(shape.Solids), time.time()-start_time))
        objects = create_file_info(shape,f)
        print (objects)

        pickle.dump(objects, open(rslt_path, "wb" ))
    # Now read all pickled data:
    info_dict = {}
    for f in sl:
        name = os.path.splitext(os.path.basename(f))[0]
        info_path = os.path.join(ROOT_DIR,INFO_DIR, name + INFO_EXT)
        info_dict[name] = pickle.load(open(info_path, "rb"))
    #Put largest element as the [0] index
    for k in info_dict:
        if len(info_dict[k]) >1:
            o = info_dict[k]
            print (k,len(o),o)
            vols = [s["volume"] for s in o]
            mi = vols.index(max(vols))
            print ("Largest solid is number %d"%(mi))
            if mi>0:
                o.insert(0,o.pop(mi))
    return info_dict

def findPartsTransformations(solids, objects, candidates, info_dict, precision=0.01):
    transformations=[]
    for i,s in enumerate(solids):
        tolerance = precision * s.BoundBox.DiagonalLength # Or should it be fraction of the translation distance?
        trans=[]
        for cand_name in candidates[i]:
            co = info_dict[cand_name][0]
            matrix_part = ppToMatrix(co['principal'],co['center'])
            # Now try 4 orientations (until the first match).
            # TODO - process parts with rotational axis (that allows certain, but not any rotation)
            matrix_part_inverse = matrix_part.inverse()
            for orient in range(4):
                matrix_assy = ppToMatrix(s.PrincipalProperties,s.CenterOfMass,orient)
                matrix_part_assy = matrix_assy.multiply(matrix_part_inverse)
                for j, v in enumerate (co['vertices']):
                    if not s.isInside(matrix_part_assy.multiply(FreeCAD.Vector(v)),tolerance,True):
#                        print("%d: %s Failed on orientation %d vertice #%d  (%f, %f,%f)"%(i,cand_name, orient, j, v[0],v[1],v[2]))
                        break
                else:
                    print("%d: %s - got transformation with orientation %d"%(i,cand_name, orient))
                    trans.append(matrix_part_assy)
                    break
            else:
                print("Could not find match for part %s, trying manually around that vertex"%(cand_name))
                # Seems to be a bug FreeCAD does not recognize seemingly perfect match even with huge tolerance
                # Will try manually around that point to find inside one
                try_vectors= ((-1,-1,-1), (-1,-1, 0), (-1,-1, 1),
                              (-1, 0,-1), (-1, 0, 0), (-1, 0, 1),
                              (-1, 1,-1), (-1, 1, 0), (-1, 1, 1),
                              ( 0,-1,-1), ( 0,-1, 0), ( 0,-1, 1),
                              ( 0, 0,-1),             ( 0, 0, 1),
                              ( 0, 1,-1), ( 0, 1, 0), ( 0, 1, 1),
                              ( 1,-1,-1), ( 1,-1, 0), ( 1,-1, 1),
                              ( 1, 0,-1), ( 1, 0, 0), ( 1, 0, 1),
                              ( 1, 1,-1), ( 1, 1, 0), ( 1, 1, 1))
                for orient in range(4):
                    matrix_assy = ppToMatrix(s.PrincipalProperties,s.CenterOfMass,orient)
                    matrix_part_assy = matrix_assy.multiply(matrix_part_inverse)
                    for j, v in enumerate (co['vertices']):
                        if not s.isInside(matrix_part_assy.multiply(FreeCAD.Vector(v)),tolerance,True):
                            for tv in try_vectors:
                                mv= FreeCAD.Vector(v[0]+tv[0]*tolerance, v[1]+tv[1]*tolerance, v[2]+tv[2]*tolerance)
                                if s.isInside(matrix_part_assy.multiply(mv),tolerance,True):
                                    break # got it!
                            else:
                                break # no luck
                    else:
                        print("%d: %s - finally got transformation with orientation %d"%(i,cand_name, orient))
                        trans.append(matrix_part_assy)
                        break
                else:
                    trans.append(None) # so Transformations have same structure as candidates
                    print("*** Could not find match for part %s"%(cand_name))
        transformations.append(trans)        
    return transformations    

#components=scan_step_parts.findComponents("/home/andrey/parts/0393/export/nc393_05_flat_noassy.stp")
def findComponents(assembly_path, precision_inside = PRECISION_INSIDE, precision = PRECISION):
    start_time=time.time()
    print("Getting parts database")
    info_dict = get_info_files()
    print("Reading assembly file %s @%f"%(assembly_path, time.time()-start_time), end="...")
    shape = Part.read(assembly_path)
    print(" got %d solids @%f"%(len(shape.Solids), time.time()-start_time))
    objects = create_file_info(shape,assembly_path)
    print (objects)
    candidates=[]
    for i,o in enumerate(objects):
        this_candidates = []
        rg=o['principal']['RadiusOfGyration']
        rgp = precision*math.sqrt(rg[0]**2 + rg[1]**2 + rg[2]**2)
        vp = o['volume']*precision
        ap = o['area']*precision
        for n in info_dict:
            co = info_dict[n][0]
            if ((abs(o['volume'] - co['volume']) < vp) and
                (abs(o['area'] -   co['area']) <   ap) and
                (abs(rg[0] -       co['principal']['RadiusOfGyration'][0]) <   ap) and
                (abs(rg[1] -       co['principal']['RadiusOfGyration'][1]) <   ap) and
                (abs(rg[2] -       co['principal']['RadiusOfGyration'][2]) <   ap)):
                this_candidates.append(n)
        candidates.append(this_candidates)
    solids = shape.Solids
    if len(solids) != len(shape.Shells):
        print ("Repairing open shells that are not solids for %s"%(assembly_path))
        solids = repair_solids_from_shells(shape)            
        
    transformations = findPartsTransformations(solids, objects, candidates, info_dict, precision_inside)
    #Each part can be in two orientations - check overlap after loading actual parts
    return {"shape":shape,"objects":objects,"candidates":candidates,"transformations":transformations}
  
def ortho3(v0,v1):
    v0.normalize()
    dv = FreeCAD.Vector(v0).multiply(v0.dot(v1))
    v1  = v1.sub(dv)
    v1.normalize()
    v2= v0.cross(v1)
    v2.normalize()
    return (v0,v1,v2)
    
    

def ppToMatrix(pp, center=(0,0,0), orient=0): #Both Vectors and lists/tuples are OK here
    v0 = FreeCAD.Vector(pp["FirstAxisOfInertia"])
    v1 = FreeCAD.Vector(pp["SecondAxisOfInertia"])
    v2 = FreeCAD.Vector(pp["ThirdAxisOfInertia"])
    t =  FreeCAD.Vector(center)
    if (orient & 1 ) :
        v0.multiply(-1.0)        
    if (orient & 2 ) :
        v1.multiply(-1.0)        
    #v0,v1,v2 = ortho3(v0,v1)
    if v2.dot(v0.cross(v1)) < 0 :
        v2.multiply(-1.0)        
    return  FreeCAD.Matrix(v0.x, v1.x, v2.x, t.x,
                           v0.y, v1.y, v2.y, t.y,
                           v0.z, v1.z, v2.z, t.z,
                           0.0,  0.0,  0.0,  1.0)
    
def traslateToMatrix(center=(0,0,0)): #Both Vectors and lists/tuples are OK here
    t =  FreeCAD.Vector(center)
    return  FreeCAD.Matrix( 1.0, 0.0, 0.0, t.x,
                            0.0, 1.0, 0.0, t.y,
                            0.0, 0.0, 1.0, t.z,
                            0.0, 0.0, 0.0, 1.0)


def list_parts_offsets():
    info_files = get_info_files()
    for i, name in enumerate(info_files):
        for j,o in enumerate(info_files[name]):
            d = math.sqrt(o["center"][0]**2 + o["center"][1]**2 + o["center"][2]**2)
            if j == 0:
                print("%3i:"%(i), end="")
            else:
                print("    ", end="")
            print("%s offset = %6.1f"%(name, d))


# X3D Export
def getShapeNode(vertices, faces, diffuseColor = None, main_color_index = 0, colorPerVertex = True):
    """Returns a <Shape> node for given mesh data.
    vertices: list of vertice coordinates as `Vector` type
    faces: list of tuple of vertice indexes and optionally a face color index ex: (1, 2, 3) or (1, 2, 3, 0)
    diffuseColor: None or a list with 3*N color component values i the form of [R, G, B, R1, G1, B1, ...]
    If only 3 color components are specified, they are applied to the whole shape, otherwise each vertex
    is assigned color from the face color index
    """

    shapeNode = et.Element('Shape')
    faceNode = et.SubElement(shapeNode, 'IndexedFaceSet')
    faceNode.set('coordIndex', ' '.join(["%d %d %d -1" % face[0:3] for face in faces]))
    if diffuseColor and (len(diffuseColor) > 3): # Multi-color
        if not colorPerVertex:
            faceNode.set('colorPerVertex', 'false')
            faceNode.set('colorIndex', ' '.join(["%d"%(f[3]) for f in faces]))
        else:  
            faceNode.set('colorIndex', ' '.join(["%d %d %d -1"%(f[3],f[3],f[3]) for f in faces]))
    coordinateNode = et.SubElement(faceNode, 'Coordinate')
    coordinateNode.set('point',' '.join(["%f %f %f" % (p.x, p.y, p.z) for p in vertices]))

    if diffuseColor:
        if len(diffuseColor) > 3:
            colorNode = et.SubElement(faceNode, 'Color')
            colorNode.set('color',' '.join(["%f" % (c) for c in diffuseColor]))
        appearanceNode = et.SubElement(shapeNode, 'Appearance')
        materialNode = et.SubElement(appearanceNode, 'Material')
        materialNode.set('diffuseColor', "%f %f %f" % tuple(diffuseColor[main_color_index * 3: main_color_index * 3 + 3]))
    return shapeNode

def exportX3D(objects, filepath, colorPerVertex):
    """Export given list of objects to a X3D file.

    Each object is a dictionary in this form:
    {
        points : [Vector, Vector...],
        faces : [(pi, pi, pi, ci), ...],    # pi: point index, ci - color index (optional)
        color : [R, G, B,...]            # number range is 0-1.0, exactly 3 elements for a single color, 3*N for per-vertex colors
    }
    """

    x3dNode = et.Element('x3d')
    x3dNode.set('profile', 'Interchange')
    x3dNode.set('version', '3.3')
    sceneNode = et.SubElement(x3dNode, 'Scene')
    progress_bar = Base.ProgressIndicator()
    progress_bar.start("Saving objects to X3D file %s ..."%(filepath), len(objects))

    for o in objects:
        shapeNode = getShapeNode(o["points"], o["faces"], o["color"], o["main_color_index"], colorPerVertex)
        sceneNode.append(shapeNode)
        progress_bar.next() # True) # True - enable ESC to abort
        
    oneliner= et.tostring(x3dNode)
    reparsed = minidom.parseString(oneliner)

    with open(filepath, "wr") as f:
        f.write(reparsed.toprettyxml(indent="  "))
    progress_bar.stop()

def prepareX3dExport(freecadObjects, fname=""):
    objects = []
    progress_bar = Base.ProgressIndicator()
    txt=""
    if fname:
        txt += " in "+fname
    progress_bar.start("Generating objects%s to export to X3D ..."%(txt), len(freecadObjects))

    for o in freecadObjects:
        progress_bar.next() # True) # have to do it here as 'for' uses 'continue', True - enable ESC to abort
        if (not o.ViewObject) or (o.ViewObject.Visibility):
            if hasattr(o, "Shape"):
                color_set=set()
                if o.ViewObject:
                    for clr in o.ViewObject.DiffuseColor:
                        color_set.add(clr)
                if (len(color_set)>1): # process multi-color objects
                    col_list = list(color_set)
                    col_dict={} # index for each color (reverse to list)
                    for i, clr in enumerate(col_list):
                        col_dict[clr] = i
                    points = [] # common for all faces
                    faces = [] # flat list
                    colors=[]
                    color_areas = [0.0] * len(col_list)
                    for c in col_list:
                        colors += c[0:3] # only 3 first elements of 4
                    for i,f in enumerate(o.Shape.Faces):
                        mesh = f.tessellate(1)
                        if (not mesh[0]) or (not mesh[1]):
                            continue  # some objects (such as Part:Circle)
                        color_index = col_dict[o.ViewObject.DiffuseColor[i]]
                        color_areas [color_index] += f.Area                              
                        delta = len(points)
                        new_indices=[]
                        for tf in mesh[1]:
                            new_indices.append((tf[0]+delta,tf[1]+delta,tf[2]+delta, color_index)) # last element - color index
                        faces  += new_indices
                        points += mesh[0]
                    #find color with maximal area (will use in "Appearance")
                    main_color_index = color_areas.index(max(color_areas))
                    objects.append({
                        "points":           points,
                        "faces":            faces, # Here - 2-d list of tuples
                        "color":            colors, # colors is a list of 3*n elements (n>1)
                        "main_color_index": main_color_index
                    })
                else: #same color for the whole object 
                    if o.ViewObject:
                        colors = o.ViewObject.DiffuseColor[0][0:3]
                    else:
                        colors = [0.7,0.7,0.3]
                    mesh = o.Shape.tessellate(1)

                    if (not mesh[0]) or (not mesh[1]):
                        continue  # some objects (such as Part:Circle)
                              # generate empty mesh, skip them

                    objects.append({
                        "points":           mesh[0],
                        "faces":            mesh[1],
                        "color":            colors, # color is a list of 3 elements
                        "main_color_index": 0})
    progress_bar.stop()
    return objects

def generatePartsX3d(dir_list = DIR_LIST, colorPerVertex = COLOR_PER_VERTEX):
    info_dict= get_info_files(dir_list) # Will (re-) build info files if missing
    step_list = get_step_list(dir_list) #relative to ROOT_DIR
    if not X3D_DIR in os.listdir(ROOT_DIR):
        os.mkdir(os.path.join(ROOT_DIR,X3D_DIR))
    for step_file in step_list:
        partName,_ =  os.path.splitext(os.path.basename(step_file))
        x3dFile = os.path.join(ROOT_DIR,X3D_DIR,partName + X3D_EXT)
        if not os.path.isfile(x3dFile):
            # Prepare data
            FreeCAD.loadFile(os.path.join(ROOT_DIR,step_file))
            doc = FreeCAD.activeDocument()
            doc.Label = partName
            x3d_objects = prepareX3dExport(doc.Objects, step_file) # step_file needed just for progress bar
            exportX3D(x3d_objects, x3dFile, colorPerVertex)
            FreeCAD.closeDocument(doc.Name)

def matrix4ToX3D(m, eps=0.000001): #assuming 3x3 matrix is pure rotational
    axis=FreeCAD.Vector(m.A32-m.A23, m.A13-m.A31, m.A21-m.A12)
    r = axis.Length # math.sqrt(axis.X**2 + axis.Y**2 + axis.Z**2)
    tr = m.A11 + m.A22 + m.A33
    theta= math.atan2(r,tr - 1)
    if r> eps:
        axis.normalize()
    else:
        #Based on Java code http://www.euclideanspace.com/maths/geometry/rotations/conversions/matrixToAngle
        if abs(tr-3.0) < eps:
            theta = 0
            axis = FreeCAD.Vector(1, 0, 0)
        else:
            theta = math.pi
            sqr2=math.sqrt(2)
            xx = (m.A11+1)/2;
            yy = (m.A22+1)/2;
            zz = (m.A33+1)/2;
            xy = (m.A12+m.A21)/4;
            xz = (m.A13+m.A31)/4;
            yz = (m.A23+m.A32)/4;
            if (xx > yy) and (xx > zz): # m.A11 is the largest diagonal term
                if xx <eps:
                    axis = FreeCAD.Vector(0,sqr2,sqr2)
                else:
                    x = math.sqrt(xx)
                    axis = FreeCAD.Vector(x,xy/x,xz/x)
            elif yy > zz: # m.A22 is the largest diagonal term
                if yy <eps:
                    axis = FreeCAD.Vector(sqr2,0.0,sqr2)
                else:
                    y = math.sqrt(yy)
                    axis = FreeCAD.Vector(xy/y, y, yz/y)
            else:  # m.A33 is the largest diagonal term
                if zz <eps:
                    axis = FreeCAD.Vector(sqr2, sqr2, 0.0)
                else:
                    z = math.sqrt(zz)
                    axis = FreeCAD.Vector(xz/z, yz/z, z)
    return{"translation": (m.A14,m.A24,m.A34),
           "rotation":    (axis.x, axis.y, axis.z, theta)}



def generateAssemblyX3d(assembly_path, components = None, dir_list = DIR_LIST, colorPerVertex = COLOR_PER_VERTEX):
    info_dict = get_info_files(dir_list) # Will (re-) build info files if missing
    generatePartsX3d(dir_list = DIR_LIST, colorPerVertex = COLOR_PER_VERTEX) # Will only run if files are not there yet
    if not components:
        components = findComponents(assembly_path, precision_inside = PRECISION_INSIDE, precision = PRECISION)
    assName,_ =  os.path.splitext(os.path.basename(assembly_path))
    x3dFile = os.path.join(ROOT_DIR,X3D_DIR,assName + X3D_EXT) # currently in the same directory as parts
    x3dNode = et.Element('x3d')
    x3dNode.set('profile', 'Interchange')
    x3dNode.set('version', '3.3')
    sceneNode = et.SubElement(x3dNode, 'Scene')
    # Including file with (manually created)  NavInfo, Cameras, etc that should not be overwritten when regenerating assembly model
    inlineNode = et.SubElement(sceneNode, 'Inline')
    inlineNode.set('id', assName + '_config')
    inlineNode.set('url',assName + '_config'+ X3D_EXT)
    inlineNode.set('nameSpaceName',assName)

    modelNode = et.SubElement(sceneNode, 'Transform')
    modelNode.set('id','transform_'+assName)
    modelNode.set('translation','%f %f %f'%(0,0,0))
    modelNode.set('rotation','%f %f %f %f'%(0,0,0,0))

    defined_parts = {} # for each defined part holds index (for ID generation)
    for i, component in enumerate(components['objects']):
        parts =           components['candidates'][i]
        transformations = components['transformations'][i] # same structure as candidates, missing - 'None'
        for transformation, part in zip(transformations,parts):
            if transformation:
                break
        else:
            print("Component %d does not have any matches, ignoring. Candidates: %s"%(i,str(parts)))
            continue
        bbox=components['shape'].Shells[i].BoundBox
        bboxCenter=((bbox.XMax + bbox.XMin)/2,(bbox.YMax + bbox.YMin)/2,(bbox.ZMax + bbox.ZMin)/2)
        bboxSize=  ( bbox.XMax - bbox.XMin,    bbox.YMax - bbox.YMin,    bbox.ZMax - bbox.ZMin)

        transform = matrix4ToX3D(transformation)
        rot=transform['rotation']
        print("%d: Adding %s, rotation = (x=%f y=%f z=%f theta=%f)"%(i,part,rot[0],rot[1],rot[2],rot[3]))
        if part in defined_parts:
            defined_parts[part] += 1
        else:
            defined_parts[part] = 0
        switchNode = et.SubElement(modelNode, 'Switch')
        switchNode.set('id','switch_'+part+":"+str(defined_parts[part]))
        switchNode.set('class','switch_'+part)
        switchNode.set('whichChoice','0')
        transformNode = et.SubElement(switchNode, 'Transform')
        transformNode.set('id','transform_'+part+":"+str(defined_parts[part]))
        transformNode.set('class','transform_'+part)
        transformNode.set('translation','%f %f %f'%transform['translation'])
        transformNode.set('rotation','%f %f %f %f'%transform['rotation'])
        groupNode = et.SubElement(transformNode, 'Group')
        groupNode.set('id','group_'+part+":"+str(defined_parts[part]))
        groupNode.set('class','group_'+part)
        groupNode.set('bboxSize','%f %f %f'%bboxSize)
        groupNode.set('bboxCenter','%f %f %f'%bboxCenter)
        
        if defined_parts[part]:
            groupNode.set('USE', part)
        else:
            groupNode.set('DEF', part)
            inlineNode = et.SubElement(groupNode, 'Inline')
            inlineNode.set('id','inline_'+part+":"+str(defined_parts[part]))
            inlineNode.set('class','inline_'+part)
#            inlineNode.set('url',os.path.join(X3D_DIR,part + X3D_EXT))
            inlineNode.set('url',part + X3D_EXT)
            inlineNode.set('nameSpaceName',part)

    oneliner= et.tostring(x3dNode)
    reparsed = minidom.parseString(oneliner)
    print ("Writing assembly to %s"%(x3dFile))
    with open(x3dFile, "wr") as f:
        f.write(reparsed.toprettyxml(indent="  "))



def run():
    get_info_files()
    
if __name__ == "__main__":    
    run()

