#-------------------------------------------------------------------------------
# Name:        MS4_Hub_prep
# Purpose:
#
# Author:      dashney
#
# Created:     27/03/2015
#
# Prepares data which has been revised per MS4 criteria for posting to CGIS hub.
# Runs some spatial stats and adds fields to represent these.
# Copies data snapshot to both archive field which has a list of date stamped versions
# and overwrites data in the "Current" directory.
# After running have steward check Current directory results before running
# the associated script to push data to the hub loading location.

# no params
#-------------------------------------------------------------------------------

#import modules
import arcpy
from utilities import reorder_fields,rename_fields
from BMP_tools import fillField_fromDict
import time
import os

#environmental variables
arcpy.gp.overwriteOutput = True

#connections
editors = r"\\besfile1\grp117\DAshney\Scripts\connections\ASM_Editors_on_BESDBPROD1.sde"
egh_public = r"\\besfile1\grp117\DAshney\Scripts\connections\egh_public on gisdb1.rose.portland.local.sde"

temp = r"C:\temp\hubpost_working.gdb"
if not arcpy.Exists(temp):
    arcpy.CreateFileGDB_management(os.path.dirname(temp), os.path.basename(temp))

archive = r"\\besfile1\modeling\GridMaster\MS4\ARC\Archive\Archive.gdb"
output = r"\\besfile1\modeling\GridMaster\MS4\ARC\CurrentAdopted\Current_MS4.gdb"

#inputs
of_points = editors + r"\ASM_EDITORS.GIS.MS4\ASM_EDITORS.GIS.MS4_OF_Points"
of_bounds = editors + r"\ASM_EDITORS.GIS.MS4\ASM_EDITORS.GIS.MS4_OF_Bounds"
wsheds = editors + r"\ASM_EDITORS.GIS.MS4\ASM_EDITORS.GIS.MS4_Watersheds"

zoning = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.zoning_pdx"
lines = egh_public + r"\EGH_PUBLIC.ARCMAP_ADMIN.collection_lines_bes_pdx"

print("Starting MS4_Hub_prep...")

#copy main features to working location
print("Copying from source to temp")
of_points_copy = arcpy.CopyFeatures_management(of_points, temp + r"\of_points_copy", "", "0", "0", "0")
of_bounds_copy = arcpy.CopyFeatures_management(of_bounds, temp + r"\of_bounds_copy", "", "0", "0", "0")
wsheds_copy = arcpy.CopyFeatures_management(wsheds, temp + r"\wsheds_copy", "", "0", "0", "0")

#add and calc some fields
print("Adding fields and initializing values")
arcpy.AddField_management(of_points_copy,"Pipe_Dia","DOUBLE")
arcpy.AddField_management(of_bounds_copy,"Area_Acres","DOUBLE")
arcpy.AddField_management(of_bounds_copy,"Acres_IND","DOUBLE")
arcpy.CalculateField_management(of_bounds_copy,"Acres_IND",0,"PYTHON","#")
arcpy.CalculateField_management(wsheds_copy,"Area_Acres","round(!Shape_Area!/43560,2)","PYTHON","#")
arcpy.CalculateField_management(of_bounds_copy,"Area_Acres","round(!Shape_Area!/43560,2)","PYTHON","#")

#calculating prelimenary IND area acres
print("Calculating prelimenary IND area acres")
zoningfl = "zoningfl"
#these 'employment' codes ('EG1', 'EG2', 'EX') were explicitly included per Patrice in addition to core IND codes
arcpy.MakeFeatureLayer_management(zoning, zoningfl, "ZONE in ( 'EG1', 'EG2', 'EX', 'IG1', 'IG2', 'IH')")
inputs = [zoningfl,of_bounds_copy]
bounds_zoning_sect = temp + r"\bounds_zoning_sect"
arcpy.Intersect_analysis(inputs, bounds_zoning_sect,"NO_FID","#","INPUT")
bounds_zoning_diss = temp + r"\bounds_zoning_diss"
arcpy.Dissolve_management(bounds_zoning_sect,bounds_zoning_diss,"Index_ID","Shape_Area SUM","MULTI_PART")
arcpy.AddField_management(bounds_zoning_diss,"Acres_calc","DOUBLE")
arcpy.CalculateField_management(bounds_zoning_diss,"Acres_calc","round(!SUM_SHAPE_Area!/43560,2)","PYTHON","#")

#calculating area of IND for OF bounds
print("Calculating area of IND and total area for OF bounds")
values={}
with arcpy.da.SearchCursor(bounds_zoning_diss,["Index_ID","Acres_calc"]) as cursor:
    for row in cursor:
        if row[0] != None:
            values[row[0]] = row[1]

with arcpy.da.UpdateCursor(of_bounds_copy, ["Index_ID", "Acres_IND"]) as cursor:
    for row in cursor:
        if row[0] in values:
            if values[row[0]] == None:
                row[1] = 0
            else:
                row[1] = values[row[0]]
            cursor.updateRow(row)

# calculating area acres field from shape_area for OF bounds"
arcpy.CalculateField_management(of_bounds_copy,"Area_Acres","round(!SHAPE_Area!/43560,2)","PYTHON","#")

# calculating pipe diameter on OF points
print("Calculating pipe diameter on OF points")
values={}
with arcpy.da.SearchCursor(lines,["TO_NODE","PIPESIZE"]) as cursor:
    for row in cursor:
        if row[0] != None:
            values[row[0]] = row[1]

with arcpy.da.UpdateCursor(of_points_copy, ["HANSEN_ID", "Pipe_Dia"]) as cursor:
    for row in cursor:
        if row[0] in values:
            if values[row[0]] != None:
                row[1] = values[row[0]]
            cursor.updateRow(row)

# convert Watershed field (bounds) and Watershed_ (watersheds) from integer (used in subtype) to text
print("Adding temp Watershed fields")
arcpy.AddField_management(of_points_copy,"Watershed_txt","TEXT","","",25)
arcpy.AddField_management(of_bounds_copy,"Watershed_txt","TEXT","","",25)
arcpy.AddField_management(wsheds_copy,"Watershed_txt","TEXT","","",25)

# remove watershed subtypes
print("Removing watershed subtyptes")
subtype_list = [1,2,3,4,5,6]
arcpy.RemoveSubtype_management(of_points_copy,subtype_list)
arcpy.RemoveSubtype_management(of_bounds_copy,subtype_list)
arcpy.RemoveSubtype_management(wsheds_copy,subtype_list)

type_dict = ({1:"COLUMBIA RIVER",
2:"COLUMBIA SLOUGH",
3:"JOHNSON CREEK",
4:"TUALATIN RIVER",
5:"WILLAMETTE RIVER",
6:"N/A"})

print("Filling fields from dictionary...")
fillField_fromDict(of_points_copy,type_dict,"Watershed","Watershed_txt")
fillField_fromDict(of_bounds_copy,type_dict,"Watershed","Watershed_txt")
fillField_fromDict(wsheds_copy,type_dict,"Watershed_","Watershed_txt")

#re-order fields and delete those that are unnecessary
arcpy.DeleteField_management(of_points_copy,"Watershed")
arcpy.DeleteField_management(of_bounds_copy,"Watershed")
arcpy.DeleteField_management(wsheds_copy,"Watershed_")

print("Renaming fields")
rename_dict = {'Watershed_txt':'Watershed'}
wshed_dict = {'Watershed_txt':'Watershed', 'Basin_':'Basin'}
points_rename = temp + r"\points_rename"
bounds_rename = temp + r"\bounds_rename"
wsheds_rename = temp + r"\wsheds_rename"
rename_fields(of_points_copy,points_rename,rename_dict)
rename_fields(of_bounds_copy,bounds_rename,rename_dict)
rename_fields(wsheds_copy,wsheds_rename,wshed_dict)

points_new_order = (["Index_ID","OUTFALL_ID","X_coordinates","Y_coordinates","Outfall_Type",
"MS4_permit","CSO_permit","permittedSSO","HANSEN_ID","Ownership","Prev_TYPE_1990","Control_Date",
"ControlMechanism","CSOCntrlRegStruc","Watershed","Basin","Subbasin","ServStat","Control_Level",
"Comments","Pipe_Dia"])
bounds_new_order = (["Index_ID","OUTFALL_ID","Boundary_Type","Jurisdiction",
"HANSEN_ID","SOURCE","COMMENTS","Watershed","Basin","Acres_IND","Area_Acres"])
wsheds_new_order = ["Index_ID","Area_Acres","Watershed","Basin"]

print("Re-ordering fields and saving to " + archive)
points_final = archive + r"\MS4_OFpoints_" + time.strftime("%m%d%Y")
bounds_final= archive + r"\MS4_OFbounds_" + time.strftime("%m%d%Y")
wsheds_final= archive + r"\MS4_watersheds_" + time.strftime("%m%d%Y")
reorder_fields(points_rename, points_final ,points_new_order,add_missing = False)
reorder_fields(bounds_rename, bounds_final ,bounds_new_order,add_missing = False)
reorder_fields(wsheds_rename, wsheds_final, wsheds_new_order,add_missing = False)

#copy result to "Current" directory - overwrite existing
print("Copying same results to " + output)
arcpy.FeatureClassToFeatureClass_conversion(points_final,output,"OF_points_bes_pdx")
arcpy.FeatureClassToFeatureClass_conversion(bounds_final,output,"OF_drainage_bounds_bes_pdx")
arcpy.FeatureClassToFeatureClass_conversion(wsheds_final,output,"MS4_catchments_bes_pdx")

print("... MS4_Hub_prep Finished")




