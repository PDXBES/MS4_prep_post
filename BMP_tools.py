#-------------------------------------------------------------------------------
# Name:        BMP_tools
# Purpose:     some geoprocessing tools to move field data from one fc to another using either attribute or spatial relationships
#
# Author:      DASHNEY
#
# Created:     02/02/2015

#-------------------------------------------------------------------------------

import arcpy
from utilities import addMessage

def add_StandardFields(input):

    # adds a set of fields, this is specific to the BMP inventory - could be made generic by looping through a list of info
    #addMessage("Adding standard fields to " + input)
    arcpy.AddField_management(input,"UID","LONG")
    arcpy.AddField_management(input,"Original_ID","TEXT","","",20)
    arcpy.AddField_management(input,"As_Built","TEXT","","",10)
    arcpy.AddField_management(input,"InstallDate","DATE")
    arcpy.AddField_management(input,"MS4","SHORT")
    arcpy.AddField_management(input,"Data_Source","TEXT","","",25)
    arcpy.AddField_management(input,"Original_Type","TEXT","","",35)
    arcpy.AddField_management(input,"Gen_Type","TEXT","","",35)
    arcpy.AddField_management(input,"ACWA_ID","LONG")
    arcpy.AddField_management(input,"ACWA_Type","TEXT","","",50)
    arcpy.AddField_management(input,"In_Stream","LONG")
    arcpy.AddField_management(input,"Nearest_Hansen","TEXT","","",10)
    arcpy.AddField_management(input,"Subwatershed","TEXT","","",25)


def incrementField(input):

    # for a given field, populates the field with an incrementing (n+1) set of values starting at 1 - can be used to create a unique ID field
    # NEED TO VERIFY - DOES THIS RESPECT EXISTING SORT OR IS IT BASICALLY THE SAME AS POPULATING USING THE OBJECTID?
    addMessage("Populating unique IDs for " + input)
    with arcpy.da.UpdateCursor(input, "UID") as rows:
        for i, row in enumerate(rows, 1):
            row[0] = i
            rows.updateRow(row)

def fillField(input,field,value):

    # fills a specified field with a specified, individual value
    #value supplied must match data type of existing field

    addMessage("Populating the " + field + " field for " +  input)
    with arcpy.da.UpdateCursor(input, field) as cursor:
        for row in cursor:
            row[0] = value
            cursor.updateRow(row)

def fillField_Conditional(input,field,new_value,criteria):

    # fills a specified field with a specified, individual value where any specified field meets a specified value
    # input value supplied must match data type of existing field

    addMessage("Populating the " + field + " field for " +  input)
    select_input = arcpy.MakeFeatureLayer_management(input,"select_input",criteria)
    with arcpy.da.UpdateCursor(select_input, field) as cursor:
        for row in cursor:
            if row[0] is None:
                row[0] = value
                cursor.updateRow(row)

def fillField_fromAnother(input,targetField,sourceField):

    #fills field from another field within the same feature class
    addMessage("Populating the " + str(targetField) + " field for " +  str(input))
    with arcpy.da.UpdateCursor(input, [targetField, sourceField]) as cursor:
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)

def fillField_ifOverlap(input, overlapFC, targetField, value):

    # fills specified field with a specified, individual value where spatial overlap exists between target and another fc
    # input value supplied must match data type of existing field
    # path,name = os.path.split(input)
    addMessage("Populating the " + targetField + " field for " +  str(input))
    input_layer = "input_layer"
    arcpy.MakeFeatureLayer_management(input, input_layer)
    selection = arcpy.SelectLayerByLocation_management(input_layer,"INTERSECT",overlapFC)
    arcpy.CalculateField_management(selection,targetField,value)
    arcpy.Delete_management("in_memory")

    addMessage("Done")

def calcField_fromOverlap(targetFC,targetField,ID,overlapFC,overlapField):

    #fills field with values from another field where overlap exists

    from random import randint # RANDINT USED BECAUSE IN MEMORY IS NOT CLEARING

    #addMessage("Populating the " + targetField + " field for " +  targetFC)
    result = arcpy.Intersect_analysis([targetFC,overlapFC],"in_memory\sect_result" + str(randint(0,100)),"NO_FID","","INPUT")
    values={}
    with arcpy.da.SearchCursor(result,[ID,overlapField]) as cursor:
        for row in cursor:
            if row[0] != None:
                values[row[0]] = row[1]

    with arcpy.da.UpdateCursor(targetFC, [ID, targetField]) as cursor:
        for row in cursor:
            if row[0] in values:
                if values[row[0]] != None:
                    row[1] = values[row[0]]
                cursor.updateRow(row)

    # arcpy.Delete_management("in_memory")
    # BEWARE AS THIS WILL DELETE ALL IN_MEMORY NOT JUST WITHIN FUNCTION

    #addMessage("Done")

def calcField_withinDistance(inputFC,selectFC,criteria,distance,targetField,fillValue):

    addMessage("Populating the " + targetField + " field for " +  inputFC)
    select_input = arcpy.MakeFeatureLayer_management(inputFC,"select_input",criteria)
    #att_selection = arcpy.SelectLayerByAttribute_management(select_input,"NEW_SELECTION",criteria)
    loc_selection = arcpy.SelectLayerByLocation_management(select_input,"INTERSECT",selectFC,distance,"SUBSET_SELECTION")
    arcpy.CalculateField_management(loc_selection,targetField,fillValue)

def fillField_fromDict(inputFC,dictionary,sourceField,targetField):

    addMessage("Populating the " + targetField + " field for " +  str(inputFC))
    with arcpy.da.UpdateCursor(inputFC,[sourceField,targetField]) as rows:
        for row in rows:
            for key,value in dictionary.items():
                if row[0] == key:
                    row[1] = value
                #elif row[0] is None:
                    #row[1] = 9999
                rows.updateRow(row)

def CopyFieldFromFeature(sourceFC,sourceID,sourceField,targetFC,targetID,targetField):

#copy value from a field in one feature class to another through an ID field link - used in place of a table join and field populate (faster)
#credit - Arnold Engelmann (DHI)

    import datetime
    #print "Running : " + datetime.datetime.now().strftime('%x %X')
    #addMessage("Copying field data from " + str(sourceFC) + " to " + str(targetFC) + " using the field: " + str(sourceID))

    values={}
    with arcpy.da.SearchCursor(sourceFC,[sourceID,sourceField]) as cursor:
        for row in cursor:
            values[row[0]] = row[1]

    with arcpy.da.UpdateCursor(targetFC,[targetID,targetField]) as cursor:
        for row in cursor:
            if row[0] in values:
                if values[row[0]] != None:
                    row[1] = values[row[0]]
                cursor.updateRow(row)
    #print "Done: " + datetime.datetime.now().strftime('%x %X')

def CopyFieldsFromFeature(sourceFC,sourceID,sourceFields,targetFC,targetID): # NOT TESTED !!!

    # copies fields into target fc through a join
    # sourceFields is a list but can be single item list
    # sourceFields must already exist in sourceFC but will be created in target if they do not exist
    # BEWARE - this will overwrite fields in target if they do already exist

    import arcpy

    for field in sourceFields:

        values={}

        # fill 'values' dict with ID and field value from source
        with arcpy.da.SearchCursor(sourceFC,[sourceID,sourceField]) as cursor:
            for row in cursor:
                values[row[0]] = row[1]

        # list all target fields
        targetFields = arcpy.ListFields(targetFC)

        # get field info from sourceFC
        my_field = arcpy.ListFields(sourceFC, field)[0]

        my_name = my_field.name
        my_type = my_field.type
        my_length = my_field.length

        # if source field not in target fields, create it
        if field not in targetFields:
            arcpy.AddField_management(targetFC, my_name, my_type, "", "", my_length)

        # update target field with value from source field
        with arcpy.da.UpdateCursor(targetFC,[targetID,targetField]) as cursor:
            for row in cursor:
                if row[0] in values:
                    if values[row[0]] != None:
                        row[1] = values[row[0]]
                    cursor.updateRow(row)


