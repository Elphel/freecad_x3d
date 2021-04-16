'''
# Copyright (C) 2015, Elphel.inc.
# File: x3d_step_assy_color_match.py
# Generate x3d model from STEP parts models and STEP assembly
# by matching each solid in the assembly to the parts.
#
# Uses code from https://gist.github.com/hyOzd/2b38adff6a04e1613622
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.#
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
#from email import Errors
__author__ = "Andrey Filippov"
__copyright__ = "Copyright 2015, Elphel, Inc."
__license__ = "GPL"
__version__ = "3.0+"
__maintainer__ = "Andrey Filippov"
__email__ = "andrey@elphel.com"
__status__ = "Development"

import FreeCAD
import FreeCADGui # just to update console output (change to threads later?) - does not seem to work
import Part
import os
import time
import pickle
import math
import pprint # pretty print objects

import xml.etree.ElementTree as et
from xml.dom import minidom
from FreeCAD import Base

from PySide import QtCore, QtGui
#from ConfigParser import SafeConfigParser #In Python 3, ConfigParser has been renamed to configparser for PEP 8 compliance. 
#from configparser import SafeConfigParser #In Python 3, ConfigParser has been renamed to configparser for PEP 8 compliance. 
from configparser import ConfigParser #In Python 3, ConfigParser has been renamed to configparser for PEP 8 compliance. 
import sys
import traceback
#https://github.com/FreeCAD/FreeCAD/blob/master/src/Mod/Part/App/ImportStep.cpp
CONFIG_PATH= "~/.FreeCAD/x3d_step_assy.ini"
ROOT_DIR = '~/parts/0393/export'
STEP_PARTS='~/parts/0393/export/step_parts'
#DIR_LIST = ["parts","subassy_flat"]
ASSEMBLY_PATH = ""
ASSEMBLY_SUFFIX = "-ASSY"
INFO_DIR = "info"
X3D_DIR = "x3d"
X3D_EXT = ".x3d"
INFO_EXT = ".pickle"
PRECISION = 0.0001
PRECISION_AREA = 0.001
PRECISION_VOLUME = 0.001
PRECISION_GYRATION = 0.001
PRECISION_INSIDE = 0.03

COLOR_PER_VERTEX = True

COMPONENTS = None # to hold data structure that is long to build so it will survive if the macro crashes
if CONFIG_PATH[0] == "~":
    CONFIG_PATH = os.path.join(os.path.expanduser('~'),CONFIG_PATH[2:])

if ROOT_DIR[0] == "~":
    ROOT_DIR = os.path.join(os.path.expanduser('~'),ROOT_DIR[2:])
if STEP_PARTS[0] == "~":
    STEP_PARTS = os.path.join(os.path.expanduser('~'),STEP_PARTS[2:])
    
def get_step_list(dir_listdirs):
    """
    @param dir_listdirs - a single directory path or a list of directories to scan for parts definitions as STEP files
    @return a list of full paths of the STEP parts models
    """
    if not isinstance(dir_listdirs,(list,tuple)):
        dir_listdirs=[dir_listdirs]
    return [os.path.join(root,f) 
      for dir_path in dir_listdirs if os.path.isdir(dir_path)
       for root, _, files in os.walk(dir_path, topdown=True, onerror=None, followlinks = True)
        for f in files if f.endswith((".step",".stp",".STP",".STEP"))]
        

def vector_to_tuple(v):
    return((v.x,v.y,v.z))

def repair_solids_from_shells(shape):
    """
    Some imported object from STEP files turned out to be open shells.
    Convert them to solids with FreeCAD
    @param shape - FreeCAD Shape
    @return a list of FreeCAD solids
    """
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

#Find Vertex indices with maximal/minimal  X,Y,Z to check orientation(Still does not check for holes - Add them somehow?
def verticesToCheck(solid):
    """
    Create a list of 18 vertices having maximal/minimal X, Y, Z (and their +/- pairs).
    These vertices will be later tested to be inside (with certain precision) the assembly part
    @param solid - A Solid object
    @return list of 18 3-tuples (x,y,z) 
    """
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

def  getBoundBox(freecadObjects):
    """
    Calculate BoundBox for all shapes in the document
    @param freecadObjects - list of FreeCAD objects or all solids/shells
    @return FreeCAD.BoundBox object for the whole document
    """
    shells =[]
    for o in freecadObjects:
        if hasattr(o, "Shape"):
            shape=o.Shape
            for shell in shape.Shells: # solids and open shells
                shells.append(shell)
        elif hasattr(o, "BoundBox"):
            shells.append(o)
    bBox=None
            
    for shell in shells:
        thisBBox = shell.BoundBox
        if not bBox:
            bBox = FreeCAD.BoundBox(thisBBox.XMin,thisBBox.YMin,thisBBox.ZMin,
                                    thisBBox.XMax,thisBBox.YMax,thisBBox.ZMax)
        else:
            bBox = FreeCAD.BoundBox(min(thisBBox.XMin,bBox.XMin),min(thisBBox.YMin,bBox.YMin),min(thisBBox.ZMin,bBox.ZMin),
                                    max(thisBBox.XMax,bBox.XMax),max(thisBBox.YMax,bBox.YMax),max(thisBBox.ZMax,bBox.ZMax))
                        
    return bBox
 
def bBoxToX3d(bBox):
    """
    Convert FreeCAD BoundBox to X3D representation (center, size)
    @param bBox - FreeCAD BoundBox object
    @return dictionary of {'center':(xc,yc,zc), size:(xs,ys,zs)}
    """
    return {'center':((bBox.XMax + bBox.XMin)/2,(bBox.YMax + bBox.YMin)/2,(bBox.ZMax + bBox.ZMin)/2),
            'size':  ( bBox.XMax - bBox.XMin,    bBox.YMax - bBox.YMin,    bBox.ZMax - bBox.ZMin)}

    
    
    #FreeCAD.BoundBox(0,0,0,0,0,0)
def create_file_info_nogui(shape, fname=""):
    """
    A no-Gui version of the create_file_info, rather useless now as the color
    is critical for the program. Using FreeCAD GGUI significantly slows down
    the program and prevents it from running in a true batch mode. It seems
    possible to hack Face.Tolerance property (unused so far) and import STEP
    files saving colors in this property.
    @param shape - FreeCAD Shape, containing one or more solids
    @param fname - source file path
    @return a pair of a list of info for each solid (as a dictionary) and a
              list of solids in the shape
    """
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
#    return objects
    return (objects,solids)


def create_file_info(freecadObjects, fname=""):
    """
    Collect information about each part/solid to be used for comparison between
    assembly objects and parts
    @param freecadObjects - list of FreeCAD objects
    @param fname - source file path
    @return a pair of a list of info for each solid (as a dictionary) and a
              list of solids in the shape
    """
    
    if not "Gui" in dir(FreeCAD):
        return create_file_info_nogui(freecadObjects, fname)
    # Count all shells in all objects
    numShells = 0
    for o in freecadObjects:
        if hasattr(o, "Shape"):
            numShells += len(o.Shape.Shells)
    txt=""
    if fname:
        txt += " in "+fname

    progress_bar = Base.ProgressIndicator()
    progress_bar.start("Generating objects%s to export to X3D ..."%(txt), len(freecadObjects))
    FreeCAD.Console.PrintMessage("Generating %d objects%s to export to X3D\n"%( len(freecadObjects), txt));
    print("Generating %d objects%s to export to X3D\n"%( len(freecadObjects), txt));

    objects = []
    
    pp = pprint.PrettyPrinter(indent=4)

    allSolids=[]
    for o in freecadObjects:
#        FreeCAD.Console.PrintMessage("Generating object # %d\n"%(no));
#        print("Generating object # %d"%(no));
        if hasattr(o, "Shape"):
            shape=o.Shape
            #repairing open shells
            solids = shape.Solids
            if len(solids) != len(shape.Shells):
                print ("Repairing open shells that are not solids for %s"%(fname))
                solids = repair_solids_from_shells(shape)            
                fromShell=True
            else:
                fromShell=False
            # get all colors for faces in this object (normally just one Shell/Solid
            color_set=set()
            try:
                dc = o.ViewObject.DiffuseColor
            except AttributeError:
                continue 
            for clr in dc: # colors are one per face
                color_set.add(clr)
            col_list = list(color_set)
            col_dict={} # index for each color (reverse to list)
            for i, clr in enumerate(col_list):
                col_dict[clr] = i
            #Calculate per-color centers for each object (normally each object has just one Solid/Shell
            if (len(dc) == 1) and (len(o.Shape.Faces)>1):
                dc= dc * len(o.Shape.Faces)
            colorCenters=[[0.0,0.0,0.0,0.0] for c in col_list] # SX,SY,SZ,S0
            for clr,face in zip(dc, o.Shape.Faces):
                clr_index = col_dict[clr]
                m = face.Area
                c = face.CenterOfMass # Vector
                colorCenters[clr_index][0]+= c.x * m
                colorCenters[clr_index][1]+= c.y * m
                colorCenters[clr_index][2]+= c.z * m
                colorCenters[clr_index][3]+= m
#                print ("%s: cx=%f, cy=%f, cz=%f, m=%f"%(fname, c.x,c.y,c.z,m))
            color_center_area={}
            for clr in col_dict:
                clr_index = col_dict[clr]
                color_center_area[clr]={"center":(colorCenters[clr_index][0]/colorCenters[clr_index][3],
                                                  colorCenters[clr_index][1]/colorCenters[clr_index][3],
                                                  colorCenters[clr_index][2]/colorCenters[clr_index][3]),
                                        "area":   colorCenters[clr_index][3]}
#                print ("color_center_area[%s] = %s"%(str(clr), str(color_center_area[clr])))
                        
            for i, s in enumerate(solids):
                pp=s.PrincipalProperties
                object={
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
                  }
                if i == 0:
                    object["colorCenters"] = color_center_area  
                objects.append(object)
                allSolids.append(s)  
                progress_bar.next() # True) # True - enable ESC to abort

    progress_bar.stop()
    return (objects,allSolids)
  
def get_info_files_nogui(dir_list = None):
    """
    a no-gui version of get_info_files()
    @param dir_list - list of directories (usually a single-element) to scan for
                      STEP part models (including subdirectories). Non-existing
                      directories in the list are OK, they will be silently skipped.
    @return a dictionary with part names as keys and info parameters lists of
            dictionaries created by create_file_info() as values
            Each part usually has just one solid, but may have more than one, in that
            case only the largest (by volume) is used for identification in the
            assembly, and it is returned at index 0 in the result
    """
    if dir_list is None:
        dir_list = [STEP_PARTS]
    start_time=time.time()
    sl = get_step_list(dir_list = dir_list)
    if not INFO_DIR in os.listdir(ROOT_DIR):
        os.mkdir(os.path.join(ROOT_DIR,INFO_DIR))
    todo_list = []
    for f in sl: # now f is a full absolute path
        fname,_ =  os.path.splitext(os.path.basename(f))
        info_path = os.path.join(ROOT_DIR,INFO_DIR,fname+INFO_EXT)
        step_file = f # os.path.join(ROOT_DIR, f)
        if (not os.path.isfile(info_path)) or (os.path.getmtime(step_file) > os.path.getmtime(info_path)): # no info or step is newer
            todo_list.append(f)

    for i, apath in enumerate(todo_list):
#        apath = os.path.join(ROOT_DIR,f)
        rslt_path = os.path.join(ROOT_DIR,INFO_DIR, os.path.splitext(os.path.basename(apath))[0] + INFO_EXT)

        print("%d: Reading %s @%f"%(i,apath, time.time()-start_time), end="...")
        shape = Part.read(apath)
        print(" got %d solids @%f"%(len(shape.Solids), time.time()-start_time))
        objects,_ = create_file_info_nogui(shape, apath)
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

def get_info_files(dir_list = None):
    """
    Get information about each part collected with create_file_info() function
    Generate this information for each part that does not have it or have
    obsolete (older than STEP file) one.
    @param dir_list - list of directories (usually a single-element) to scan for
                      STEP part models (including subdirectories). Non-existing
                      directories in the list are OK, they will be silently skipped.
    @return a dictionary with part names as keys and info parameters lists of
            dictionaries created by create_file_info() as values
            Each part usually has just one solid, but may have more than one, in that
            case only the largest (by volume) is used for identification in the
            assembly, and it is returned at index 0 in the result
    """
    if dir_list is None:
        dir_list = [STEP_PARTS]
    if not "Gui" in dir(FreeCAD):
        return get_info_files_nogui(dir_list)
    start_time=time.time()
    sl = get_step_list(dir_listdirs = dir_list)
    
    if not INFO_DIR in os.listdir(ROOT_DIR):
        os.mkdir(os.path.join(ROOT_DIR,INFO_DIR))
    todo_list = []
    for f in sl: # now f is a full absolute path
        print (f)
        fname,_ =  os.path.splitext(os.path.basename(f))
        info_path = os.path.join(ROOT_DIR,INFO_DIR,fname+INFO_EXT)
        step_file = f # os.path.join(ROOT_DIR, f)
        if (not os.path.isfile(info_path)) or (os.path.getmtime(step_file) > os.path.getmtime(info_path)): # no info or step is newer
            todo_list.append(f)

    for i, apath in enumerate(todo_list):
#        apath=os.path.join(ROOT_DIR,f)
        rslt_path = os.path.join(ROOT_DIR,INFO_DIR, os.path.splitext(os.path.basename(apath))[0] + INFO_EXT)
        print("%d: Reading %s @%f"%(i,apath, time.time()-start_time), end="...")
        # Prepare data
        FreeCAD.loadFile(apath)
        doc = FreeCAD.activeDocument()
        doc.Label = fname
        print(" got %d objects @%f"%(len(doc.Objects), time.time()-start_time))
        objects,_ = create_file_info(doc.Objects, apath)
        FreeCAD.closeDocument(doc.Name)
        FreeCADGui.updateGui()
#        print (objects)
        pickle.dump(objects, open(rslt_path, "wb" ))
    # Now read all pickled data:
    
    info_dict = {}
    progress_bar = Base.ProgressIndicator()
    progress_bar.start("Reading %d part info files ..."%(len(sl)), len(sl))
    for f in sl:
        name = os.path.splitext(os.path.basename(f))[0]
        info_path = os.path.join(ROOT_DIR,INFO_DIR, name + INFO_EXT)
        info_dict[name] = pickle.load(open(info_path, "rb"))
        progress_bar.next()
        print("Read info for ", name)
        if name == '0393-13-14A':
            print ('info_dict[name]=',info_dict[name])
    progress_bar.stop()
#    FreeCAD.Console.PrintMessage("get_info_files() - loaded"); #Rare FreeCAD crash?

    #Put largest element of multi-solid parts as the [0] index. 
    for k in info_dict:
        if len(info_dict[k]) >1:
            o = info_dict[k]
            print (k,len(o),o)
            vols = [s["volume"] for s in o]
#            vols = [s['principal']['RadiusOfGyration'][0] for s in o] # RadiusOfGyration[2] better characterizes the outer(larger) object?
                                                                      # Maybe it is just outer thread?
            mi = vols.index(max(vols))
            print ("Largest solid is number %d"%(mi))
            if mi>0:
                o.insert(0,o.pop(mi))
#    FreeCAD.Console.PrintMessage("get_info_files() - largest made first"); # rare FreeCAD crash?
    return info_dict


def findPartsTransformations(solids, objects, candidates, info_dict, insidePrecision = PRECISION_INSIDE, precision = PRECISION):
    """
    Find transformation (translation+rotation) matrices for each assembly part and each candidate part
    @param solids - list of solids, they are used to check that the test part vertices are almost inside
                    Number of elements in solids, objects, candidates  should match
    @param objects - list of the solid properties (as dictionaries made by create_file_info()) of the assembly
                    elements.                 
    @param candidates - list (per assembly element) of dictionaries indexed by part name (usually just one),
                        containing list of colors (tuples) for which there is an area match between assembly
                        element and a part. Build element part frame from colors first, then (if not enough)
                        use inertial directions.
    @param info_dict - dictionary (part name as a key) of lists (first element is the largest by volume) of
                       part solid properties used for matching
    @param inside_precision - precision for determining if the test points (available for each part) get inside
                              the assembly element. Currently as a fraction of the object bounding box diagonal,
                              but maybe it is better to use fraction of the translation distance plus diagonal?
    @param precision - relative precision for matrix/vector calculations (determining co-linear/co-planar objects                   
    @return a list (per assembly solid) of dictionaries part_name -> 4x4 transformation matrix (not yet tested
                              with multiple fits
            
    """
    progress_bar = Base.ProgressIndicator()
    progress_bar.start("Finding transformations for library parts to match assembly elements ...", len(objects))
    transformations=[]
    for i,s in enumerate(solids):
        tolerance = insidePrecision * s.BoundBox.DiagonalLength # Or should it be fraction of the translation distance?
        trans={}
        print ("%d findPartsTransformations:"%(i))
        for cand_name in candidates[i]:
            print("cand_name=",cand_name)
            co = info_dict[cand_name][0] # First solid in the candidate part file 
            print("co=",co)
            print("candidates[i]=",candidates[i])
            print("candidates[i][cand_name]=",candidates[i][cand_name])
            try:
                colorCenters = co['colorCenters']
            except:
                colorCenters = {}
            """
def ppToMatrix(pp,
               center =      (0,0,0),
               colorCenters = {}, # should have all the colors in a colors list "by design"
               colors =       [],
               orient  =      0,
               precision =    PRECISION): 
            
            """
            matrix_part = ppToMatrix(co['principal'],co['center'], colorCenters, candidates[i][cand_name], 0, precision)
            
            # Now try 4 orientations (until the first match).
            # TODO - process parts with rotational axis (that allows certain, but not any rotation)
            matrix_part_inverse = matrix_part.inverse()
            # get color properties of a solid
            try:
                colorCenters = objects[i]['colorCenters']
            except:
                colorCenters = {}    
            for orient in range(4):
                matrix_assy = ppToMatrix(s.PrincipalProperties,s.CenterOfMass,colorCenters, candidates[i][cand_name], orient, precision)
                matrix_part_assy = matrix_assy.multiply(matrix_part_inverse)
                for j, v in enumerate (co['vertices']):
                    if not s.isInside(matrix_part_assy.multiply(FreeCAD.Vector(v)),tolerance,True):
#                        print("%d: %s Failed on orientation %d vertice #%d  (%f, %f,%f)"%(i,cand_name, orient, j, v[0],v[1],v[2]))
                        break
                else:
                    print("%d: %s - got transformation with orientation %d"%(i,cand_name, orient))
#                    trans.append(matrix_part_assy)
                    trans[cand_name] = matrix_part_assy
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
                    matrix_assy = ppToMatrix(s.PrincipalProperties,s.CenterOfMass,colorCenters, candidates[i][cand_name], orient, precision)
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
#                        trans.append(matrix_part_assy)
                        trans[cand_name] = matrix_part_assy
                        break
                else:
#                    trans.append(None) # so Transformations have same structure as candidates, and it is now dictionary
                    print("*** Could not find match for part %s"%(cand_name))
        transformations.append(trans)
        progress_bar.next() # True)
    progress_bar.stop()        
    return transformations

    
def colorMatchCandidate(assy_object, candidates, info_dict, precision = PRECISION_AREA):
    """
    Select colored features among the parts candidates by comparing total area per color
    with the candidates so if some feature on the assembly object and the part have
    different colors, the others can still be used for orientation identification.
    Parts w/o matching color information can only be oriented by axes of gyration
    @param  assy_object - a dictionary of the parameters of the assembly object
    @param candidates - a list of part name that fit this assembly object without color
                        properties
    @param info_dict - dictionary of parameters for all parts (indexed by part names)                    
    @return dictionary partName -> list of colors (as 3-tuples)
    """
    colored_candidates={}
    if  candidates:
        try:
            assy_color_center_area = assy_object["colorCenters"]
        except:
            print ("colorMatchCandidate(), assy_object = ",assy_object)
            assy_color_center_area = {}
        cand_matches=[]
        for candidate in candidates:
            matched_colors=[]
            info_cand= info_dict[candidate][0] # only first solid in a part
#            print ("info_cand=",info_cand)
            for color in assy_color_center_area:
                assy_area= assy_color_center_area[color]["area"]
#                print ("color: %s, assy_area = %f"%(str(color), assy_area))
                try:
                    part_area = info_cand ["colorCenters"][color]["area"]
#                    print ("color: %s, part_area = %f"%(str(color), part_area))
                    if abs(part_area - assy_area) < precision * assy_area:
                        matched_colors.append(color)
                except:
                    pass
            cand_matches.append(matched_colors)
        max_match = max([len(a) for a in cand_matches])
        for candidate, colors in zip(candidates,cand_matches):
            if len(colors) == max_match:
                colored_candidates[candidate]=colors
    return colored_candidates

def findComponents(assembly,
                   precision_area =   PRECISION_AREA,
                   precision_volume = PRECISION_VOLUME,
                   precision_gyration = PRECISION_GYRATION,
                   precision_inside = PRECISION_INSIDE,
                   precision =        PRECISION,
                   show_best =        True):
    """
    Match each assembly element with a part, provide the transformation matrix
    @param assembly - may be file path (different treatment for Gui/no-Gui, Shape or doc.Objects or "" - will use ActiveDocument().Objects
    @param precision_area =   PRECISION_AREA - relative precision in surface area calculations
    @param precision_volume = PRECISION_VOLUME - relative precision in volume calculations
    @param precision_gyration = PRECISION_GYRATION - relative precision in radius of gyration calculations
    @param precision_inside = PRECISION_INSIDE - relative precision in calculations of point inside/outside of a solid
    @param precision =        PRECISION - precision in vector calculation
    @param show_best - calculate and show the best relative match for each parameter - can be used to fine-tune PRECISION* parameters
    @return a dictionary with 4 fields (each list value has the same number of elements):
                              'solids' - a list of solids in the assembly
                              'objects' - a list of solid properties (as dictionaries) used for identification
                              'candidates' - a list of candidate parts dictionaries, containing lists of matched colors
                              'transformation' - a list of dictionaries of transformations, indexed by part names (normally just one element)
    The same return dictionary is saved as a global variable COMPONENTS and is available as getComponents() method                           
    """
    FreeCAD.Console.PrintMessage("findComponents(): Getting parts database, assembly = %s\n"%(assembly));
    print("findComponents(): Getting parts database-\n");
    global COMPONENTS
    start_time=time.time()
    print("Getting parts database-\n")
    info_dict = get_info_files()
    FreeCAD.Console.PrintMessage("findComponents(): Got parts database\n");
    print("findComponents(): Got parts database, assembly=",assembly,"\n")
    aname = ""
    if not assembly: # including "" string
        assembly = FreeCAD.activeDocument().Objects
        FreeCAD.Console.PrintMessage("Using %d solids in the active document @%f"%(len(assembly), time.time()-start_time));
    if isinstance (assembly, (bytes,str)):
        assembly_path = assembly
        aname,_ =  os.path.splitext(os.path.basename(assembly_path))
        if not "Gui" in dir(FreeCAD):
            print("Reading assembly file %s @%f"%(assembly_path, time.time()-start_time), end="...")
            assembly = Part.read(assembly_path)
            print(" got %d solids @%f"%(len(assembly.Solids), time.time()-start_time))
        else:    
            FreeCAD.Console.PrintMessage("Using STEP file assembly %s @%f"%(assembly_path, time.time()-start_time));
            FreeCAD.loadFile(assembly_path)
            doc = FreeCAD.activeDocument()
            doc.Label = aname
            print(" got %d objects @%f"%(len(doc.Objects), time.time()-start_time))
            assembly = doc.Objects
            FreeCAD.Console.PrintMessage(" got %d solids @%f\n"%(len(assembly), time.time()-start_time));
    # assuming assembly is doc.Objects
    if isinstance(assembly,Part.Shape):    
        FreeCAD.Console.PrintMessage("Using provided objects @%f"%(len(assembly.Solids), time.time()-start_time));
        objects,solids = create_file_info_nogui(shape, aname)
#        shape = assembly
    else:
        print("GUI mode: assembly=",assembly) # [<Part::PartFeature>]
        objects,solids = create_file_info(assembly, aname)
        print("GUI mode: objects=",objects)
        print("GUI mode: solids=",solids)
        
    show_best = True #FIXME: debugging
    
#    print (objects)
    progress_bar = Base.ProgressIndicator()
    progress_bar.start("Looking for matching parts for each of the assembly element ...", len(objects))
    FreeCAD.Console.PrintMessage("Looking for matching parts for each of the assembly element %d\n"%(len(objects)));
    candidates=[]
    for i,o in enumerate(objects):
#        try:
#            FreeCADGui.updateGui()
#        except:
#            pass
        print (i,o)
        this_candidates = []
        list_errors=[]
        rg=o['principal']['RadiusOfGyration']
        rg_av = math.sqrt(rg[0]**2 + rg[1]**2 + rg[2]**2)
        rgp = precision_gyration * rg_av
        vp = o['volume']*precision_volume
        ap = o['area']*precision_area
        for n in info_dict:
            co = info_dict[n][0]
            errors = (abs(o['volume'] - co['volume']),
                      abs(o['area'] -   co['area']),
                      abs(rg[0] -       co['principal']['RadiusOfGyration'][0]),
                      abs(rg[1] -       co['principal']['RadiusOfGyration'][1]),
                      abs(rg[2] -       co['principal']['RadiusOfGyration'][2]),
                      )
            if show_best:
                list_errors.append(errors)

            if ((errors[0] < vp) and
                (errors[1] < ap) and
                (errors[2] < rgp) and
                (errors[3] < rgp) and
                (errors[4] < rgp)):
                this_candidates.append(n)
        if show_best:
            weighted_errors = [errors[0]/vp + errors[1]/ap + (errors[2] + errors[3] + errors[4])/rgp for errors in list_errors]
            best_index = weighted_errors.index(min(weighted_errors))
            errors = list_errors[best_index]
            print ("Best match with %s, relative errors: dV=%f, dS=%f, dRG1=%f, dRG2=%f, dRG3=%f"%(
                                                                                list(info_dict.keys())[best_index],
                                                                                errors[0]/o['volume'],
                                                                                errors[1]/o['area'],
                                                                                errors[2]/rg_av,
                                                                                errors[3]/rg_av,
                                                                                errors[4]/rg_av))
        print ("this_candidates=",this_candidates)
        # Filter candidates by number of color areas matched
        colored_candidates=colorMatchCandidate(o, this_candidates, info_dict, precision_area)
        try:
            num_ass_obj_colors = len(o["colorCenters"])
        except:
            num_ass_obj_colors = 0
        print ("%d :colors: %d candidates: %s, colored_candidates: %s"%(i,num_ass_obj_colors, str(this_candidates), str(colored_candidates)))
        candidates.append(colored_candidates)
        progress_bar.next() # True) # True - enable ESC to abort

    progress_bar.stop()
    transformations = findPartsTransformations(solids, objects, candidates, info_dict, precision_inside, precision)
    #Each part can be in two orientations - check overlap after loading actual parts
    COMPONENTS = {"solids":solids,"objects":objects,"candidates":candidates,"transformations":transformations}
    FreeCAD.Console.PrintMessage("DONE looking for matching parts for each of the assembly element\n");
    return COMPONENTS
#    return {"solids":solids,"objects":objects,"candidates":candidates,"transformations":transformations}
def getComponents():
    """
    @return global COMPONENTS directory, set by findComponents()
    """
    return COMPONENTS


def ppToMatrix(pp,
               center =      (0,0,0),
               colorCenters = {}, # should have all the colors in a colors list "by design"
               colors =       [],
               orient  =      0,
               precision =    PRECISION): 
    """
    Generates object transformation matix (used for parts and assembly objects) including center of volume translation
    and rotational axes (ortho-normal). The axes selection is base on the off-center colored components (centers of same
    colored faces) and gyration axes. The 'color' axes have precedence, gyration ones are added when the color ones are
    insufficient. First axis is selected as being the longest, second - as having largest component perpendicular to the
    first, and the third is just a common perpendicular to the first two. Gyration axes do not provide sign, so for
    asymmetrical object with 3 different gyration radii there could be 4 different orientations having the same inertial
    properties 
    
    @param pp - PrincipalProperties (including gyration axes)
    @param center - Center of volume
    @param colorCenters - dictionary indexed by colors, having center of color and area of each color (not used here)
    @param colors - list of matched colors (tuples)
    @param orient - 2-bit modifier for first and second axis of inertia (bit 0 - sign of the first axis, bit 1 - sign of the second)
                    orient will be overridden if there are some color vectors that define orientation
    @param precision - multiplier for the radius of gyration to compare with color vectors 
    @return 4x4 transformation matrix 
    """
    rg= pp['RadiusOfGyration']
    eps=math.sqrt(rg[0]**2 + rg[1]**2 + rg[2]**2) * precision
    color_vectors = []
    t =  FreeCAD.Vector(center)
    vectors=[]
    for color in colors:
##        print ("colorCenters=", colorCenters[color]['center']," area=",colorCenters[color]['area'])        
        color_vectors.append(FreeCAD.Vector(colorCenters[color]['center']) - t)
    print ("color_vectors=",color_vectors)        
##    print ("color_vectors=",color_vectors, "t=",t)        
    if color_vectors: # find the longest one
        lengths = [v.Length for v in color_vectors]
        l = max(lengths)
        v = color_vectors.pop(lengths.index(l))
        if l > eps:
            vectors.append(v.normalize())
    
    if vectors and color_vectors: # now find the vector having maximal orthogonal component to v[0]
        lengths = [v.cross(vectors[0]).Length for v in color_vectors]
        l = max(lengths)
        v = color_vectors.pop(lengths.index(l))
        if l > eps:
            vectors.append(v.normalize())
#    print ("vectors=",vectors)        
    #use gyro axis (or two of them)
    if len(vectors) < 3: #insufficient color vectors                
        vgyro=[FreeCAD.Vector(pp["FirstAxisOfInertia"]),
               FreeCAD.Vector(pp["SecondAxisOfInertia"]),
               FreeCAD.Vector(pp["ThirdAxisOfInertia"])]
        if (orient & 1 ) :
            vgyro[0].multiply(-1.0)        
        if (orient & 2 ) :
            vgyro[1].multiply(-1.0)        
        if vgyro[2].dot(vgyro[0].cross(vgyro[1])) < 0 :
            vgyro[2].multiply(-1.0)
##        print ("vgyro=", vgyro)        
        if not vectors:
            vectors = [vgyro[0], vgyro[1], vgyro[2]]
        else: # at least one vector is defined from colors, need one more
            new_directions = [False,False,False]
            new_length = len(vectors)
            if len(vectors) < 2: # == 1, need one more
##                print ("vgyro=",vgyro)        
                for i in range(3): # filter parallel to existing
                    for v in vectors:
                        if v.cross(vgyro[i]).Length < eps:
                            break
                    else:
                        new_directions[i] = True
                        new_length += 1
##                print ("new_directions=",new_directions," new_length=",new_length)        
                if new_length > 2: # extras, filter more (perpendicular to axis of symmetry)
                    if (new_directions[0] or new_directions[1]) and ((rg[0] - rg[1]) < eps):
                        if new_directions[1]:
                            new_directions[1] = False
                            new_length -= 1
                        if new_directions[0] and (new_length > 2):
                            new_directions[0] = False
                            new_length -= 1
                    if (new_length > 2) and (new_directions[1] or new_directions[2]) and ((rg[1] - rg[2]) < eps):
                        if new_directions[1]:
                            new_directions[1] = False
                            new_length -= 1
                        if new_directions[2] and (new_length > 3):
                            new_directions[2] = False
                            new_length -= 1
##                print ("new_directions=",new_directions," new_length=",new_length)        
            
                # All good, add 1,2,3-rd and make ortho-normal
                if len(vectors) < 2:
                    i = new_directions.index(True)        
                    vectors.append((vgyro[i] - vectors[0] * vectors[0].dot(vgyro[i])).normalize())
            # here we have 2 vectors, make a third
            vectors=[vectors[0],vectors[1], vectors[0].cross(vectors[1]).normalize()]
            
    if vectors[2].dot(vectors[0].cross(vectors[1])) < 0 :
        vectors[2].multiply(-1.0)
#    print ("Final vectors=",vectors)        
                
    return  FreeCAD.Matrix(vectors[0].x, vectors[1].x, vectors[2].x, t.x,
                           vectors[0].y, vectors[1].y, vectors[2].y, t.y,
                           vectors[0].z, vectors[1].z, vectors[2].z, t.z,
                           0.0,          0.0,          0.0,          1.0)

def list_parts_offsets():
    """
    Shows center of volume distance from (0,0,0) for each part. It may be beneficial
    to re-export STEP models from CAD if the offset is very large to increase the
    precision of calculations.
    Builds the parts info files if not available/obsolete
    @return ordered list of (part_name, offset) tuples, in descending order of offsets 
    """
    info_files = get_info_files()
    parts_offsets=[]
    for i, name in enumerate(info_files):
        for j,o in enumerate(info_files[name]):
            d = math.sqrt(o["center"][0]**2 + o["center"][1]**2 + o["center"][2]**2)
            if j == 0:
                print("%4d:"%(i), end="")
                parts_offsets.append((name, d))    

            else:
                print("     ", end="")
            print("%s offset = %6.1f"%(name, d))
    # now sort:
    parts_offsets =  sorted(parts_offsets, key=lambda offs: -offs[1])
    print ("\nSorted:")
    for o in parts_offsets:
        print ("%s: %f"%(o))
    return parts_offsets
    
    
def list_parts():
    """
    Output each part information to console/log file
    """
    info_files = get_info_files()
    for i, name in enumerate(info_files):
        print ("%4d '%s': %d solids:%s"%(i,name,len(info_files[name]),str(info_files[name])))

def getShapeNode(vertices, faces, diffuseColor = None, main_color_index = 0, colorPerVertex = False):
    """
    Build a node for the tesselated mesh data 
    @param vertices: list of vertice coordinates as `Vector` type
    @param faces: list of tuples of vertice indices and optionally a face color index ex: (1, 2, 3) or (1, 2, 3, 0)
    @param diffuseColor: None or a list with 3*N color component values in the form of [R, G, B, R1, G1, B1, ...]
           If only 3 color components are specified, they are applied to the whole shape, otherwise each vertex
           (or face) is assigned color from the face color index
    @param main_color_index - in multi-color object this index sets the color of the object
    @param colorPerVertex - True: specify color per erach vertex, False - for each face (reduces file size)
    @return XML node for the whole shape to be inserted in the X3D file    
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

def exportX3D(objects, filepath,  partName="", bbox = None, colorPerVertex=False):
    """
    Export given list of objects to a X3D file.
    @param objects - a list of dictionaries in the following format:
            {
                points : [Vector, Vector...],
                faces : [(pi, pi, pi, ci), ...],    # pi: point index, ci - color index (optional)
                color : [R, G, B,...]            # number range is 0-1.0, exactly 3 elements for a single color, 3*N for per-vertex colors
            }
    @param filepath - os path of the file to save X3D data
    @param id - id set for the X3D Group node wrapping all the objects in the file
    @param bbox - optional bound box as a dictionary {'center':(xc,yc,zc), size:(xs,ys,zs)}

    @param colorPerVertex - True: specify color per erach vertex, False - for each face (reduces file size)
    """
    
    progress_bar = Base.ProgressIndicator()
    progress_bar.start("Saving objects to X3D file %s ..."%(filepath), len(objects))

    x3dNode = et.Element('x3d')
    x3dNode.set('profile', 'Interchange')
    x3dNode.set('version', '3.3')
    sceneNode = et.SubElement(x3dNode, 'Scene')
    transformNode =et.SubElement(sceneNode, 'Transform') # Empty transform to adjust center for offset models (use bboxCenter)
    transformNode.set('id', 'transformTop_'+partName)
    transformNode.set('class', 'transformTop_'+partName)
#    if bbox:
#        transformNode.set('translation','%f %f %f'%(-bbox['center'][0],-bbox['center'][1],-bbox['center'][2]))
#    else:    
    transformNode.set('translation','%f %f %f'%(0,0,0))
    transformNode.set('rotation','%f %f %f %f'%(0,0,0,0))
    
    groupNode = et.SubElement(transformNode, 'Group')
    groupNode.set('id', 'groupTop_'+partName)
    groupNode.set('class', 'groupTop_'+partName)
    if bbox:
        groupNode.set('bboxSize','%f %f %f'%bbox['size'])
        groupNode.set('bboxCenter','%f %f %f'%bbox['center'])

    for o in objects:
        shapeNode = getShapeNode(o["points"], o["faces"], o["color"], o["main_color_index"], colorPerVertex)
        groupNode.append(shapeNode)
        progress_bar.next() # True) # True - enable ESC to abort
        
    oneliner= et.tostring(x3dNode)
    reparsed = minidom.parseString(oneliner)

#    with open(filepath, "wr") as f:
    with open(filepath, "w") as f:
        f.write(reparsed.toprettyxml(indent="  "))
    progress_bar.stop()

def prepareX3dExport(freecadObjects, fname=""):
    """
    Convert object geometry (including color that is separate in FreeCAD) for exporting to X3D,
    tessellate faces to traingles
    @param freecadObjects - a list of FreeCAD objects
    @param fname - file name/path used for the progress bar indicator
    @return a list of dictionaries in the following format:
            {
                points : [Vector, Vector...],
                faces : [(pi, pi, pi, ci), ...],    # pi: point index, ci - color index (optional)
                color : [R, G, B,...]            # number range is 0-1.0, exactly 3 elements for a single color, 3*N for per-vertex colors
            }
    """
    objects = []
    progress_bar = Base.ProgressIndicator()
    txt=""
    if fname:
        txt += " in "+fname
    progress_bar.start("Generating objects%s to export to X3D ..."%(txt), len(freecadObjects))
    xyzMin=None
    xyzMax=None
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
                        color_index = col_dict[o.ViewObject.DiffuseColor[i]] #sometimes len(o.ViewObject.DiffuseColor[i]) ==1, but it will not get here 
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

def generatePartsX3d(dir_list = [STEP_PARTS], colorPerVertex = COLOR_PER_VERTEX):
    """
    Convert all parts to X3D, skipping already converted ones, processing only
    non-existing or obsolete (older than the source STEP models)
    @param dir_list - a list of directories to look for STEP models
    @param colorPerVertex - True: specify color per erach vertex, False - for each face (reduces file size)
    """
    start_time=time.time()
    info_dict= get_info_files(dir_list) # Will (re-) build info files if missing
    step_list = get_step_list(dir_list) # now absolute, not relative to ROOT_DIR
    if not X3D_DIR in os.listdir(ROOT_DIR):
        os.mkdir(os.path.join(ROOT_DIR,X3D_DIR))
    numExported=0    
    for step_file in step_list:
        partName,_ =  os.path.splitext(os.path.basename(step_file))
        x3dFile = os.path.join(ROOT_DIR,X3D_DIR,partName + X3D_EXT)
        if (not os.path.isfile(x3dFile)) or (os.path.getmtime(step_file) > os.path.getmtime(x3dFile)):
            # Prepare data
            FreeCAD.loadFile(step_file) # os.path.join(ROOT_DIR,step_file))
            doc = FreeCAD.activeDocument()
            doc.Label = partName
            
            x3d_objects = prepareX3dExport(doc.Objects, step_file) # step_file needed just for progress bar
            bboxX3d= bBoxToX3d(getBoundBox(doc.Objects))
            exportX3D(x3d_objects, x3dFile, partName = partName, bbox = bboxX3d, colorPerVertex=colorPerVertex)
            FreeCAD.closeDocument(doc.Name)
            FreeCADGui.updateGui()
            numExported += 1
    print("Exported %d files as X3D in @%f seconds, "%(numExported, time.time()-start_time))
    
def matrix4ToX3D(m, eps=0.000001): #assuming 3x3 matrix is pure rotational
    """
    Convert FreeCAD 4x4 transformation matrix to X3D representation
    (translation and rotation by the specified angle around the specified axis
    @param m - 4x4 transformation matrix
    @return a dictionary of two elements: "translation" having a value of a 3-element tuple (x,y,z)
            and  "rotation" as a 4-element tuple (axis and angle)
    """
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



def generateAssemblyX3d(assembly_path,
                        components =         None,
                        dir_list =           [STEP_PARTS],
                        colorPerVertex =     COLOR_PER_VERTEX,
                        precision_area =     PRECISION_AREA,
                        precision_volume =   PRECISION_VOLUME,
                        precision_gyration = PRECISION_GYRATION,
                        precision_inside =   PRECISION_INSIDE,
                        precision =          PRECISION
                        ):
    """
    Generate X3D file for the assembly and the parts (if they are not yet converted)
    @param assembly_path - may be file path (different treatment for Gui/no-Gui, Shape or doc.Objects or "" - will
                           use ActiveDocument().Objects
    @param components a dictionary as generated by findComponents() or None - in that case the rather long search for
                      parts/transformations. If it is provided (or the global COMPONENTS dictionary is defined) this
                      method just generates x3d files from the prepared data
    @param colorPerVertex - True: specify color per erach vertex, False - for each face (reduces file size)
    @param precision_area =   PRECISION_AREA - relative precision in surface area calculations
    @param precision_volume = PRECISION_VOLUME - relative precision in volume calculations
    @param precision_gyration = PRECISION_GYRATION - relative precision in radius of gyration calculations
    @param precision_inside = PRECISION_INSIDE - relative precision in calculations of point inside/outside of a solid
    @param precision =        PRECISION - precision in vector calculation

    @return a dictionary with 4 fields (each list value has the same number of elements):
                              'solids' - a list of solids in the assembly
                              'objects' - a list of solid properties (as dictionaries) used for identification
                              'candidates' - a list of candidate parts dictionaries, containing lists of matched colors
                              'transformation' - a list of dictionaries of transformations, indexed by part names (normally just one element)
    The same return dictionary is saved as a global variable COMPONENTS and is available as getComponents() method                           
    """
    
    start_time=time.time()
    info_dict = get_info_files(dir_list) # Will (re-) build info files if missing
#    FreeCAD.Console.PrintMessage("generateAssemblyX3d()");
    generatePartsX3d(dir_list = [STEP_PARTS], colorPerVertex = COLOR_PER_VERTEX) # Will only run if files are not there yet
    FreeCAD.Console.PrintMessage("generatePartsX3d() Done\n");
    print("generatePartsX3d() Done");
    if not components:
        components = COMPONENTS # try to use global ones
    if not components: # COMPONETS do not exist either - rebuild them
        components = findComponents(assembly_path, # None is OK here
                                    precision_area =     precision_area,
                                    precision_volume =   precision_volume,
                                    precision_gyration = precision_gyration,
                                    precision_inside =   precision_inside,
                                    precision =          precision,
                                    show_best =          False)

    if assembly_path:    
        assName,_ =  os.path.splitext(os.path.basename(assembly_path))
    else:
        assName= FreeCAD.activeDocument().Objects[0].Label
    FreeCAD.Console.PrintMessage("findComponents() Done, ass_name=%s\n"%(assName));
    ass_with_suffix = assName
    if not ass_with_suffix.endswith(ASSEMBLY_SUFFIX):
        ass_with_suffix = assName + ASSEMBLY_SUFFIX       
    FreeCAD.Console.PrintMessage("ass_with_suffix=%s\n"%(ass_with_suffix));
    x3dFile = os.path.join(ROOT_DIR,X3D_DIR, ass_with_suffix + X3D_EXT) # currently in the same directory as parts
    x3dNode = et.Element('x3d')
    x3dNode.set('profile', 'Interchange')
    x3dNode.set('version', '3.3')
    sceneNode = et.SubElement(x3dNode, 'Scene')
    # Including file with (manually created)  NavInfo, Cameras, etc that should not be overwritten when regenerating assembly model
    inlineNode = et.SubElement(sceneNode, 'Inline')
    inlineNode.set('id', ass_with_suffix + '_config')
    inlineNode.set('url',ass_with_suffix + '_config'+ X3D_EXT)
    inlineNode.set('nameSpaceName', ass_with_suffix )
    #empty Transform node to move/rotate the whole assembly now translation to -(bounding box center)
    bboxX3d= bBoxToX3d(getBoundBox(components['solids']))
    transformNode = et.SubElement(sceneNode, 'Transform')
    transformNode.set('id','transformTop_'+ass_with_suffix)
    transformNode.set('class','transformTop_'+ass_with_suffix)
#    if bboxX3d:
#        transformNode.set('translation','%f %f %f'%(-bboxX3d['center'][0],-bboxX3d['center'][1],-bboxX3d['center'][2]))
#    else:    
    transformNode.set('translation','%f %f %f'%(0,0,0))
    
    transformNode.set('rotation','%f %f %f %f'%(0,0,0,0))
    #Group node to provide a bbox center/size of the whole assembly (and center the view)
    modelNode = et.SubElement(transformNode, 'Group')
    modelNode.set('id','groupTop_'+ass_with_suffix)
    modelNode.set('class','groupTop_'+ass_with_suffix)
    if bboxX3d:
        modelNode.set('bboxSize','%f %f %f'%bboxX3d['size'])
        modelNode.set('bboxCenter','%f %f %f'%bboxX3d['center'])

    defined_parts = {} # for each defined part holds index (for ID generation)
    #TODO: Reorder parts - smallest (by a product og gyration radii) first
    volumes=[]
    for i, component in enumerate(components['objects']):
        rg=component['principal']['RadiusOfGyration']
        volumes.append((i,rg[0]*rg[1]*rg[2]))
    volumes=sorted(volumes,key= lambda t: t[1])    
    FreeCAD.Console.PrintMessage("Generating x3d %d volumes\n"%(len(volumes))) # OK
#    for i, component in enumerate(components['objects']):
    for i, _ in volumes:
        transformations = components['transformations'][i] # same structure as candidates, missing - {}'None'
        if not transformations:
            print("Component %d does not have any matches, ignoring. Candidates: %s"%(i,str(components['candidates'][i])))
            FreeCAD.Console.PrintMessage("Component %d does not have any matches, ignoring. Candidates: %s\n"%(i,str(components['candidates'][i])))
            continue
        part = list(transformations.keys())[0]
        # rename part if there is the same one with ASSEMBLY_SUFFIX
        part_name = part
        if ASSEMBLY_SUFFIX and os.path.isfile( os.path.join(ROOT_DIR, X3D_DIR, part + ASSEMBLY_SUFFIX + X3D_EXT)) :
            part_name = part + ASSEMBLY_SUFFIX
        
        transformation = transformations[part]    
        bbox= bBoxToX3d(components['solids'][i].BoundBox)

        transform = matrix4ToX3D(transformation)
        rot=transform['rotation']
        print("%d: Adding %s, rotation = (x=%f y=%f z=%f theta=%f)"%(i,part,rot[0],rot[1],rot[2],rot[3]))
        FreeCAD.Console.PrintMessage("%d: Adding %s, rotation = (x=%f y=%f z=%f theta=%f)"%(i,part,rot[0],rot[1],rot[2],rot[3]))
        if part in defined_parts:
            defined_parts[part] += 1
        else:
            defined_parts[part] = 0
        switchNode = et.SubElement(modelNode, 'Switch')
        switchNode.set('id','switch_'+part_name+":"+str(defined_parts[part]))
        switchNode.set('class','switch_'+part_name)
        switchNode.set('whichChoice','0')
        transformNode = et.SubElement(switchNode, 'Transform')
        transformNode.set('id','transform_'+part_name+":"+str(defined_parts[part]))
        transformNode.set('class','transform_'+part_name)
        transformNode.set('translation','%f %f %f'%transform['translation'])
        transformNode.set('rotation','%f %f %f %f'%transform['rotation'])
        groupNode = et.SubElement(transformNode, 'Group')
        groupNode.set('id','group_'+part_name+":"+str(defined_parts[part]))
        groupNode.set('class','group_'+part_name)
        groupNode.set('bboxSize','%f %f %f'%bbox['size'])
        groupNode.set('bboxCenter','%f %f %f'%bbox['center'])

        if defined_parts[part]:
            groupNode.set('USE', part_name)
        else:
            groupNode.set('DEF', part_name)
            inlineNode = et.SubElement(groupNode, 'Inline')
            inlineNode.set('id','inline_'+part_name+":"+str(defined_parts[part]))
            inlineNode.set('class','inline_'+part_name)
#            inlineNode.set('url',os.path.join(X3D_DIR,part_name + X3D_EXT))
            inlineNode.set('url',part_name + X3D_EXT)
            inlineNode.set('nameSpaceName',part_name)
    oneliner= et.tostring(x3dNode)
    reparsed = minidom.parseString(oneliner)
    print ("Writing assembly to %s"%(x3dFile))
#    with open(x3dFile, "wr") as f:
    with open(x3dFile, "w") as f:
        f.write(reparsed.toprettyxml(indent="  "))
    print("Assembly %s exported as X3D file in @%f seconds, "%(x3dFile, time.time()-start_time))
    FreeCAD.Console.PrintMessage("Assembly %s exported as X3D file in @%f seconds\n"%(x3dFile, time.time()-start_time));

    return components

def showFailedComponents(components = None):
    """
    Shows failed components - assembly elements for which the program could not find parts+transformations by
    adding them to the FreeCAD document that contains assembly. All other solids are hidden (visibility is set
    to False) so the added ones are easier visible. In many cases these missing components do not constitute a
    problem as they match to other (non-primary) components of the STEP part files (current software only uses
    the primary (largest by volume) solid of each part file for identification.
    @param components - a dictionary of lists as defined in findComponents() description
    """
    if components is None:
        components = COMPONENTS
    FreeCADGui.SendMsgToActiveView("ViewFit")
    doc=FreeCAD.activeDocument()
    for o in doc.Objects:
        o.ViewObject.Visibility = False # turn off  normal objects
    print (components)
    print (COMPONENTS)
    for i, s in enumerate(components['solids']):
        if not components['transformations'][i]:
            doc.addObject("Part::Feature","missing_%d"%i).Shape = s
def getBOM(components = None):
    """
    Build a Bill of Materials (parts list) for the assembly
    @param components - a dictionary of lists as defined in findComponents() description
    @return an list of pairs - tuples (part_name, number_of_instances), ordered by the part names
    """
    if components is None:
        components = COMPONENTS
    if not components:
        return None
    d={}
    for t in components['transformations']:
        if t:
            if len(t) >1:
                print ("***** WARNING: Multiple candidate parts for the same assembly element: %s"%(str(t)))
            pn = list(t.keys())[0] # in unlikely case of multiple candidates use the first one
            if pn in d:
                d[pn] += 1
            else:
                d[pn] = 1
    bom = sorted(d.items(), key = lambda t:t[0])
    print("\nParts List:")
    for i, p in enumerate(bom):
        print ("%3d: %s %2d"%(i,p[0],p[1]))
    return bom    

#X3dStepAssyDialog
########################################################################
class X3dStepAssyDialog(QtGui.QWidget):
    """"""
    assembly_path =   ""
    x3d_root_path =   ""
    step_parts_path = ""
    log_file =        ""
    assembly_suffix = ""
    
    precision =          0.0001
    precision_area =     0.001
    precision_volume =   0.001
    precision_gyration = 0.001
    precision_inside =   0.03
    
    textWindows=[]
    class TextViewerWindow(QtGui.QWidget):
        """"""
        dir = ""
        isHTML = False 
        #----------------------------------------------------------------------
        def __init__(self, text_to_show, title, geometry=(50,50,400,800), rd0nly=False, isHTML=False, dir=""):
            self.dir = dir
            self.isHTML = isHTML
            """Constructor"""
            QtGui.QWidget.__init__(self)
            

            self.setWindowTitle(title)
            self.setGeometry(*geometry)
            
            self.text_editor = QtGui.QTextEdit(self)
            if self.isHTML:
                self.text_editor.setHtml(text_to_show)
            else:
                self.text_editor.setText(text_to_show)
            self.text_editor.setReadOnly(rd0nly)
     
            saveButton = QtGui.QPushButton('Save')
            saveButton.clicked.connect(self.openSaveFileDialog)

            printButton = QtGui.QPushButton('Print')
            printButton.clicked.connect(self.onPrint)
            
            printPreviewButton = QtGui.QPushButton('Preview Print')
            printPreviewButton.clicked.connect(self.onPrintPreview)
     
            btnLayout = QtGui.QHBoxLayout()
            mainLayout = QtGui.QVBoxLayout()
     
            btnLayout.addWidget(saveButton)
            btnLayout.addWidget(printButton)
            btnLayout.addWidget(printPreviewButton)
            mainLayout.addWidget(self.text_editor)
            mainLayout.addLayout(btnLayout)
            self.setLayout(mainLayout)
     
        #----------------------------------------------------------------------
        def onPrint(self):
            """
            Create and show the print dialog
            """
            dialog = QtGui.QPrintDialog()
            if dialog.exec_() == QtGui.QDialog.Accepted:
                doc = self.text_editor.document()
                doc.print_(dialog.printer())
     
        #----------------------------------------------------------------------
        def onPrintPreview(self):
            """
            Create and show a print preview window
            """
            dialog = QtGui.QPrintPreviewDialog()
            dialog.paintRequested.connect(self.text_editor.print_)
            dialog.exec_()        

        #----------------------------------------------------------------------
        def openSaveFileDialog(self):
            path, _ = QtGui.QFileDialog.getSaveFileName(self, "Save File", self.dir)
            if path:
                with open (path, 'w') as f:
                    if self.isHTML:
                        f.write(self.text_editor.toHtml())
                    else:    
                        f.write(self.text_editor.toPlainText())
    

    #----------------------------------------------------------------------
    def get_path_text(self, path, mode = None):
        if path:
            return path
        if mode == "assy":
            return "Active FreeCAD document"
        elif mode == "log":
            return "stdout"
        else:
            return "not set"
                 
    def saveSettings(self):
        config = ConfigParser()
        config.read(CONFIG_PATH) # OK not to have any file
        try:
            config.add_section('paths')
        except:
            pass # OK if the section already exists    
        config.set('paths', 'assembly_path',   self.assembly_path)
        config.set('paths', 'x3d_root_path',   self.x3d_root_path)
        config.set('paths', 'step_parts_path', self.step_parts_path)
        config.set('paths', 'log_file',        self.log_file)
        config.set('paths', 'assembly_suffix', self.assembly_suffix)
        try:
            config.add_section('precisions')
        except:
            pass # OK if the section already exists    
        config.set('precisions', 'precision',          '%f'%(self.precision))
        config.set('precisions', 'precision_area',     '%f'%(self.precision_area))
        config.set('precisions', 'precision_volume',   '%f'%(self.precision_volume))
        config.set('precisions', 'precision_gyration', '%f'%(self.precision_gyration))
        config.set('precisions', 'precision_inside',   '%f'%(self.precision_inside))
        with open(CONFIG_PATH, 'w') as f:
            config.write(f)
    def restoreSettings(self):
        config = ConfigParser()
        config.read(CONFIG_PATH) # OK not to have any file
        try:
            self.assembly_path =   config.get('paths', 'assembly_path')
        except:
            self.assembly_path =   ASSEMBLY_PATH
        try:         
            self.x3d_root_path =   config.get('paths', 'x3d_root_path')
        except:
            self.x3d_root_path =   ROOT_DIR
        try:            
            self.step_parts_path = config.get('paths', 'step_parts_path')
        except:
            self.step_parts_path = STEP_PARTS
        try:     
            self.log_file =        config.get('paths', 'log_file')
        except:
            self.log_file =        ""
        try:     
            self.assembly_suffix = config.get('paths', 'assembly_suffix' )
        except:
            self.assembly_suffix =  ASSEMBLY_SUFFIX
        try:     
            self.precision=          float(config.get('precisions', 'precision'))
        except:
            self.precision=          PRECISION
        try:     
            self.precision_area=     float(config.get('precisions', 'precision_area'))
        except:
            self.precision_area=     PRECISION_AREA
        try:     
            self.precision_volume=   float(config.get('precisions', 'precision_volume'))
        except:
            self.precision_volume=   PRECISION_VOLUME
        try:     
            self.precision_gyration= float(config.get('precisions', 'precision_gyration'))
        except:
            self.precision_gyration= PRECISION_GYRATION
        try:     
            self.precision_inside=   float(config.get('precisions', 'precision_inside'))
        except:
            self.precision_inside=   PRECISION_INSIDE

    def __init__(self):
        self.restoreSettings()
        """Constructor"""
        QtGui.QWidget.__init__(self) # ,parent=parent)
 
        self.label = QtGui.QLabel("Python rules!")
 
        # create the buttons

        label_log_file =      QtGui.QLabel("Log file")
        self.log_file_btn =   QtGui.QPushButton(self.get_path_text(self.log_file, "log"))
        self.log_file_btn.setToolTip("Select log file for 'print' operators. Will be reset when starting macro execution")
        
        label_assembly =      QtGui.QLabel("Assembly to process")
        self.assembly_btn =   QtGui.QPushButton(self.get_path_text(self.assembly_path, "assy"))
        self.assembly_btn.setToolTip("Select assembly STEP model, if none is selected the active FreeCAD document will be used")
        label_x3d_root_btn =  QtGui.QLabel("Working directory")
        self.x3d_root_btn =   QtGui.QPushButton(self.get_path_text(self.x3d_root_path))
        self.x3d_root_btn.setToolTip("'info' and 'x3d' directories will be created/updated under the selected directory")
        label_step_parts =    QtGui.QLabel("Step parts directory")
        self.step_parts_btn = QtGui.QPushButton(self.get_path_text(self.step_parts_path))
        self.step_parts_btn.setToolTip("Select directory containing all the parts STEP models. Will scan sub-directories")

        label_assembly_suffix =           QtGui.QLabel("Assembly suffix")
        self.lineedit_assembly_suffix =   QtGui.QLineEdit()
        self.lineedit_assembly_suffix.setText  (self.assembly_suffix)
        self.lineedit_assembly_suffix.setToolTip("Add this suffix to the assembly name when generating X3D, inline files with such suffix instead of the base ones")
        
        self.help_btn =       QtGui.QPushButton("?")
        self.help_btn.setToolTip("Show description of this program")
        self.execute_btn  =   QtGui.QPushButton("Convert")
        self.execute_btn.setToolTip("Build X3D models for the parts (if needed) and the assembly. May take hours!")
        self.offsets_btn  =   QtGui.QPushButton("Parts offsets")
        self.offsets_btn.setToolTip("List part centers offsets. Keeping them small (compared to the part size) increases precision of transformations")
        self.bom_btn  =       QtGui.QPushButton("(BOM)")
        self.bom_btn.setToolTip("Bill of Materials (available after assembly conversion)")

        
        label_precision =           QtGui.QLabel("precision")
        label_precision_area =      QtGui.QLabel("precision_area")
        label_precision_volume =    QtGui.QLabel("precision_volume")
        label_precision_gyration =  QtGui.QLabel("precision_gyration")
        label_precision_inside =    QtGui.QLabel("precision_inside")

        self.lineedit_precision =          QtGui.QLineEdit()
        self.lineedit_precision_area =     QtGui.QLineEdit()
        self.lineedit_precision_volume =   QtGui.QLineEdit()
        self.lineedit_precision_gyration = QtGui.QLineEdit()
        self.lineedit_precision_inside =   QtGui.QLineEdit()
        
        self.lineedit_precision.setToolTip         ("Relative precision in matrix/vector calculations")
        self.lineedit_precision_area.setToolTip    ("Relative precision when comparing objects surface area")
        self.lineedit_precision_volume.setToolTip  ("Relative precision when comparing objects volume")
        self.lineedit_precision_gyration.setToolTip("Relative precision when comparing objects radii of gyration")
        self.lineedit_precision_inside.setToolTip  ("Relative precision when determining if part vertices fit into assembly object")

        self.lineedit_precision.setText          ('%f'%(self.precision))
        self.lineedit_precision_area.setText     ('%f'%(self.precision_area))
        self.lineedit_precision_volume.setText   ('%f'%(self.precision_volume))
        self.lineedit_precision_gyration.setText ('%f'%(self.precision_gyration))
        self.lineedit_precision_inside.setText   ('%f'%(self.precision_inside))
        

        self.log_file_btn.clicked.connect(self.selectLogFile)
        self.assembly_btn.clicked.connect(self.selectAssembly)
        self.x3d_root_btn.clicked.connect(self.selectX3dRoot)
        self.step_parts_btn.clicked.connect(self.selectStepParts)
        
        self.lineedit_assembly_suffix.editingFinished.connect  (self.editedAssemblySuffix)
        
        self.lineedit_precision.editingFinished.connect         (self.editedPrecision)
        self.lineedit_precision_area.editingFinished.connect    (self.editedPrecisionArea)
        self.lineedit_precision_volume.editingFinished.connect  (self.editedPrecisionVolume)
        self.lineedit_precision_gyration.editingFinished.connect(self.editedPrecisionGyration)
        self.lineedit_precision_inside.editingFinished.connect  (self.editedPrecisionInside)

        self.help_btn.clicked.connect(self.showHelp)
        self.execute_btn.clicked.connect(self.executeMacro)
        self.offsets_btn.clicked.connect(self.showOffsets)
        self.bom_btn.clicked.connect(self.showBOM)
 
        # layout widgets
        layout = QtGui.QGridLayout() # parent=parent)
        layout.setColumnStretch(1,1)
        layout.setColumnStretch(2,1)
        layout.setColumnStretch(3,1)
        layout.addWidget(label_assembly,                   0, 0)
        layout.addWidget(self.assembly_btn,                0, 1, 1, 3)

        layout.addWidget(label_x3d_root_btn,               1, 0)
        layout.addWidget(self.x3d_root_btn,                1, 1, 1, 3)

        layout.addWidget(label_step_parts,                 2, 0)
        layout.addWidget(self.step_parts_btn,              2, 1, 1, 3)

        layout.addWidget(label_log_file,                   3, 0)
        layout.addWidget(self.log_file_btn,                3, 1, 1, 3)
        
        layout.addWidget(label_assembly_suffix,            4, 0)
        layout.addWidget(self.lineedit_assembly_suffix,    4, 1, 1, 1)
        
        layout.addWidget(label_precision,                  5, 0)
        layout.addWidget(self.lineedit_precision,          5, 1, 1, 1)
        
        layout.addWidget(label_precision_area,             6, 0)
        layout.addWidget(self.lineedit_precision_area,     6, 1, 1, 1)
        
        layout.addWidget(label_precision_volume,           7, 0)
        layout.addWidget(self.lineedit_precision_volume,   7, 1, 1, 1)
        
        layout.addWidget(label_precision_gyration,         8, 0)
        layout.addWidget(self.lineedit_precision_gyration, 8, 1, 1, 1)
        
        layout.addWidget(label_precision_inside,           9, 0)
        layout.addWidget(self.lineedit_precision_inside,   9, 1, 1, 1)
        
        layout.addWidget(self.help_btn,                    10, 0)
        layout.addWidget(self.offsets_btn,                 10, 1)
        layout.addWidget(self.execute_btn,                 10, 2)
        layout.addWidget(self.bom_btn,                     10, 3)
        
        self.setLayout(layout)
 
        # set the position and size of the window
        self.setGeometry(100, 100, 300, 200)
 
        self.setWindowTitle("STEP assembly to X3D converter")
        FreeCAD.Console.PrintMessage("Disabling STEP compound merge in preferences/Import-Export/STEP");
#FIXME - uncomment when done. Merges STEP solid into a single grey object        
        App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import/hSTEP").SetBool('ReadShapeCompoundMode',False)
    #----------------------------------------------------------------------
    def selectLogFile(self):
        prompt_file = self.log_file
        if not prompt_file:
            prompt_file =  self.x3d_root_path
        self.log_file,_ = QtGui.QFileDialog.getSaveFileName (self,
                                                           "Select log file (or cancel to use stdout)",
                                                           prompt_file)
        self.log_file_btn.setText(self.get_path_text(self.log_file, "log"))
        self.saveSettings()
    
    
    def selectAssembly(self):
        self.assembly_path, _ = QtGui.QFileDialog.getOpenFileName(self,
                                                                  "Select assembly file (cancel to use loaded to FreeCAD)",
                                                                  self.assembly_path,
                                                                  "STEP files (*.step *.stp *.STEP *.STP)")
        self.assembly_btn.setText(self.get_path_text(self.assembly_path, True))
        self.saveSettings()
        
    def selectX3dRoot(self):
        self.x3d_root_path = QtGui.QFileDialog.getExistingDirectory(self,
                                                                    "Select working directory for STEP->x3d conversion",
                                                                     self.x3d_root_path)
        self.x3d_root_btn.setText(self.get_path_text(self.x3d_root_path))
        self.saveSettings()
    
    def selectStepParts(self):
        self.step_parts_path = QtGui.QFileDialog.getExistingDirectory(self,
                                                                    "Select working directory for STEP->x3d conversion",
                                                                     self.step_parts_path)
        self.step_parts_btn.setText(self.get_path_text(self.step_parts_path))
        self.saveSettings()
        
    def editedAssemblySuffix(self):
        self.assembly_suffix = self.lineedit_assembly_suffix.text()
        self.saveSettings()
            
    def editedPrecision(self):
        txt = self.lineedit_precision.text()
        try:
            number = float(txt)
            self.precision = number
        except Exception:
            pass
        self.lineedit_precision.setText('%f'%(self.precision))
        self.saveSettings()
        
    def editedPrecisionArea(self):
        txt = self.lineedit_precision_area.text()
        try:
            number = float(txt)
            self.precision_area = number
        except Exception:
            pass
        self.lineedit_precision_area.setText('%f'%(self.precision_area))
        self.saveSettings()
        
    def editedPrecisionVolume(self):
        txt = self.lineedit_precision_volume.text()
        try:
            number = float(txt)
            self.precision_volume = number
        except Exception:
            pass
        self.lineedit_precision_volume.setText('%f'%(self.precision_volume))
        self.saveSettings()
        
    def editedPrecisionGyration(self):
        txt = self.lineedit_precision_gyration.text()
        try:
            number = float(txt)
            self.precision_gyration = number
        except Exception:
            pass
        self.lineedit_precision_gyration.setText('%f'%(self.precision_gyration))
        self.saveSettings()
        
    def editedPrecisionInside(self):
        txt = self.lineedit_precision_inside.text()
        try:
            number = float(txt)
            self.precision_inside = number
        except Exception:
            pass
        self.lineedit_precision_inside.setText('%f'%(self.precision_inside))
        self.saveSettings()
        
        
        
        
    
    def showHelp(self):
        msg = ("<h2>LICENSE</h2>\n"
               "<p>Copyright (C) 2015, Elphel.inc.</p>\n"
               "<p>This program is free software: you can redistribute it and/or modify "
               "it under the terms of the GNU General Public License as published by "
               "the Free Software Foundation, either version 3 of the License, or "
               "(at your option) any later version.</p>\n"
               "<p>This program is distributed in the hope that it will be useful, "
               "but WITHOUT ANY WARRANTY; without even the implied warranty of "
               "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
               "GNU General Public License for more details.</p>\n"
               "<p>You should have received a copy of the GNU General Public License "
               "along with this program.  If not, see "
               "<a href='http://www.gnu.org/licenses/'>http://www.gnu.org/licenses/</a>.</p>\n"
               "<h2>DESCRIPTION</h2>\n"
               "<p>x3d_step_assy macro converts assembly CAD model to X3D. It tries to recognize "
               "individual parts (provided as STEP files) in the assembly model, converts "
               "each part to X3D and then generates assembly X3D file that includes inline "
               "references to the recognized part files, applying appropriate transformations "
               "(rotations and translations).</p>\n"
               "<p>First thing the program does is it scans all the STEP models under the "
               "specified directory and collects general properties of each file, including "
               "volume, surface area, center of mass, gyration radii and axes, as well as "
               "per-color centers. Normally each part should contain just one solid, but if "
               "there are more than one only the largest (by volume) will be used for "
               "identification in the assembly (in that case assembly may show multiple not "
               "matched solids that will still be correctly rendered in the final model with "
               "each part).</p>\n"
               "<p>This information will be saved in 'info' directory under the specified working "
               "directory, same file name as the original STEP model but with extension "
               "'.pickle' (and yes, they are just Python pickle files). These files are "
               "saved in one directory, so each original part file have to have unique name, "
               "even when stored in different directories. This file basename (last segment "
               "of the OS path without the extension) will be used as a part name and used "
               "in 'id' and 'class' properties of the result x3d files. The program only "
               "processes the part files if the corresponding info file does not exist or "
               "has the modification timestamp earlier than the STEP model.</p>\n"
               "<p>During the next step the assembly object is analyzed and the same properties "
               "are extracted for each solid, then the each is compared to the library part "
               "and the parts with the same values (to the specified precision) are selected "
               "as potential candidates. Parts material is not used, so distinguish between "
               "similar screws that have the same geometry the color may be used.</p>\n"
               "<p>This allows to find the position of the center of volume of the part in the "
               "assembly, but getting the correct orientation is trickier. For the asymmetrical "
               "(having all 3 different radii of gyration) it is rather easy (only 4 variants "
               "to check as the gyration axes can have opposite direction), it also works for "
               "the parts with full cylindrical or spherical symmetry where the axes match is not "
               "required, but it is more difficult to deal with the discrete rotational symmetry. "
               "When resolving such cases the program relies on colored faces of the parts. "
               "Coloring just a single hole (not on the axis of the symmetry) in the part "
               "(and then using it in the assembly) breaks ambiguity. Parts that do not have "
               "faces that can be easily colored can be modified with boolean operations that "
               "preserves the shape but add color asymmetry.</p>\n"
               "<p>When the solids are matched, the program generates missing/old (by timestamp) " 
               "x3d files of the individual parts and assembly in the 'x3d' subdirectory of the "
               "working directory. It also generates and shows the parts that are not recognized "
               "(they might be 'other' solids of the part files and so will be available in the "
               "generated model).</p>\n"
               "<p>This method can work with most modern CAD systems, and does not require special "
               "export - the colored STEP files are still good for production. In some systems "
               "the assembly model should be flattened (removed assembly status) before STEP "
               "export, it is also advised to import individual parts that are provided to you "
               "as STEP models to the CAD that is used for the assembly and re-exporting to STEP "
               "so both part and assembly STEP files will be generated by the same software.<p>"
               )   
        txt_edit = X3dStepAssyDialog.TextViewerWindow(msg,"Program Description",(100,10,600,920),True,True,self.x3d_root_path)
        txt_edit.show()
        self.textWindows.append(txt_edit)
        
    def preRun(self):    
        global ROOT_DIR, ASSEMBLY_PATH, STEP_PARTS, COMPONENTS, PRECISION, PRECISION_AREA, PRECISION_VOLUME, PRECISION_GYRATION, PRECISION_INSIDE
        ASSEMBLY_PATH =      self.assembly_path
        ROOT_DIR =           self.x3d_root_path
        STEP_PARTS =         self.step_parts_path
        
        PRECISION =          self.precision
        PRECISION_AREA =     self.precision_area
        PRECISION_VOLUME =   self.precision_volume
        PRECISION_GYRATION = self.precision_gyration
        PRECISION_INSIDE =   self.precision_inside
        ASSEMBLY_SUFFIX =    self.assembly_suffix


        self.saveSettings()

    def showBOM(self):
        if not COMPONENTS:
            msgBox = QtGui.QMessageBox.critical(self,"BOM not available", "BOM is available only after assembly conversion")
            msgBox.exec_()
            return
        FreeCAD.Console.PrintMessage("Getting BOM...")
        self.preRun()
        bom = getBOM()
        try:
            if self.assembly_path:
                aname,_ =  os.path.splitext(os.path.basename(assembly_path))
            elif not  FreeCAD.ActiveDocument.Label.startswith(u"Unnamed"):
                aname =  FreeCAD.ActiveDocument.Label
            else:
                aname = FreeCAD.ActiveDocument.Objects[0].Label
        except:
            aname="unknown assembly"
        self.bom_btn.setText("BOM")
        self.bom_btn.setToolTip("Generate Bill of Materials (parts list)")
        txt="Bill of Materials for %s \n\n"%(aname)
        for i, m in enumerate(bom):
            txt += "%3d\t%s\t%d\n"%(i+1,m[0],int(m[1]))

        txt_edit = X3dStepAssyDialog.TextViewerWindow(txt,"Bill of Materials for %s"%(aname),(400,10,300,500),False,False,self.x3d_root_path)
        txt_edit.show()
        self.textWindows.append(txt_edit)
        return
        
    def showOffsets(self):
        FreeCAD.Console.PrintMessage("Starting parts offsets calculation...")
        self.preRun()
        offsets = list_parts_offsets()

        txt=("Parts volume centers distance from the coordinate origin. "
             "Keeping this distance reasonably small (not larger than the object size) "
             "may help to improve precision of objects transformations\n\n")
        for offset in offsets:
            txt += "%s\t%3.2f\n"%offset
        
        txt_edit = X3dStepAssyDialog.TextViewerWindow(txt,"Parts offset distances",(200,10,300,500),False,False,self.x3d_root_path)
        txt_edit.show()
        self.textWindows.append(txt_edit)

    def executeMacro(self):
        global COMPONENTS
        COMPONENTS =         None # Start with new ones
#        FreeCAD.Console.PrintMessage("Starting conversion...")
        self.preRun()
        if  self.log_file:
            sys.stdout = open(self.log_file,"w")
        else:
            sys.stdout = sys.__stdout__

##        try: # does not work
        components=generateAssemblyX3d(self.assembly_path) # If None - will use ActiveDocument().Objects
 ##       except:
 ##           self.errorDialog(traceback.format_exc())    
        showFailedComponents(components)
        sys.stdout.close()
        sys.stdout = sys.__stdout__
        COMPONENTS = components
        self.bom_btn.setText("BOM")
        
    def errorDialog(msg):
    # Create a simple dialog QMessageBox
    # The first argument indicates the icon used: one of QtGui.QMessageBox.{NoIcon, Information, Warning, Critical, Question}
        diag = QtGui.QMessageBox(QtGui.QMessageBox.Error, 'Error in macro', msg)
        diag.exec_()
    
 
#----------------------------------------------------------------------
def saveSettings(): # when working w/o dialog
    config = ConfigParser()
    config.read(CONFIG_PATH) # OK not to have any file
    try:
        config.add_section('paths')
    except:
        pass # OK if the section already exists    
    config.set('paths', 'assembly_path',   ASSEMBLY_PATH)
    config.set('paths', 'x3d_root_path',   ROOT_DIR)
    config.set('paths', 'step_parts_path', STEP_PARTS)
    config.set('paths', 'log_file',        "")
    try:
        config.add_section('precisions')
    except:
        pass # OK if the section already exists    
    config.set('precisions', 'precision',          '%f'%(PRECISION))
    config.set('precisions', 'precision_area',     '%f'%(PRECISION_AREA))
    config.set('precisions', 'precision_volume',   '%f'%(PRECISION_VOLUME))
    config.set('precisions', 'precision_gyration', '%f'%(PRECISION_GYRATION))
    config.set('precisions', 'precision_inside',   '%f'%(PRECISION_INSIDE))
    with open(CONFIG_PATH, 'w') as f:
        config.write(f)

def restoreSettings():
    global ROOT_DIR, ASSEMBLY_PATH, STEP_PARTS, COMPONENTS, PRECISION, PRECISION_AREA, PRECISION_VOLUME, PRECISION_GYRATION, PRECISION_INSIDE
    
    config = ConfigParser()
    config.read(CONFIG_PATH) # OK not to have any file
    try:
        ASSEMBLY_PATH =      config.get('paths', 'assembly_path')
    except:
        pass
    try:         
        ROOT_DIR =           config.get('paths', 'x3d_root_path')
    except:
        pass
    try:            
        STEP_PARTS =         config.get('paths', 'step_parts_path')
    except:
        pass
    try:     
        PRECISION =          float(config.get('precisions', 'precision'))
    except:
        pass
    try:     
        PRECISION_AREA =     float(config.get('precisions', 'precision_area'))
    except:
        pass
    try:     
        PRECISION_VOLUME =   float(config.get('precisions', 'precision_volume'))
    except:
        pass
    try:     
        PRECISION_GYRATION = float(config.get('precisions', 'precision_gyration'))
    except:
        pass
    try:     
        PRECISION_INSIDE =   float(config.get('precisions', 'precision_inside'))
    except:
        pass

if __name__ == "__main__":    
    form = X3dStepAssyDialog() # FreeCADGui.getMainWindow())
    form.show()


"""
from importlib import reload
Manually starting dialog:
import x3d_step_assy3
reload (x3d_step_assy3)
form = x3d_step_assy3.X3dStepAssyDialog()
form.show()
x3d_step_assy3.generateAssemblyX3d("") #or with path

or just run conversion from the command line in Python console 
x3d_step_assy3.generateAssemblyX3d("") #or with path
x3d_step_assy3.showFailedComponents()
"""
