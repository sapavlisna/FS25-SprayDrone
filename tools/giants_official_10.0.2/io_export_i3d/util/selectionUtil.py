""" This util module contains helpers for retrieving the active and selected objects of a blender file,
including hidden objects selected only in the outliner. """

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy, bmesh
import re


def get_outliner_selected_nodes():
    """ Returns objects selected in the outliner, including hidden ones.
    Uses obj.select_get() which reflects selection state regardless of visibility,
    avoiding context-override quirks across Blender versions. """

    return [obj for obj in bpy.context.view_layer.objects if obj.select_get()]

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def getSelectedNodes():
    """ Returns a list of all bpy.context.selected_objects names. """

    iterItems = get_outliner_selected_nodes()
    if iterItems is None or len(iterItems) == 0:
        iterItems = bpy.context.selected_objects
    nameList = [o.name for o in iterItems]
    nameList.sort(key=natural_keys)
    return nameList

def getActiveObjectName(previous):
    """
    previous: name of the previous object
    """

    #nativ_activeObjName = context.active_object.name    #necessary?
    nodes = getSelectedNodes()
    if len(nodes)>0:
        activeObjName = getSelectedNodes()[0]
    else:
        return (previous, False)
    hasChanged = True
    if previous == activeObjName:
        hasChanged = False
    return (activeObjName,hasChanged)


def getSelectedObjects(context):
    # get active object from outliner context
    # this also includes hidden objects like collision etc
    selected_items = []
    for area in context.screen.areas:
        if area.type == 'OUTLINER':
            try:
                context_override = {}
                context_override['area'] = area
                context_override['region'] = [region for region in area.regions if region.type == 'WINDOW'][0]

                with bpy.context.temp_override(**context_override):
                    selected_items.extend(context.selected_ids)
            except Exception as e:
                print(f"An exception occurred: {e}")
    if not selected_items:
        selected_items.extend(context.selected_objects)

    return selected_items