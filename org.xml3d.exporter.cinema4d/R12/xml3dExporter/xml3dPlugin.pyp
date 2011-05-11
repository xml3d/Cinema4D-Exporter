######################################################################################
#
#  xml3dPlugin.pyp
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
#  Author(s): Ken Patrik Dahm, Georg Demme
# 
#####################################################################################

import os
import sys
import c4d
from c4d import gui, plugins, utils, bitmaps, storage, documents

sys.path.append(c4d.storage.GeGetStartupWritePath() + "/plugins/xml3dExporter/")  # local plugins
sys.path.append(c4d.storage.GeGetStartupPath() + "/plugins/xml3dExporter/")       # global plugins
from xml3dExporter import XML3DExporter
 
PLUGIN_ID_EXPORTER = 1193733
 
class XML3DExporterGUI(gui.GeDialog):
    """
    Extended dialog to communicate with the user.
    """

    def __init__(self):
        """
        Initialize the dialog by removing the menubar from the dialog
        """
        self.AddGadget(c4d.DIALOG_NOMENUBAR, 0)

    def InitValues(self):
        """
        Initializing gui layout and and try to read previously stored settings.
        @return: Success
        """
        self.SetTitle("Export as XML3D")
        self.GroupBorderSpace(5,5,5,5)
        self.GroupBegin(id=101, flags=c4d.BFH_SCALEFIT, rows=3, title="", cols=2, groupflags=c4d.BORDER_GROUP_IN)
        self.AddStaticText(id=1011,initw=0, inith=0, name="Panel width:", borderstyle=0, flags=c4d.BFH_SCALEFIT)
        self.panelWidth = self.AddEditText(id=10111, flags=c4d.BFH_SCALEFIT, initw=50, inith=0)
        self.AddStaticText(id=1012,initw=0, inith=0, name="Panel height:", borderstyle=0, flags=c4d.BFH_SCALEFIT)
        self.panelHeight = self.AddEditText(id=10121, flags=c4d.BFH_SCALEFIT, initw=50, inith=0)
        self.AddStaticText(id=1013,initw=0, inith=0, name="Embed into XHTML:", borderstyle=0, flags=c4d.BFH_SCALEFIT)
        self.embedIntoXHTML = self.AddCheckbox(id=10131, flags=c4d.BFH_SCALEFIT, initw=0, inith=0, name="")
        self.GroupEnd()

        self.GroupBegin(id=101, flags=c4d.BFH_SCALEFIT, rows=1, title="", cols=1, groupflags=c4d.BORDER_GROUP_IN)
        self.exportStrategy = self.AddComboBox(id=10290, flags=c4d.BFH_SCALEFIT)
        self.AddChild(10290, 102900, "Export whole scene")
        self.AddChild(10290, 102901, "Export tagged objects separately")
        self.AddChild(10290, 102903, "Export tagged objects separately with separate defs and groups")
        self.AddChild(10290, 102902, "Export only selected objects")
        self.GroupEnd()
 
        self.GroupBegin(id=103, flags=c4d.BFH_SCALEFIT, rows=2, title="", cols=2, groupflags=c4d.BORDER_GROUP_IN)
        self.AddStaticText(id=1031,initw=0, inith=0, name="", borderstyle=0, flags=c4d.BFH_SCALEFIT)
        self.bt_Submit = self.AddButton(id=10311, flags=c4d.BFH_SCALEFIT, initw=100, inith=10, name="Export")
        self.AddStaticText(id=1032,initw=0, inith=0, name="", borderstyle=0, flags=c4d.BFH_SCALEFIT)
        self.bt_Cancel = self.AddButton(id=10321, flags=c4d.BFH_SCALEFIT, initw=100, inith=10, name="Cancel")
        self.GroupEnd()
 
        if self.readSettings() == False:
            self.targetPath = None
            self.SetString(self.panelWidth, "1024")
            self.SetString(self.panelHeight, "1024")
            self.SetBool(self.embedIntoXHTML, True)
            self.SetLong(self.exportStrategy, 102900)
        return True
 
    def Command(self,id,msg):
        """
        This method gets called after a user event was fired. Call exporting
        routine if the user clicked the 'Submit'-button.
        @param id: Id of fired event
        @param msg: Message
        @return: Success
        """
        if id == 10321: # Cancel
            self.Close()
        elif id == 10311: # Submit
            # Read settings
            if self.targetPath != None:
                self.targetPath = storage.SaveDialog(0, "Choose target file", "xhtml", self.targetPath)
            else:    
                docPath = documents.GetActiveDocument().GetDocumentPath()
                if docPath != "":
                    self.targetPath = storage.SaveDialog(0, "Choose target file", "xhtml", docPath)
                else:
                    self.targetPath = storage.SaveDialog(0, "Choose target file", "xhtml", storage.GeGetStartupWritepath())
            
            if self.targetPath == None:
                self.Close()
                return False
            
            # Store settings
            if self.storeSettings() == False:
                print "Something went wrong (self.storeSettings())"
            self.export()

        return True
 
    def AskClose(self):
        """
        If the user wants to close the dialog with the OK button this function
        will be called
        """
        return False

    def export(self):     
        """
        Call exporter. This method gets called right after the user clicked the
        'Submit'-button.
        """
        try:
            width = self.GetString(self.panelWidth)
            height = self.GetString(self.panelHeight)
            embed = self.GetBool(self.embedIntoXHTML)
            strategy = self.GetLong(self.exportStrategy)
        except:
            print "Invalid parameter. Can't export scene. Will abort now."
            return

        if self.targetPath == None:
            print "Invalid path specified. Can't export scene. Will abort now."
            return

        exporter = XML3DExporter(self.targetPath)
        scene = documents.GetActiveDocument()
        self.Close()
        exporter.write(documents.GetActiveDocument(), width, height, embed, strategy)
        
    def readSettings(self):
        """
        Try to read previously entered data. Cinema4D provides a convenient way
        to get a container for a specific plugin. We can call the function
        c4d.plugins.GetWorldPluginData() with our plugin id to see whether there
        is some data or not.
        @return True: Data found => Read data
        @return False: No data found
        """
        self.settings = c4d.plugins.GetWorldPluginData(PLUGIN_ID_EXPORTER)
        if self.settings is None:
            return False
        else:
            self.targetPath = self.settings.GetString(0)
            self.SetString(self.panelWidth, self.settings.GetString(1))
            self.SetString(self.panelHeight, self.settings.GetString(2))
            self.SetBool(self.embedIntoXHTML, self.settings.GetBool(3))
            self.SetLong(self.exportStrategy, self.settings.GetLong(4))
            return True
 
    def storeSettings(self):
        """
        Create a new container if it is not already initialized and put the
        entered data to it
        @return True: Data were successfully stored
        @return False: Error
        """
        if self.settings is None:
            self.settings = c4d.BaseContainer()
        self.settings.SetString(0, self.targetPath)
        self.settings.SetString(1, self.GetString(self.panelWidth))
        self.settings.SetString(2, self.GetString(self.panelHeight))
        self.settings.SetBool(3, self.GetBool(self.embedIntoXHTML))
        self.settings.SetLong(4, self.GetLong(self.exportStrategy))
        result = c4d.plugins.SetWorldPluginData(PLUGIN_ID_EXPORTER, self.settings, False)
        return result
        
 
class XML3DCommandData(c4d.plugins.CommandData):
    """
    XML3DCommandData extends c4d.plugins.CommandData to export the scene
    to file.
    """
    dialog = None
 
    def Execute(self, doc):
        """
        Execute fires up the GUI
        @param doc: The currently active document when the command was selected.
        """
        if self.dialog is None:
           self.dialog = XML3DExporterGUI()
 
        return self.dialog.Open(False, pluginid=PLUGIN_ID_EXPORTER, defaulth=200, defaultw=340)
 
# Entry point of application: Registers our plugin.
# Needed information for registering a CommandData plugin:
#  id = Unique plugin id
#  str = Name of the plugin
#  help = Tool tip and status bar help
#  info = Settings for the plugin
#  dat = Class which inherited from c4d.plugins.CommandData
#  icon = Path to bitmap file
if __name__ == "__main__":
    bmp = bitmaps.BaseBitmap()
    dir, f = os.path.split(__file__)
    
    # Register exporter plugin
    bmp.InitWith(os.path.join(dir, "res", "export.tif"))
    c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID_EXPORTER, str="XML3DExporter",help="XML3D Exporter",info=0, dat=XML3DCommandData(), icon=bmp)