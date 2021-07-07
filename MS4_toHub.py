#-------------------------------------------------------------------------------
# Name:        MS4_toHub
# Purpose:
#
# Author:      dashney
#
# Created:     31/03/2015
# script copies MS4 files from 'Current' directory to CGIS loading location
# ONLY RUN ONCE REVIEW OF MS4_Hub_prep SCRIPT RESULT IS COMPLETE

# no params
#-------------------------------------------------------------------------------

import arcpy
import os

#environmental variables
arcpy.gp.overwriteOutput = True

input = r"\\besfile1\modeling\GridMaster\MS4\ARC\CurrentAdopted\Current_MS4.gdb"
output = r"\\besfile1\grp117\DAshney\Scripts\connections\BESDBPROD1.GIS_TRANSFER10.GIS.sde"

print "Starting Process"

print "Getting list of feature classes to copy"
arcpy.env.workspace = input
fc_list = []
fcs = arcpy.ListFeatureClasses()
for fc in fcs:
    fc_list.append(fc)

print "Deleting old versions from loading dock before copying the new ones"
for fc in fc_list:
    fc_path = os.path.join(output,fc)
    if arcpy.Exists(fc_path):
        print "...deleting " + fc + " from GIS_TRANSFER10"
        arcpy.Delete_management(fc_path)
    else:
        print fc + " : ...none to delete"

print "Copying data from " + input + " to " + output
print "...copying " + str(fc_list) + " to GIS_TRANSFER10"
arcpy.FeatureClassToGeodatabase_conversion(fc_list,output)

print "Process Complete"