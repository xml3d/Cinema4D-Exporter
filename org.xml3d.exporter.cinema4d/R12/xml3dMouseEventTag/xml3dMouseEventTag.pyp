################################################################################
#
#  xml3dMouseEeventTag.pyp
#
#  Cinema4D to XML3D exporter plugin 
#
#  Copyright (C) 2010 Saarland University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Author(s): Ken Patrik Dahm
# 
################################################################################

import c4d  
import os  
from c4d import plugins, utils, bitmaps, gui  

PLUGIN_ID = 1000002 

class XML3DMouseEventTag(plugins.TagData):  
    """
    This class do not implement any logic. It just offers a gui to enter different
    properties. The gui is defined via resource files.
    The gui provides a text field for each Javascript mouse event. The
    XML3DExporter checks whether such an tag is attached to an object or not. If
    so, it takes the Javascript code and puts it into the right XML3D attribute.
    """
  
    def Init(self, op):
        """
        Initializes the tag
        @param op: The established base object
        """
        return True  
  
    def Execute(self, tag, doc, op, bt, priority, flags):  
        """
        Executes the tag
        @param tag: The established BaseTag
        @param doc: The host documentation of the tag's object
        @param op: The host object of the tag
        @param bt: Currently not used
        @param priority: Priority of this tag
        @param flags: Combination of flags
        """
        return True  

 # Entry point of application: Registers our plugin.
 # Needed information for registering a tag plugin:
 #  id = Unique plugin id
 #  str = Name of the plugin
 #  g = Overwritten class
 #  description = Description of tag
 #  icon = Path to bitmap file
 #  info = Settings for the plugin
if __name__ == "__main__":  
    dir, file = os.path.split(__file__)  
    bmp = bitmaps.BaseBitmap()  
    bmp.InitWith(os.path.join(dir, "res", "export.tif"))  
    plugins.RegisterTagPlugin(id=PLUGIN_ID, str="XML3DMouseEventTag", g=XML3DMouseEventTag,  
                         description="XML3DMouseEventTag", icon=bmp,  
                         info=c4d.TAG_VISIBLE)