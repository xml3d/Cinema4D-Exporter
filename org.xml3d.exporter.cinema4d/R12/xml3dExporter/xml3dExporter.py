################################################################################
#
#  xml3dExporter.py
#
#  Cinema4D to XML3D exporter plugin
#
#  Copyright (C) 2010  Saarland University
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
#  Author(s): Ken Patrik Dahm, Tobias Gross, Georg Demme
#
################################################################################

import xml.dom.minidom
import c4d
import math
import sys
import traceback
import re
from c4d import *
from xml3d import *

class XML3DExporter:
    """
    Class for exporting the scene as XML3D
    """
    def __init__(self, filename):
        """
        """
        self.filename = filename

        self.XML3D_EXPORT_STRATEGY_COMPLETE = 102900
        self.XML3D_EXPORT_STRATEGY_TAGGED   = 102901
        self.XML3D_EXPORT_STRATEGY_SELECTED = 102902
        self.XML3D_EXPORT_STRATEGY_TAGGED_S = 102903


    ############################################################################
    # UTILITY

    def createUniqueAndValidName(self, obj, prefix, renameId):
        """
        Replacing the name of an object by a prefix and a number. The original is
        stored in a map.
        Key -> Value
        New name (prefix_ASCENDING-NUMBER) -> Original C4D name
        @param obj: Object to be renamed
        @param prefix: New name is given as: prefix_ASCENDING-NUMBER
        @param renameId: Unique number for renaming
        """
        newName = "%s_%d_%s" % (prefix,renameId,self.mangleName(obj.GetName()))
        self.originalNames[newName] = obj.GetName()
        obj.SetName(newName)

    def createUniqueAndValidNames(self, obj, prefix, renameId):
        """
        XML3D doesn't allow non-unique node names - Cinema4D does. This method
        traverses the scene graph and renames all renames all objects/materials.
        @param obj: Object to be renamed
        @param prefix: Either 'material' or 'object'
        @param renameId: Unique number for renaming
        @return: Modified renameId
        """
        while obj != None:
            self.createUniqueAndValidName(obj, prefix, renameId)
            renameId = renameId + 1
            renameId = self.createUniqueAndValidNames(obj.GetDown(), prefix, renameId)
            obj = obj.GetNext()
        return renameId

    def createProperFilename(self, filename):
        """
        Append .xhtml if not already appended
        @param filename: Name of file to be checked
        @return: Either original name (if ok) or modified one
        """
        if re.search(".xhtml$", filename) == None:
            filename = filename % ".xhtml"
        return filename

    def findWorldAmbient(self, obj):
        """
        Find global ambient color and ambient strength
        @param obj: Start of hierarchical search
        """
        while obj != None:
            if obj.GetType() == c4d.Oenvironment:
                objContainer = obj.GetDataInstance()
                ambColor = obj[c4d.ENVIRONMENT_AMBIENT]
                ambStrength = obj[c4d.ENVIRONMENT_AMBIENTSTRENGTH]
                self.ambientWorld = ambColor * ambStrength
                break
            else:
                self.findWorldAmbient(obj.GetDown())
                obj = obj.GetNext()

    def findTaggedObjects(self, obj):
        """
        """
        list = []
        while obj != None:
            tag = self.findTagByName(obj, "XML3DMouseEventTag")
            if tag != None:
                print("Found tagged object %s" % obj.GetName())
                list.append(obj)
            list.extend(self.findTaggedObjects(obj.GetDown()))
            obj = obj.GetNext()
        return list

    def mangleName(self, name):
        """
        Change object and material names so that they match the needs of a proper
        XML3D name.
        @param name: string
        @return: mangled name
        """
        name = re.sub("[^A-Za-z0-9_-]", "", name)
        name = re.sub(" ", "_", name)
        return name

    def mangleObjectNames(self, obj):
        """
        Change all object names hierarchically using the string transformation
        done by mangleName().
        @param obj: Start of hierarchical whitespace elimination
        """
        while obj != None:
            obj.SetName( self.mangleName(obj.GetName()) )
            self.mangleObjectNames(obj.GetDown())
            obj = obj.GetNext()

    def monochromaticTransform(self, rgb):
        """
        Transform a RGB color value to its monochromatic equivalent
        @param rgb: Color value in RGB format
        @return: Monochromatic representation of rgb
        """
        return 0.2125 * rgb.x + 0.7154 * rgb.y + 0.0721 * rgb.z

    def getName(self, obj):
        """
        Extract Cinema4D name from object
        @param obj: Object
        @return: Name of obj
        """
        return obj.GetName()

    def writeNull(self, parent, obj):
        """
        Create a group element and append it to 'parent'
        @param parent: Parent object in graph
        @param obj: Group is named after name of 'obj'
        @return: XML3D element
        """
        group = self.doc.createGroupElement(self.getName(obj), \
                "true", "#t_%s" % self.getName(obj))
        parent.appendChild(group)
        return group

    def convertRadians(self, radians):
        """
        Convert degree to radians
        @param radians: Value in radians
        @param: Value in degree
        """
        return radians * 180.0 / math.pi

    def createFloatTextElement(self, name, text, id = None):
        """
        Wrapper method for generating a XML3D float element
        @param name: Name of element
        @param text: Will be attached to the the element as text node
        @param id: Optional field. ID of the XML3D element
        @return: XML3D element
        """
        element = self.doc.createFloatElement(id, name)
        element.appendChild(self.doc.createTextNode(text))
        return element

    def createFloat2TextElement(self, name, text, id = None):
        """
        Wrapper method for generating a XML3D float2 element
        @param name: Name of element
        @param text: Will be attached to the the element as text node
        @param id: Optional field. ID of the XML3D element
        @return: XML3D element
        """
        element = self.doc.createFloat2Element(id, name)
        element.appendChild(self.doc.createTextNode(text))
        return element

    def createFloat3TextElement(self, name, text, id = None):
        """
        Wrapper method for generating a XML3D float3 element
        @param name: Name of element
        @param text: Will be attached to the the element as text node
        @param id: Optional field. ID of the XML3D element
        @return: XML3D element
        """
        element = self.doc.createFloat3Element(id, name)
        element.appendChild(self.doc.createTextNode(text))
        return element

    def createIntTextElement(self, name, text, id = None):
        """
        Wrapper method for generating a XML3D int element
        @param name: Name of element
        @param text: Will be attached to the the element as text node
        @param id: Optional field. ID of the XML3D element
        @return: XML3D element
        """
        element = self.doc.createIntElement(id, name)
        element.appendChild(self.doc.createTextNode(text))
        return element

    def createBoolTextElement(self, name, text, id = None):
        """
        Wrapper method for generating a XML3D bool element
        @param name: Name of element
        @param text: Will be attached to the the element as text node
        @param id: Optional field. ID of the XML3D element
        @return: XML3D element
        """
        element = self.doc.createBoolElement(id, name)
        element.appendChild(self.doc.createTextNode(text))
        return element

    def createShader(self, name, ambient, diffuseColor, emissiveColor, specularColor, shininess, transparency, reflective, texture = None):
        """
        Wrapper method for generating a XML3D shader element
        @param name: Name of element
        @param ambient: Ambient color
        @param diffuseColor: Diffuse color
        @param emissiveColor: Emissive color
        @param specularColor: Specular color
        @param shininess: Specular exponent
        @param transparency: Transparency amount between 0-1
        @param reflective   : Reflectivity amount
        @param texture: Optional. Texture path
        @return: XML3D element
        """
        shaderElement = self.doc.createShaderElement("shader_%s" % name, "urn:xml3d:shader:phong")
        shaderElement.appendChild(self.createFloatTextElement("ambientIntensity", "%g" % ambient))
        shaderElement.appendChild(self.createFloat3TextElement("diffuseColor", "%g %g %g" % (diffuseColor.x,diffuseColor.y,diffuseColor.z)))
        shaderElement.appendChild(self.createFloat3TextElement("emissiveColor", "%g %g %g" % (emissiveColor.x,emissiveColor.y,emissiveColor.z)))
        shaderElement.appendChild(self.createFloat3TextElement("specularColor", "%g %g %g" % (specularColor.x,specularColor.y,specularColor.z)))
        shaderElement.appendChild(self.createFloat3TextElement("reflective", "%g %g %g" % (reflective,reflective,reflective)))
        shaderElement.appendChild(self.createFloatTextElement("shininess", "%g" % shininess))
        shaderElement.appendChild(self.createFloatTextElement("transparency", "%g" % transparency))

        if texture != None and texture[c4d.BITMAPSHADER_FILENAME] != None:
            textureElement = self.doc.createTextureElement(None, "diffuseTexture")
            textureElement.appendChild(self.doc.createImgElement(None, "tex/" + texture[c4d.BITMAPSHADER_FILENAME]))
            shaderElement.appendChild(textureElement)
        return shaderElement

    def createEnvShader(self, name, texture):
        """
        Wrapper method for generating a XML3D environment shader element
        @param name: Name of element
        @param texture: Texture path
        @return: XML3D element
        """
        shaderElement = self.doc.createShaderElement("shader_%s" % name, "urn:xml3d:shader:phong")
        if texture != None:
            textureElement = self.doc.createTextureElement(None, "diffuseTexture")
            textureElement.appendChild(self.doc.createImgElement(None, texture[c4d.BITMAPSHADER_FILENAME]))
            shaderElement.appendChild(textureElement)
            shaderElement.appendChild(self.createBoolTextElement("receiveShadow", "false"))

        return shaderElement

    def getTypeAsString(self, obj):
        """
        Convert type of object to string
        @param obj: Object of interest
        @return: String representation
        @return: 'Unknown' if type is unknown
        """
        if obj.GetType() == c4d.Opolygon:
            return "Polygon"
        elif obj.GetType() == c4d.Olight:
            return "Light"
        elif obj.GetType() == c4d.Ocamera:
            return "Camera"
        elif obj.GetType() == c4d.Oinstance:
            return "Instance"
        elif obj.GetType() == c4d.Oenvironment:
            return "Environment"
        elif obj.GetType() == c4d.Onull:
            return "Null"
        else:
            return "Unknown"

    def modifytextureLenght (self, LengthX, LengthY, fidx, uvwTag):
        """
        """
        uvw = uvwTag.GetSlow(fidx)
        scaledVec = Vector(LengthX, LengthY, 1)
        uvw["a"].x = uvw["a"].x / LengthX
        uvw["a"].y = uvw["a"].y / LengthY

        uvw["b"].x = uvw["b"].x / LengthX
        uvw["b"].y = uvw["b"].y / LengthY

        uvw["c"].x = uvw["c"].x / LengthX
        uvw["c"].y = uvw["c"].y / LengthY

        if len(uvw) > 3:
            uvw["d"].x = uvw["d"].x / LengthX
            uvw["d"].y = uvw["d"].y / LengthY

        return uvw

    def getMaterialName (self, obj):
        """
        get the name of the material of the object or of the object's parents
        """
        texTag = self.findTag(obj, c4d.Ttexture)
        if texTag == None:
            parentObj = obj.GetUp()
            while parentObj != None:
                texTag = self.findTag(parentObj, c4d.Ttexture)
                if texTag != None:
                    break
                parentObj = parentObj.GetUp()

        materialName = "defaultMaterial"
        if texTag != None and texTag.GetMaterial() != None:
            materialName = self.getName(texTag.GetMaterial())

        return materialName

    #
    ################################################################################################


    ################################################################################################
    # XHTML

    def writeHeader(self):
        """
        Write standard XML3D header and attach it to self.doc
        @return body: Can be used to append more nodes
        """
        html = self.doc.createElementNS("http://www.w3.org/1999/xhtml", "html")
        html.setAttribute("xmlns", "http://www.w3.org/1999/xhtml")
        self.doc.appendChild(html)
        head = self.doc.createElement("head")
        title = self.doc.createElement("title")
        title.appendChild(self.doc.createTextNode("XML3D"))

        link = self.doc.createElement("link")
        link.setAttribute("href", "http://www.xml3d.org/xml3d/script/xml3d.css")
        link.setAttribute("media", "all")
        link.setAttribute("rel", "stylesheet")
        link.setAttribute("type", "text/css")

        head.appendChild(link)
        head.appendChild(title)
        html.appendChild(head)
        body = self.doc.createElement("body")
        html.appendChild(body)
        return body
    #
    ################################################################################################

    ################################################################################################
    # DEFS

    def writeMainDef(self, parent, scene):
        """
        Write transformations, light objects, polygon objects and materials
        @param parent: Parent object in graph
        @param scene: Contains the complete description of a scene
        (unpolygonized scene)
        """
        defElement = self.doc.createDefsElement()            
        parent.appendChild(defElement)
        self.writeTransformsAndLightAndPolys(defElement, scene.GetFirstObject())
        self.writeMaterials(defElement, scene.GetFirstMaterial())
        self.writeDefaultMaterial(defElement)


    def writeTransformsAndLightAndPolys(self, parent, obj, continueSameLevel = True):
        """
        Write transformations, light objects and polygon objects. We traverse the
        scene graph of the unpolygonized scene. The reason for this is that
        polygonizing a scene removes all non-polygon data. If we want export a
        polygon object, we have to search in the polygonized scene.
        @param parent: Parent object in graph
        @param obj: Start of hierarchical export
        """
        while obj != None:
            self.statusPercent = self.statusPercent + self.timeStep
            c4d.StatusSetBar(int(self.statusPercent * 100.0 + 0.5))
            self.writeTransform(parent, obj)
            if obj.GetType() == c4d.Olight:
                self.writeLightShader(parent, obj)
            else:
                polyObj = self.polygonizedScene.SearchObject(obj.GetName())
                if polyObj != None and polyObj.GetType() == c4d.Opolygon:
                    self.writeDataObject(parent, polyObj)
            self.writeTransformsAndLightAndPolys(parent, obj.GetDown())

            if continueSameLevel:
                obj = obj.GetNext()
            else:
                obj = None


    def writeParentTransforms(self, current, obj):
        """
        todo Add some comment here!
        """
        if obj != None :
          parentObj = obj.GetUp()
          if parentObj != None :
              self.writeParentTransforms(current, parentObj)
          self.writeTransform(current, obj)


    def writeTransform(self, parent, obj):
        """
        Write transformation: Translation, Scale, Rotation. The individual
        transformations will only be exported if it is necessary (e.g translation
        > 0.0f).
        @param parent: Parent object in graph
        @param obj: Start of hierarchical export
        """
        ax, angle = c4d.utils.MatrixToRotAxis(c4d.utils.HPBToMatrix(obj.GetRelRot()))
        pos = obj.GetRelPos()
        sca = obj.GetRelScale()

        epsilon = 0.00001
        isTranslated = math.fabs(pos.x) > epsilon or math.fabs(pos.y) > epsilon or math.fabs(pos.z) > epsilon
        isScaled = math.fabs(sca.x - 1.0) > epsilon or math.fabs(sca.y - 1.0) > epsilon or math.fabs(sca.z - 1.0) > epsilon
        isRotated = math.fabs(angle) > epsilon

        translateStr = None
        scaleStr = None
        rotateStr = None
        if isTranslated:
            translateStr = "%g %g %g" % (pos.z,pos.y,pos.x)
        if isScaled:
            scaleStr = "%g %g %g" % (sca.z,sca.y,sca.x)
        if isRotated:
            rotateStr = "%g %g %g %g" % (-ax.z,-ax.y,-ax.x,angle)
        transform = self.doc.createTransformElement("t_" + self.getName(obj),translateStr, scaleStr, rotateStr)
        parent.appendChild(transform)

    def writeLightShader(self, parent, obj):
        """
        Write light shader
        @param parent: Parent object in graph
        @param obj: Start of hierarchical export
        """
        lightType = obj[c4d.LIGHT_TYPE]
        scriptValue = "urn:xml3d:lightshader:directional"
        if lightType == c4d.LIGHT_TYPE_OMNI:
            scriptValue = "urn:xml3d:lightshader:point"
        elif lightType == c4d.LIGHT_TYPE_SPOT:
           scriptValue = "urn:xml3d:lightshader:spot"

        lightShaderElement = self.doc.createLightshaderElement("ls_" + self.getName(obj), scriptValue)
        parent.appendChild(lightShaderElement)

        shadowElement = self.doc.createBoolElement(None, "castShadow")
        if obj[c4d.LIGHT_SHADOWTYPE] != c4d.LIGHT_SHADOWTYPE_NONE:
            shadowElement.appendChild(self.doc.createTextNode("true"))
        else:
            shadowElement.appendChild(self.doc.createTextNode("false"))
        lightShaderElement.appendChild(shadowElement)

        falloffType = obj[c4d.LIGHT_DETAILS_FALLOFF]
        if falloffType == c4d.LIGHT_DETAILS_FALLOFF_NONE:
            atten0, atten1, atten2 = 1.0, 0.0, 0.0
        elif falloffType == c4d.LIGHT_DETAILS_FALLOFF_LINEAR:
            atten0, atten1, atten2 = 0.0, 1.0, 0.0
        else:
            atten0, atten1, atten2 = 0.0, 0.0, 1.0

        lightIntensity = obj[c4d.LIGHT_COLOR] * obj[c4d.LIGHT_BRIGHTNESS]
        lightShaderElement.appendChild(self.createFloat3TextElement("attenuation", "%g %g %g" % (atten0, atten1, atten2)))
        lightShaderElement.appendChild(self.createFloat3TextElement("intensity", "%g %g %g" % (lightIntensity.x, lightIntensity.y, lightIntensity.z)))
        if lightType == c4d.LIGHT_TYPE_SPOT:
            lightShaderElement.appendChild(self.createFloatTextElement("beamWidth", "%g" % self.convertRadians(obj[c4d.LIGHT_DETAILS_INNERANGLE])))
            lightShaderElement.appendChild(self.createFloatTextElement("cutOffAngle", "%g" % self.convertRadians(obj[c4d.LIGHT_DETAILS_OUTERANGLE])))

    def writeMaterials(self, parent, obj):
        """
        The method traverses the material graph and exports all materials.
        @param parent: Parent object in graph
        @param obj: Start of hierarchical export
        """
        while obj != None:
            self.statusPercent = self.statusPercent + self.timeStep
            c4d.StatusSetBar(int(self.statusPercent * 100.0 + 0.5))
            self.writeMaterial(parent, obj)
            self.writeMaterials(parent, obj.GetDown())
            obj = obj.GetNext()

    def writeMaterial(self, parent, obj):
        """
        Write single material.
        @param parent: Parent object in graph
        @param obj: Material
        """
        if obj == None:
            print ("Object is none Cannot export material")
            return

        ambient = self.monochromaticTransform(self.ambientWorld)
        diffuseColor = Vector(0.5,0.5,0.5)
        emissiveColor = Vector(0.0,0.0,0.0)
        specularColor = Vector(0.0,0.0,0.0)
        reflective = 0.0
        shininess = 0.2
        transparency = 0.0

        if obj[c4d.MATERIAL_USE_COLOR]:
            diffuseColor = obj[c4d.MATERIAL_COLOR_COLOR] * obj[c4d.MATERIAL_COLOR_BRIGHTNESS]
        if obj[c4d.MATERIAL_USE_LUMINANCE]:
            emissiveColor = obj[c4d.MATERIAL_LUMINANCE_COLOR] * obj[c4d.MATERIAL_LUMINANCE_BRIGHTNESS]
        if obj[c4d.MATERIAL_USE_SPECULARCOLOR]:
            specularColor = obj[c4d.MATERIAL_SPECULAR_COLOR] * obj[c4d.MATERIAL_SPECULAR_BRIGHTNESS]
        if obj[c4d.MATERIAL_USE_SPECULAR]:
            shininess = (obj[c4d.MATERIAL_SPECULAR_WIDTH] * obj[c4d.MATERIAL_SPECULAR_WIDTH])
        if obj[c4d.MATERIAL_USE_TRANSPARENCY]:
            transparency = obj[c4d.MATERIAL_TRANSPARENCY_BRIGHTNESS]
        if obj[c4d.MATERIAL_USE_REFLECTION]:
            reflective = obj[c4d.MATERIAL_REFLECTION_BRIGHTNESS]

        texture = obj[c4d.MATERIAL_COLOR_SHADER]
        if texture != None:
            mixStrength = obj[c4d.MATERIAL_COLOR_TEXTURESTRENGTH]
            if mixStrength < 1.0:
                diffuseColor = (1.0 - mixStrength) * diffuseColor
            else:
                diffuseColor = Vector(1,1,1)

        materialName = obj.GetName()
        # see if materials is used at all
        if materialName in self.usedMaterials:
            # check if material is not exported already
            if self.usedMaterials[materialName] < 2:
                if obj.GetName() == "envMapMat":
                    parent.appendChild(self.createEnvShader(self.getName(obj), texture))
                else:
                    parent.appendChild(self.createShader(self.getName(obj), ambient, diffuseColor, emissiveColor, specularColor, shininess, transparency, reflective, texture))
                self.usedMaterials[materialName] = 2

    def writeDefaultMaterial(self, parent):
        """
        Write default material. This material can be used for objects without
        attached texture tags.
        @param parent: Parent object in graph
        """
        ambient = 0.0
        diffuseColor = Vector(0.5,0.5,0.5)
        emissiveColor = Vector(0.0,0.0,0.0)
        specularColor = Vector(1.0,1.0,1.0)
        reflective = 0.0
        shininess = 0.2
        transparency = 0.0
        parent.appendChild(self.createShader("defaultMaterial",ambient,diffuseColor,emissiveColor,specularColor,shininess,transparency,reflective))

    def writeDataObject(self, parent, obj):
        """
        Write single mesh as data object. Exporting a mesh involves several steps:
        1. Generation of sharing faces data structure:
        sharingFaces[VERTEX_INDEX] = CORRESPONDING_FACE_INDEX
        2. Optimize vertex array:
        2.1. Remove isolated vertices from raw vertex array
        2.2. Update variable numVertices
        2.3. Correct vertex indices of polygon array
        2.4. Rebuild sharing faces data structure
        3. Create phong normals and search for uvw tag
        4. Iterate over vertices and check if all faces sharing current vertex:
        - Have same normal
        - Have same texture coordinate (if uvwTag was found)
        5. If both criteria are matched: Export vertex, normal and texture
        coordinate together with single index. Otherwise split face and
        duplicate data.
        6. Insert data into document
        @param parent: Parent object in graph
        @param obj: Mesh
        """
        materialName = self.getMaterialName(obj)
        self.usedMaterials[materialName] = 1

        # Create group
        group = self.doc.createDataElement("data_"+self.getName(obj))
        parent.appendChild(group)

        # Extract mesh
        polyCount = obj.GetPolygonCount()
        polygonIndices = obj.GetAllPolygons()
        rawVertices = obj.GetAllPoints()
        numVertices = obj.GetPointCount()

        # Generate sharing faces data structure
        sharingFaces = [ [] for i in xrange(numVertices) ]
        for i in range(0, polyCount):
            p = polygonIndices[i]
            sharingFaces[p.a].append(i)
            sharingFaces[p.b].append(i)
            sharingFaces[p.c].append(i)
            if p.c != p.d:
                sharingFaces[p.d].append(i)

        # Optimize vertex array:
        isolatedVertexCount = 0
        isolatedVertexCountArray = []
        vertices = []
        for i in range(0, numVertices):
            if len(sharingFaces[i]) > 0:
                vertices.append(rawVertices[i])
            else:
                isolatedVertexCount = isolatedVertexCount + 1
            isolatedVertexCountArray.append(isolatedVertexCount)
        if len(rawVertices) - len(vertices) > 0:
            for i in range(0, polyCount):
                p = polygonIndices[i]
                polygonIndices[i].a = p.a - isolatedVertexCountArray[p.a]
                polygonIndices[i].b = p.b - isolatedVertexCountArray[p.b]
                polygonIndices[i].c = p.c - isolatedVertexCountArray[p.c]
                polygonIndices[i].d = p.d - isolatedVertexCountArray[p.d]

            numVertices = len(vertices)
            sharingFaces = [ [] for i in xrange(numVertices) ]
            for i in range(0, polyCount):
                p = polygonIndices[i]
                sharingFaces[p.a].append(i)
                sharingFaces[p.b].append(i)
                sharingFaces[p.c].append(i)
                if p.c != p.d:
                    sharingFaces[p.d].append(i)

        normals = obj.CreatePhongNormals()
        uvwTag = self.findTag(obj, c4d.Tuvw)
        textureTag = self.findTag(obj, c4d.Ttexture)
        if uvwTag != None:
            if textureTag != None:
                LengthX = textureTag[c4d.TEXTURETAG_LENGTHX]
                LengthY = textureTag[c4d.TEXTURETAG_LENGTHY]
                # print (" x: %s" %(LengthX))
                # print (" y: %s" %(LengthY))
            else:
                # print ("Texturetag = None")
                LengthX = 1
                LengthY = 1

        #normals = None
        if normals != None:
            normalList = [ None for i in xrange(numVertices) ]
            texcoordList = [ None for i in xrange(numVertices) ]
            for i in range(0, numVertices):
                equal = True
                curNormal = None

                # Handle isolated vertices
                if len(sharingFaces[i]) == 0:
                    print ("Isolated vertex found")
                    continue

                for fidx in sharingFaces[i]:
                    p = polygonIndices[fidx]
                    if i == p.a:
                        tmpNormal = normals[fidx * 4]
                    elif i == p.b:
                        tmpNormal = normals[fidx * 4 + 1]
                    elif i == p.c:
                        tmpNormal = normals[fidx * 4 + 2]
                    else:
                        tmpNormal = normals[fidx * 4 + 3]
                    if curNormal == None:
                        curNormal = tmpNormal
                    else:
                        if math.fabs(curNormal.x - tmpNormal.x) > 0.0001 or math.fabs(curNormal.y - tmpNormal.y) > 0.0001 or math.fabs(curNormal.z - tmpNormal.z) > 0.0001:
                            equal = False
                            break

                if equal and uvwTag != None:
                    curUVW = None
                    for fidx in sharingFaces[i]:
                        p = polygonIndices[fidx]
                        uvw = self.modifytextureLenght ( LengthX, LengthY, fidx, uvwTag)
                        #uvw = uvwTag.GetSlow(fidx)
                        if i == p.a:
                            tmpUVW = uvw["a"]
                        elif i == p.b:
                            tmpUVW = uvw["b"]
                        elif i == p.c:
                            tmpUVW = uvw["c"]
                        else:
                            tmpUVW = uvw["d"]
                        if curUVW == None:
                            curUVW = tmpUVW
                        else:
                            if math.fabs(curUVW.x - tmpUVW.x) > 0.0001 or math.fabs(curUVW.y - tmpUVW.y) > 0.0001 or math.fabs(curUVW.z - tmpUVW.z) > 0.0001:
                                equal = False
                                break
                # Normals and tex coords are equal for all sharing faces.
                # A single index can be used in that case.
                if equal:
                    if curNormal == None:
                        print ("curNormal == None!!")
                    normalList[i] = ("%g %g %g " % (curNormal.z,curNormal.y,curNormal.x))
                    if uvwTag != None:
                        texcoordList[i] = ("%g %g" % (curUVW.x,1.0-curUVW.y))
                # Normals and/or tex coords are not equal for all sharing faces.
                # The vertex needs to be split up, so that each sharing face
                # gets its own vertex.
                else:
                    if curNormal == None:
                        print ("curNormal == None!!")
                    normalList[i] = ("%g %g %g " % (curNormal.z,curNormal.y,curNormal.x))
                    if uvwTag != None:
                        fidx = sharingFaces[i][0]
                        p = polygonIndices[fidx]
                        if LengthX == None:
                            LengthX = 1
                        if LengthY == None:
                            LengthY = 1
                        uvw = self.modifytextureLenght ( LengthX, LengthY, fidx, uvwTag)
                        if i == p.a:
                            texcoordList[i] = ("%g %g" % (uvw["a"].x,1.0-uvw["a"].y))
                        elif i == p.b:
                            texcoordList[i] = ("%g %g" % (uvw["b"].x,1.0-uvw["b"].y))
                        elif i == p.c:
                            texcoordList[i] = ("%g %g" % (uvw["c"].x,1.0-uvw["c"].y))
                        else:
                            texcoordList[i] = ("%g %g" % (uvw["d"].x,1.0-uvw["d"].y))

                    for k in range(1, len(sharingFaces[i])):
                        fidx = sharingFaces[i][k]
                        p = polygonIndices[fidx]
                        if uvwTag != None:
                            uvw = self.modifytextureLenght ( LengthX, LengthY, fidx, uvwTag)
                            if i == p.a:
                                texcoordList.append("%g %g" % (uvw["a"].x,1.0-uvw["a"].y))
                            elif i == p.b:
                                texcoordList.append("%g %g" % (uvw["b"].x,1.0-uvw["b"].y))
                            elif i == p.c:
                                texcoordList.append("%g %g" % (uvw["c"].x,1.0-uvw["c"].y))
                            else:
                                texcoordList.append("%g %g" % (uvw["d"].x,1.0-uvw["d"].y))

                        if i == p.a:
                            tmpNormal = normals[fidx * 4]
                            polygonIndices[fidx].a = len(vertices)
                        elif i == p.b:
                            tmpNormal = normals[fidx * 4 + 1]
                            polygonIndices[fidx].b = len(vertices)
                        elif i == p.c:
                            tmpNormal = normals[fidx * 4 + 2]
                            polygonIndices[fidx].c = len(vertices)
                        else:
                            tmpNormal = normals[fidx * 4 + 3]
                            polygonIndices[fidx].d = len(vertices)

                        # Split face
                        #if math.fabs(curNormal.x - tmpNormal.x) > 0.0001 or math.fabs(curNormal.y - tmpNormal.y) > 0.0001 or math.fabs(curNormal.z - tmpNormal.z) > 0.0001:
                        vertices.append(vertices[i])
                        if tmpNormal == None:
                            print ("tmpNormal == None!!")
                        normalList.append("%g %g %g " % (tmpNormal.z,tmpNormal.y,tmpNormal.x))

        if len(vertices) > 0 and polyCount > 0:
            indexList = []
            vertexList = []
            for vertex in vertices:
                vertexList.append("%g %g %g" % (vertex.z,vertex.y,vertex.x))
            for i in range(0, polyCount):
                p = polygonIndices[i]
                indexList.append(str(p.a))
                indexList.append(str(p.b))
                indexList.append(str(p.c))
                if p.c != p.d:
                    indexList.append(str(p.a))
                    indexList.append(str(p.c))
                    indexList.append(str(p.d))

            # Insert into document
            group.appendChild(self.createIntTextElement("index", ' '.join(indexList)))
            group.appendChild(self.createFloat3TextElement("position", ' '.join(vertexList)))

            if normals != None and len(normals) > 0:
                group.appendChild(self.createFloat3TextElement("normal", ''.join(normalList)))
                if uvwTag != None:
                   group.appendChild(self.createFloat2TextElement("texcoord", ' '.join(texcoordList)))
    #
    ################################################################################################

    ################################################################################################
    # VIEWs

    def writeView(self, parent, obj):
        """
        Write camera properties to buffer. Only the first camera will be set to
        active (self.cameraIdx == 0).
        @param parent: Parent object in graph
        @param obj: Camera object
        """
        posStr = "0.0 0.0 0.0"
        oriStr = "0.0 -1.0 0.0 1.570796"
        fov = 2.0 * math.atan(obj.GetAperture() / (2.0 * obj.GetFocus()));
        if self.cameraIdx == 0:
            cameraName = "defaultView"
            cameraActive = "true"
        else:
            cameraName = self.getName(obj)
            cameraActive = "false"
        self.cameraIdx += 1
        view = self.doc.createViewElement(cameraName, cameraActive, posStr, oriStr, "%g" % fov)
        group = self.doc.createGroupElement("group_"+self.getName(obj), "true", "#t_%s" % self.getName(obj))
        group.appendChild(view)
        parent.appendChild(group)
    #
    ################################################################################################

    ################################################################################################
    # Mesh

    def writeMeshNew(self, parent, obj, writeTransform = True):
        """
        Write mesh. Find a texture tag (:= attached material). The object itself
        can have such a tag or any object above in the scene graph can have one,
        which is automatically inherited.
        Create XML3D group element and reference mesh data element.
        @param parent: Parent object in graph
        @param obj: Mesh object
        @param writeTransform: If true the transformation will be exported
        @return: Reference to created XML3D group element
        """
        materialName = self.getMaterialName(obj)

        # Create group
        if writeTransform:
            group = self.doc.createGroupElement("group_"+self.getName(obj), "true", "#t_%s" % self.getName(obj), "#shader_%s" % materialName)
        else:
            group = self.doc.createGroupElement("group_"+self.getName(obj), "true", None, "#shader_%s" % materialName)
        mesh = self.doc.createMeshElement("mesh_%s" % self.getName(obj), "true", "triangles", "#data_"+self.getName(obj))
        group.appendChild(mesh)
        parent.appendChild(group)
        return group

    def findTag(self, obj, type):
        """
        Iterate over all tags of an object and find a specific type.
        @param obj: Object to be searched
        @param type: Type of interest
        @return: First tag matches type
        @return None: No tag found
        """
        tag = obj.GetFirstTag()
        while tag != None:
            if tag.GetType() == type:
                return tag
            tag = tag.GetNext()
        return None

    def findTagByName(self, obj, name):
        """
        Iterate over all tags of an object and find a specific name.
        @param obj: Object to be searched
        @param name: Name of interest
        @return: First tag matches name
        @return None: No tag found
        """
        tag = obj.GetFirstTag()
        while tag != None:
            if tag.GetName() == name:
                return tag
            tag = tag.GetNext()
        return None

    #
    ################################################################################################

    ################################################################################################
    # Lights

    def writeLight(self, parent, obj):
        """
        Write light by creating a XML3D group element and referencing to the
        corresponding light shader
        @param parent: Parent object in graph
        @param obj: Light object
        """
        group = self.doc.createGroupElement("group_%s" % self.getName(obj), "true", "#t_%s" % self.getName(obj), None)
        parent.appendChild(group)

        light = self.doc.createLightElement("light_%s" % self.getName(obj), "true", "#ls_%s" % self.getName(obj))
        group.appendChild(light)
        return group
    #
    ################################################################################################

    ################################################################################################
    # Scripts

    def writeScripts(self, parent):
        """
        Write script tag containing link to xml3d.js
        @param parent: Parent object in graph
        """
        location = "http://www.xml3d.org/xml3d/script/"
        type = "text/javascript"
        scripts = ["xml3d.js"]

        for script in scripts:
            scriptElem = self.doc.createScriptElement(None, location + script, type)
            parent.appendChild(scriptElem)
    #
    ################################################################################################

    def handleSpecialTags(self, xml3dObj, obj):
        """
        Treatment of special tags (e.g. XML3DMouseEventTag)
        This plugin provides a way to directly attach js code to a XML3D object
        @param xml3dObj: XML3D object to which the code will be attached
        @param obj: Corresponding Cinema4D object
        """
        # Search for special tag
        tag = obj.GetFirstTag()
        while tag != None:
            if tag.GetName() == 'XML3DMouseEventTag':
                if tag[c4d.ONCLICK] != None and tag[c4d.ONCLICK] != "":
                    xml3dObj.setAttribute("onclick", tag[c4d.ONCLICK])
                if tag[c4d.ONDBLCLICK] != None and tag[c4d.ONDBLCLICK] != "":
                    xml3dObj.setAttribute("ondblclick", tag[c4d.ONDBLCLICK])
                if tag[c4d.ONMOUSEDOWN] != None and tag[c4d.ONMOUSEDOWN] != "":
                    xml3dObj.setAttribute("onmousedown", tag[c4d.ONMOUSEDOWN])
                if tag[c4d.ONMOUSEUP] != None and tag[c4d.ONMOUSEUP] != "":
                    xml3dObj.setAttribute("onmouseup", tag[c4d.ONMOUSEUP])
                if tag[c4d.ONMOUSEOVER] != None and tag[c4d.ONMOUSEOVER] != "":
                    xml3dObj.setAttribute("onmouseover", tag[c4d.ONMOUSEOVER])
                if tag[c4d.ONMOUSEMOVE] != None and tag[c4d.ONMOUSEMOVE] != "":
                    xml3dObj.setAttribute("onmousemove", tag[c4d.ONMOUSEMOVE])
                if tag[c4d.ONMOUSEOUT] != None and tag[c4d.ONMOUSEOUT] != "":
                    xml3dObj.setAttribute("onmouseout", tag[c4d.ONMOUSEOUT])
                if tag[c4d.ONKEYPRESS] != None and tag[c4d.ONKEYPRESS] != "":
                    xml3dObj.setAttribute("onkeypress", tag[c4d.ONKEYPRESS])
                if tag[c4d.ONKEYDOWN] != None and tag[c4d.ONKEYDOWN] != "":
                    xml3dObj.setAttribute("onkeydown", tag[c4d.ONKEYDOWN])
                if tag[c4d.ONKEYUP] != None and tag[c4d.ONKEYUP] != "":
                    xml3dObj.setAttribute("onkeyup", tag[c4d.ONKEYUP])
            tag = tag.GetNext()


    def writeParentGroups(self, parent, obj):
        """
        todo Add some comment here!
        """
        if obj != None :
            parentObj = obj.GetUp()
            if parentObj != None :
                parent = self.writeParentGroups(parent, parentObj)
            group = self.doc.createGroupElement("group_"+self.getName(obj), "true", "#t_%s" % self.getName(obj), "#shader_%s" % self.getMaterialName(obj))
            parent.appendChild(group)
            parent = group
        return parent


    def writeSceneGraph(self, parent, rawObj, instanceObject, continueSameLevel = True):
        """
        Main exporting loop. Traversing scene graph and invoking correct methods
        to export several objects. Special care needs to be taken for exporting
        instances, see the comments in the code.
        @param parent: Parent object in graph
        @param rawObj: Current Cinema4D object
        @param instanceObject: Are we facing a instanced object?
        @param continueSameLevel: Continue at same level in hierarchy or one
        level deeper
        """
        while rawObj != None:
            # Update progress bar
            self.statusPercent = self.statusPercent + self.timeStep
            c4d.StatusSetBar(int(self.statusPercent * 100.0 + 0.5))

            # Export null object explicitely
            next = parent
            if rawObj.GetType() == c4d.Onull:
                next = self.writeNull(next, rawObj)
                self.handleSpecialTags(next, rawObj)
            # Export instance type
            elif rawObj.GetType() == c4d.Oinstance:
                next = self.writeNull(next, rawObj)
                self.handleSpecialTags(next, rawObj)
                linkedObj = rawObj[c4d.INSTANCEOBJECT_LINK]
                polyObj = self.polygonizedScene.SearchObject(linkedObj.GetName())
                # Export polygon without transformation of polygon
                if polyObj != None and polyObj.GetType() == c4d.Opolygon:
                    self.writeSceneGraph(next, linkedObj, True, False)
                # Export first non-instance object without the transformations
                # of instance types (already stored in this instance object)
                elif linkedObj.GetType() == c4d.Oinstance:
                    # Search first non-instance object
                    while linkedObj != None and linkedObj.GetType() == c4d.Oinstance:
                        linkedObj = linkedObj[c4d.INSTANCEOBJECT_LINK]

                    # Handle first non-instance object
                    if linkedObj != None:
                        polyObj = self.polygonizedScene.SearchObject(linkedObj.GetName())
                        # Handle polygon type
                        if polyObj != None and polyObj.GetType() == c4d.Opolygon:
                            self.writeSceneGraph(next, linkedObj, True, False)
                        # Handle null object
                        else:
                            linkedObj = linkedObj.GetDown()
                            while linkedObj != None:
                                self.writeSceneGraph(next, linkedObj, True, False)
                                linkedObj = linkedObj.GetNext()
                # Export children of linked null object
                else:
                    linkedObj = linkedObj.GetDown()
                    while linkedObj != None:
                        self.writeSceneGraph(next, linkedObj, False, False)
                        linkedObj = linkedObj.GetNext()
            # Export other types
            else:
                obj = self.polygonizedScene.SearchObject(rawObj.GetName())
                if obj != None:
                    if obj.GetType() == c4d.Opolygon:
                        next = self.writeMeshNew(parent, obj, not instanceObject)
                        self.handleSpecialTags(next, rawObj)
                    elif obj.GetType() == c4d.Olight:
                        next = self.writeLight(parent, obj)
                        self.handleSpecialTags(next, rawObj)
                    elif obj.GetType() == c4d.Ocamera:
                        next = self.writeView(parent, obj)
                        self.handleSpecialTags(next, rawObj)
                else:
                    print ("Not found in polygonized scene: %s (Type: %s)" % (rawObj.GetName(), self.getTypeAsString(rawObj)))
                    break

            self.writeSceneGraph(next, rawObj.GetDown(), instanceObject)
            if continueSameLevel:
                rawObj = rawObj.GetNext()
            else:
                rawObj = None

    def write(self, scene, width, height, embed, strategy):
        """
        Main function for exporting a scene
        @param scene: Contains the complete description of a scene.
        @param width: Width of rendering area
        @param height: Height of rendering area
        @param embed: Embed into XHTML
        @return True: Successfully exported scene
        @return False: May happen if the file is not accessible or an error is
        thrown within the main exporting loop
        """
        start_time = c4d.GeGetMilliSeconds()
        try:
            self.cameraIdx = 0
            self.ambientWorld = Vector(0,0,0)
            c4d.StatusSetText("Find world ambient constant")
            self.findWorldAmbient(scene.GetFirstObject())

            # dictionary of used materials as key (name of material) and value (usage of material)
            # usage = 1   material is used by some object to be exported
            # usage = 2   material was written to defs section
            self.usedMaterials = {}

            # dictionary with original names of the objects
            self.originalNames = {}

            c4d.StatusSetText("Cloning scene")
            # clone the scene to not disturb the original scene
            self.rawScene = scene.GetClone()
            # create some unique names and remove unnecessary spaces
            self.numObjects   = self.createUniqueAndValidNames(self.rawScene.GetFirstObject(), "object", 0)
            self.numMaterials = self.createUniqueAndValidNames(self.rawScene.GetFirstMaterial(), "material", 0)
#            self.mangleObjectNames(self.rawScene.GetFirstObject())
#            self.mangleObjectNames(self.rawScene.GetFirstMaterial())

            # derive a polygonized scene now, after raw scene has been prepared
            self.polygonizedScene = self.rawScene.Polygonize()
            # create unique names again, since polygonization creates new names (with spaces)
            self.mangleObjectNames(self.polygonizedScene.GetFirstObject())

            # get all active objects or the complete scene
            selectedObjects = []
            taggedObjects = []
            # export tagged objects separately
            if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED  or  strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                #  selected objects will be set to current tagged object
                taggedObjects = self.findTaggedObjects(self.rawScene.GetFirstObject())
                if taggedObjects == []:
                    print("No tagged objects found. Exporting nothing!")
                    return False
                sameLevel = False
            # export only selected objects
            elif strategy == self.XML3D_EXPORT_STRATEGY_SELECTED:
                taggedObjects.append(self.rawScene.GetFirstObject())
                selectedObjects = self.rawScene.GetActiveObjects(0)
                if selectedObjects == []:
                    print("No selected objects found. Exporting nothing!")
                    return False
                sameLevel = False
            # export whole scene
            else:
                taggedObjects.append(self.rawScene.GetFirstObject())
                selectedObjects.append(self.rawScene.GetFirstObject())
                if selectedObjects == []  or  taggedObjects == []:
                    print("No objects found. Exporting nothing!")
                    return False
                sameLevel = True

            # create a good filename that ends with .xhtml
            basefilename = self.createProperFilename(self.filename)
            filename = basefilename




            c4d.StatusSetText("Starting export")
            for taggedObject in taggedObjects:

                # the one tagged object is the selected one
                if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED  or  strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                    selectedObjects = []
                    selectedObjects.append(taggedObject)

                # set individual filename for export 
                if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED:
                    filename = "%s_%s.xhtml" % (re.sub(".xhtml", "", basefilename), self.originalNames[taggedObject.GetName()])
                if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                    filename = "%s_%s_defs.inc" % (re.sub(".xhtml", "", basefilename), self.originalNames[taggedObject.GetName()])
                # split files name
                # open the file
                try:
                    out = open(filename, 'w')
                except:
                    c4d.StatusSetText("Unable to open file")
                    print("Unable to open file %s" % filename)
                    return False

                self.doc = XML3DDocument()


                # only create a defs section for TAGGED_S export
                if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                    xml3dElem = self.doc.createXml3dElement("defs")
                else:
                    xml3dElem = self.doc.createXml3dElement("xml3DElem", activeView_="#defaultView")
                    xml3dElem.setAttribute("style", "width: %spx; height: %spx;" % (width, height))
                    xml3dElem.setAttribute("xmlns", "http://www.xml3d.org/2009/xml3d")

                if embed == True:
                    parent = self.writeHeader()
                    parent.appendChild(xml3dElem)
                else:
                    self.doc.appendChild(xml3dElem)
                
                # Ausgabe des Dateinamens
                print("Exporting to filename %s" % filename)

                self.statusPercent = 0.0
                self.timeStep = 1.0 / (2.0 * self.numObjects + self.numMaterials - 1.0)

                # create the base defs element
                defElement = self.doc.createDefsElement()

                xml3dElem.appendChild(defElement)

                # write all active objects to scene graph
                c4d.StatusSetText("Exporting transformations and shaders...")
                c4d.StatusSetBar(0)
                for selectedObject in selectedObjects:
                    if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED  or  strategy == self.XML3D_EXPORT_STRATEGY_SELECTED  or  strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                        if selectedObject != None :
                            self.writeParentTransforms(defElement, selectedObject.GetUp())
                    self.writeTransformsAndLightAndPolys(defElement, selectedObject, sameLevel)

                # write all materials
                c4d.StatusSetText("Exporting materials...")
                c4d.StatusSetBar(0)
                self.writeDefaultMaterial(defElement)
                self.writeMaterials(defElement, self.rawScene.GetFirstMaterial())
                c4d.StatusSetText("Write exported data to disk")
                
                # write individual files for split files export
                if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                    c4d.StatusSetText("Writing Defs")
                    self.doc.writexml(out, " ", " ", "\n");
                    out.close()
                   
                    # filename for groups part
                    filename = "%s_%s_group.inc" % (re.sub(".xhtml", "", basefilename), self.originalNames[taggedObject.GetName()])
                    try:
                        out = open(filename, 'w')
                    except:
                        c4d.StatusSetText("Unable to open file")
                        print("Unable to open file %s" % filename)
                        return False

                    self.doc = XML3DDocument()
                    xml3dElem = self.doc.createXml3dElement("groups")
                    self.doc.appendChild(xml3dElem)
                    
                # write scene graph
                c4d.StatusSetText("Exporting scene graph...")
                c4d.StatusSetBar(0)
                for selectedObject in selectedObjects:
                    if strategy == self.XML3D_EXPORT_STRATEGY_TAGGED  or  strategy == self.XML3D_EXPORT_STRATEGY_SELECTED  or  strategy == self.XML3D_EXPORT_STRATEGY_TAGGED_S:
                        if selectedObject != None :
                            xml3dElem = self.writeParentGroups(xml3dElem, selectedObject.GetUp())
                    self.writeSceneGraph(xml3dElem, selectedObject, False, sameLevel)

                if embed == True:
                    c4d.StatusSetText("Export scripts")
                    self.writeScripts(parent)

                # finish file groups
                c4d.StatusSetText("Write exported data to disk")
                self.doc.writexml(out, " ", " ", "\n");

                out.close()

                # ??????????? destroy the self.doc???



            elapsed = c4d.GeGetMilliSeconds() - start_time
            print("Exporting completed Comment by Joergi: %gms" % elapsed)
            c4d.StatusClear()
        except:
            print("Something went wrong. Will abort now")
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60
            return False
        return True
