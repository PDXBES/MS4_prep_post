#-------------------------------------------------------------------------------
# Name:        utilities
# Purpose:
#
# Author:      Josh Werts
#   http://joshwerts.com/blog/
# for reorder and rename fields pieces

#-------------------------------------------------------------------------------


import arcpy, os, datetime, platform


def reorder_fields(table, out_table, field_order, add_missing=True):
    """
    Reorders fields in input featureclass/table
    :table:         input table (fc, table, layer, etc)
    :out_table:     output table (fc, table, layer, etc)
    :field_order:   order of fields (objectid, shape not necessary)
    :add_missing:   add missing fields (that were not specified in field_order) to end if True (leave out if False) - good way to delete a bunch of fields if you need to
    -> path to output table
    """
    existing_fields = arcpy.ListFields(table)
    existing_field_names = [field.name for field in existing_fields]

    existing_mapping = arcpy.FieldMappings()
    existing_mapping.addTable(table)

    new_mapping = arcpy.FieldMappings()

    def add_mapping(field_name):
        mapping_index = existing_mapping.findFieldMapIndex(field_name)

        # required fields (OBJECTID, etc) will not be in existing mappings
        # they are added automatically
        if mapping_index != -1:
            field_map = existing_mapping.fieldMappings[mapping_index]
            new_mapping.addFieldMap(field_map)

    # add user fields from field_order
    for field_name in field_order:
        if field_name not in existing_field_names:
            raise Exception("Field: {0} not in {1}".format(field_name, table))

        add_mapping(field_name)

    # add missing fields at end
    if add_missing:
        missing_fields = [f for f in existing_field_names if f not in field_order]
        for field_name in missing_fields:
            add_mapping(field_name)

    # use merge with single input just to use new field_mappings
    arcpy.Merge_management(table, out_table, new_mapping)
    return out_table


def rename_fields(table, out_table, new_name_by_old_name):
    """ Renames specified fields in input feature class/table
    :table:                 input table (fc, table, layer, etc)
    :out_table:             output table (fc, table, layer, etc)
    :new_name_by_old_name:  {'old_field_name':'new_field_name',...}
    ->  out_table
    """
    existing_field_names = [field.name for field in arcpy.ListFields(table)]

    field_mappings = arcpy.FieldMappings()
    field_mappings.addTable(table)

    for old_field_name, new_field_name in new_name_by_old_name.iteritems():
        if old_field_name not in existing_field_names:
            message = "Field: {0} not in {1}".format(old_field_name, table)
            raise Exception(message)

        mapping_index = field_mappings.findFieldMapIndex(old_field_name)
        field_map = field_mappings.fieldMappings[mapping_index]
        output_field = field_map.outputField
        output_field.name = new_field_name
        output_field.aliasName = new_field_name
        field_map.outputField = output_field
        field_mappings.replaceFieldMap(mapping_index, field_map)

    # use merge with single input just to use new field_mappings
    arcpy.Merge_management(table, out_table, field_mappings)
    return out_table

def addMessage(message, log_file_path = None):

    if len(message) < 1000:
        arcpy.AddMessage(message)

    time_stamp = datetime.datetime.now().strftime('%x %X')
    full_message = "{0} - {1}".format(time_stamp, message)
    print full_message[0:min(len(full_message), 1000)]

    # Hack to get rawq scripts to output to build log without having to pass through logfile name
    if log_file_path is None and platform.node() == 'WS18325':
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir.lower() == r'c:\swsp\scripts':
            log_file_path = r'C:\SWSP\Build\Swsp.Build.log'

    if log_file_path is None:
        script_dir = os.path.curdir
        log_file_path = os.path.join(script_dir, "Script_Log.log")

    if not log_file_path is None:
        log_file = open(log_file_path, 'a')
        log_file.write(full_message + "\n")
        log_file.close()

    return

def replaceBogusCharacters(input):
     in1 = input.replace("-", "_")
     in2 = in1.replace(".", "_")
     in3 = in2.replace(" ", "_")
     in4 = in3.replace("(", "_")
     in5 = in4.replace(")", "_")
     output = in5.replace("/", "_")
     return output
