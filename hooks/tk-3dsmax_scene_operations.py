# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import sgtk
from sgtk import TankError
from typing import Any, Generator

try:
    import pymxs
except ImportError:
    pymxs = None

HookBaseClass = sgtk.get_hook_baseclass()



class BreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for 3ds Max.

    This implementation handles detection of 3ds Max XRef objects, XRef scenes,
    and bitmap texture file references using the pymxs runtime library.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the hook."""
        super().__init__(*args, **kwargs)
        
        if not pymxs:
            raise TankError("pymxs is not available. Please ensure it's installed and accessible.")

        # Store reference to pymxs runtime for convenience
        self._rt = pymxs.runtime

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene reference
        that is returned should be represented by a dictionary with three keys:

        - "node_name": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "node_type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.
        - "extra_data": Optional key to pass some extra data to the update method
          in case we'd like to access them when updating the nodes.

        Toolkit will scan the list of items, see if any of the objects matches
        a published file and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of date.
        """

        refs = []

        # Scan XRef Objects
        refs.extend(self._scan_xref_objects())

        # Scan XRef Scenes
        refs.extend(self._scan_xref_scenes())

        # Scan Material Bitmap Textures
        refs.extend(self._scan_material_bitmaps())

        return refs

    def _get_xref_objects(self):

        for object_name in self._rt.getMAXFileObjectNames(self._rt.Name("XRefObjects")):
            obj = self._rt.getMAXFileObject(self._rt.Name("XRefObjects"), xref_name)

    def _scan_xref_objects(self):
        """
        Scan for XRef objects in the scene.
        
        :return: List of XRef object references
        :rtype: list
        """
        refs = []

        try:
            # Get all XRef objects in the scene
            xref_objects = self._rt.getMAXFileObjectNames(self._rt.Name("XRefObjects"))
            
            if xref_objects:
                for i in range(xref_objects.count):
                    xref_name = str(xref_objects[i])
                    
                    # Get the XRef object
                    xref_obj = self._rt.getMAXFileObject(self._rt.Name("XRefObjects"), xref_name)
                    
                    if xref_obj and hasattr(xref_obj, 'filename'):
                        file_path = str(xref_obj.filename)
                        if file_path and os.path.exists(file_path):
                            refs.append({
                                "node_name": xref_name,
                                "node_type": "xref_object",
                                "path": os.path.normpath(file_path),
                                "extra_data": {
                                    "xref_index": i
                                }
                            })
        except Exception as e:
            self.logger.warning("Error scanning XRef objects: %s" % str(e))
            
        return refs

    def _scan_xref_scenes(self):
        """
        Scan for XRef scenes in the scene.
        
        :return: List of XRef scene references
        :rtype: list
        """
        refs = []
        
        try:
            # Get all XRef scenes
            xref_scenes = self._rt.getMAXFileObjectNames(self._rt.Name("XRefScenes"))
            
            if xref_scenes:
                for i in range(xref_scenes.count):
                    xref_name = str(xref_scenes[i])
                    
                    # Get the XRef scene
                    xref_scene = self._rt.getMAXFileObject(self._rt.Name("XRefScenes"), xref_name)
                    
                    if xref_scene and hasattr(xref_scene, 'filename'):
                        file_path = str(xref_scene.filename)
                        if file_path and os.path.exists(file_path):
                            refs.append({
                                "node_name": xref_name,
                                "node_type": "xref_scene",
                                "path": os.path.normpath(file_path),
                                "extra_data": {
                                    "xref_index": i
                                }
                            })
        except Exception as e:
            self.logger.warning("Error scanning XRef scenes: %s" % str(e))
            
        return refs

    def _scan_material_bitmaps(self):
        """
        Scan for bitmap textures in materials.
        
        :return: List of bitmap texture references
        :rtype: list
        """
        refs = []
        
        try:
            # Get all bitmap textures in the scene
            bitmap_textures = self._rt.getClassInstances(self._rt.BitmapTexture)
            
            for bitmap in bitmap_textures:
                if hasattr(bitmap, 'filename') and bitmap.filename:
                    file_path = str(bitmap.filename)
                    if file_path and os.path.exists(file_path):
                        # Get the material name that contains this bitmap
                        material_name = self._get_material_name_for_bitmap(bitmap)
                        node_name = "%s_bitmap_%s" % (material_name or "unknown", bitmap.name or "unnamed")
                        
                        refs.append({
                            "node_name": node_name,
                            "node_type": "bitmap_texture",
                            "path": os.path.normpath(file_path),
                            "extra_data": {
                                "bitmap_handle": bitmap.handle,
                                "material_name": material_name
                            }
                        })
        except Exception as e:
            self.logger.warning("Error scanning bitmap textures: %s" % str(e))
            
        return refs

    def _get_material_name_for_bitmap(self, bitmap):
        """
        Get the material name that contains the given bitmap texture.
        
        :param bitmap: The bitmap texture object
        :return: Material name or None if not found
        :rtype: str or None
        """
        try:
            # Get all materials in the scene
            materials = self._rt.sceneMaterials
            
            for material in materials:
                if self._bitmap_in_material(bitmap, material):
                    return str(material.name) if hasattr(material, 'name') else None
        except Exception as e:
            self.logger.debug("Error finding material for bitmap: %s" % str(e))
            
        return None

    def _bitmap_in_material(self, bitmap, material):
        """
        Check if a bitmap is used in a material (recursive check for sub-materials).
        
        :param bitmap: The bitmap texture to search for
        :param material: The material to search in
        :return: True if bitmap is found in material
        :rtype: bool
        """
        try:
            # Check if this material directly uses the bitmap
            if hasattr(material, 'diffuseMap') and material.diffuseMap == bitmap:
                return True
            if hasattr(material, 'bumpMap') and material.bumpMap == bitmap:
                return True
            if hasattr(material, 'specularMap') and material.specularMap == bitmap:
                return True
            if hasattr(material, 'opacityMap') and material.opacityMap == bitmap:
                return True
            if hasattr(material, 'reflectionMap') and material.reflectionMap == bitmap:
                return True
            
            # Check sub-materials for multi-materials
            if hasattr(material, 'materialList'):
                for sub_material in material.materialList:
                    if sub_material and self._bitmap_in_material(bitmap, sub_material):
                        return True
                        
        except Exception as e:
            self.logger.debug("Error checking bitmap in material: %s" % str(e))
            
        return False

    def update(self, item):
        """
        Perform replacements given a number of scene items passed from the app.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        :param item: Dictionary on the same form as was generated by the scan_scene hook above.
                     The path key now holds the path that the node should be updated *to* rather than the current path.
        """

        node_name = item["node_name"]
        node_type = item["node_type"]
        path = item["path"]
        extra_data = item.get("extra_data", {})

        # Normalize path for 3ds Max (use forward slashes)
        path = path.replace("\\", "/")

        if node_type == "xref_object":
            self._update_xref_object(node_name, path, extra_data)
        elif node_type == "xref_scene":
            self._update_xref_scene(node_name, path, extra_data)
        elif node_type == "bitmap_texture":
            self._update_bitmap_texture(node_name, path, extra_data)
        else:
            self.logger.warning("Unknown node type: %s" % node_type)

    def _update_xref_object(self, node_name, path, extra_data):
        """
        Update an XRef object to point to a new file.
        
        :param node_name: Name of the XRef object
        :param path: New file path
        :param extra_data: Extra data containing xref_index
        """
        try:
            self.logger.debug("Updating XRef object '%s' to: %s" % (node_name, path))
            
            xref_index = extra_data.get("xref_index", 0)
            
            # Get the XRef object
            xref_obj = self._rt.getMAXFileObject(self._rt.Name("XRefObjects"), node_name)
            
            if xref_obj:
                # Update the filename
                xref_obj.filename = path
                
                # Reload the XRef
                self._rt.reloadMAXFile(self._rt.Name("XRefObjects"), node_name)
                
                self.logger.debug("Successfully updated XRef object '%s'" % node_name)
            else:
                self.logger.error("Could not find XRef object '%s'" % node_name)
                
        except Exception as e:
            self.logger.error("Error updating XRef object '%s': %s" % (node_name, str(e)))

    def _update_xref_scene(self, node_name, path, extra_data):
        """
        Update an XRef scene to point to a new file.
        
        :param node_name: Name of the XRef scene
        :param path: New file path
        :param extra_data: Extra data containing xref_index
        """
        try:
            self.logger.debug("Updating XRef scene '%s' to: %s" % (node_name, path))
            
            xref_index = extra_data.get("xref_index", 0)
            
            # Get the XRef scene
            xref_scene = self._rt.getMAXFileObject(self._rt.Name("XRefScenes"), node_name)
            
            if xref_scene:
                # Update the filename
                xref_scene.filename = path
                
                # Reload the XRef
                self._rt.reloadMAXFile(self._rt.Name("XRefScenes"), node_name)
                
                self.logger.debug("Successfully updated XRef scene '%s'" % node_name)
            else:
                self.logger.error("Could not find XRef scene '%s'" % node_name)
                
        except Exception as e:
            self.logger.error("Error updating XRef scene '%s': %s" % (node_name, str(e)))

    def _update_bitmap_texture(self, node_name, path, extra_data):
        """
        Update a bitmap texture to point to a new file.
        
        :param node_name: Name identifier for the bitmap
        :param path: New file path
        :param extra_data: Extra data containing bitmap_handle
        """
        try:
            self.logger.debug("Updating bitmap texture '%s' to: %s" % (node_name, path))
            
            bitmap_handle = extra_data.get("bitmap_handle")
            
            if bitmap_handle:
                # Get the bitmap by handle
                bitmap = self._rt.maxOps.getNodeByHandle(bitmap_handle)
                
                if bitmap:
                    # Update the filename
                    bitmap.filename = path
                    
                    # Reload the bitmap
                    bitmap.reload()
                    
                    self.logger.debug("Successfully updated bitmap texture '%s'" % node_name)
                else:
                    self.logger.error("Could not find bitmap texture with handle '%s'" % bitmap_handle)
            else:
                self.logger.error("No bitmap handle provided for '%s'" % node_name)
                
        except Exception as e:
            self.logger.error("Error updating bitmap texture '%s': %s" % (node_name, str(e)))

    def register_scene_change_callback(self, scene_change_callback):
        """
        Register the callback such that it is executed on a scene change event.

        This hook method is useful to reload the breakdown data when the data in the scene has
        changed.

        :param scene_change_callback: The callback to register and execute on scene changes.
        :type scene_change_callback: function
        """
        
        try:
            # 3ds Max doesn't have a direct equivalent to Maya's scene callbacks
            # We'll use a simpler approach with file change notifications
            # This is a placeholder implementation - in a real scenario, you might
            # want to use 3ds Max's notification system or polling
            
            self.logger.debug("Scene change callback registration not fully implemented for 3ds Max")
            
            # Store the callback for potential future use
            self._scene_change_callback = scene_change_callback
            
        except Exception as e:
            self.logger.error("Error registering scene change callback: %s" % str(e))

    def unregister_scene_change_callback(self):
        """Unregister the scene change callbacks."""
        
        try:
            # Clear the stored callback
            if hasattr(self, '_scene_change_callback'):
                self._scene_change_callback = None
                
            self.logger.debug("Scene change callback unregistered")

        except Exception as e:
            self.logger.error("Error unregistering scene change callback: %s" % str(e))
