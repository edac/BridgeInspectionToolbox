import arcpy
from arcpy.sa import *
import os
arcpy.ClearWorkspaceCache_management()
arcpy.env.overwriteOutput = True
class Toolbox(object):
    def __init__(self):
        """Bridge Inspection Toolbox."""
        self.label = "Bridge Inspection Toolbox"
        self.alias = "Bridge Inspection Toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [CrackHeightEnhancement,DelaminationDetectionTool]


class CrackHeightEnhancement(object):
    def __init__(self):
        """Enhances Crack Height"""
        self.label = "Cracking Detection Tool"
        self.description = "This tool can be used to detect cracks on the wearing surface of a bridge deck."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        dsm = arcpy.Parameter(
        displayName="DSM",
        name="DSM",
        datatype="DEFile",
        parameterType="Required",
        direction="Input")

        orthophoto = arcpy.Parameter(
        displayName="Orthophoto",
        name="Orthophoto",
        datatype="DEFile",
        parameterType="Required",
        direction="Input")

        output_folder = arcpy.Parameter(
        displayName="Output Folder",
        name="Output Folder",
        datatype="DEFolder",
        parameterType="Required",
        direction="Input")

        parameters=[dsm,orthophoto,output_folder]

        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.AddMessage("Creating Hillshades")
        dsm=parameters[0].valueAsText
        orthophoto=parameters[1].valueAsText
        output_folder=parameters[2].valueAsText
        azimuth=45
        hillshade_list=[]
        while azimuth<=360:
            
            outRaster=os.path.join(output_folder,"hillshade"+str(azimuth)+'.img')
            arcpy.AddMessage("Creating Hillshade for azimuth:"+str(azimuth))
            hillshade_list.append(outRaster)
            arcpy.HillShade_3d(dsm, outRaster, azimuth, 45, False, 4)
            
            azimuth=azimuth+45
        arcpy.AddMessage("Creating Hillshade Average")
        
        hillshade_average = (Raster(hillshade_list[0]) + Raster(hillshade_list[1])+ Raster(hillshade_list[2])+ Raster(hillshade_list[3])+ Raster(hillshade_list[4])+ Raster(hillshade_list[5])+ Raster(hillshade_list[6])+ Raster(hillshade_list[7])) / 8
        

        #Orthophoto Albedo
        arcpy.AddMessage("Creating Orthophoto Average")
        orthophoto_average = CellStatistics(orthophoto, "MEAN", "DATA")
        #final
        arcpy.AddMessage("Creating Hillshade-Orthophoto Average")
        outFinal=(orthophoto_average+hillshade_average)/2
        
        enhanced_crack=os.path.join(output_folder,"enhanced_crack.img")
        outFinal.save(enhanced_crack)

        arcpy.AddMessage("Creating 5X5 Statistics")
        max5x5_out=FocalStatistics(dsm,NbrRectangle(5,5,'CELL'),'MAXIMUM',True)
        diff_mm=(max5x5_out-Raster(dsm))*1000
        arcpy.AddMessage("Creating diff_mm_cracks.img")
        outSetNull = SetNull(diff_mm,diff_mm, "VALUE >16")
        diff_mm_cracks=os.path.join(output_folder,"diff_mm_cracks.img")
        outSetNull.save(diff_mm_cracks)

        arcpy.AddMessage("Cleaning up Hillshade Files.")
        for hs_file in hillshade_list:
            arcpy.Delete_management(hs_file)

        return

class DelaminationDetectionTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Delamination Detection Tool"
        self.description = "This tool can be used to detect delamination on the subsurface of a bridge deck."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        tir_image = arcpy.Parameter(
            displayName="TIR Image",
            name="TIR Image",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")

        output_folder = arcpy.Parameter(
            displayName="Output Folder",
            name="Output Folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        spectral_detail = arcpy.Parameter(
            displayName="Spectral Detail",
            name="spectral_detail",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input", )
        spectral_detail.value =20

        spatial_detail = arcpy.Parameter(
            displayName="Spatial Detail", 
            name="spatial_detail", 
            datatype="GPLong",
            parameterType="Optional", 
            direction="Input", )
        spatial_detail.value = 20

        min_segment_size = arcpy.Parameter(
            displayName="Min Segment Size",
            name="min_segment_size",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input", )

        min_segment_size.value = 100

        
        parameters=[tir_image,output_folder,spectral_detail,spatial_detail,min_segment_size]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        tir_image=parameters[0].valueAsText
        output_folder=parameters[1].valueAsText
        spectral_detail=parameters[2].valueAsText
        spatial_detail=parameters[3].valueAsText
        min_segment_size=parameters[4].valueAsText
        Component_2='Component_2'
        arcpy.AddMessage("Running Pricipal Components on Thermal Image.")
        outPrincipalComp = PrincipalComponents(tir_image, 3)
        arcpy.AddMessage("Building Raster Layer for Component 2")
        arcpy.MakeRasterLayer_management(outPrincipalComp, Component_2, "", "", "2")
        arcpy.AddMessage("Running Segment Mean Shift on Component 2 Layer")
        seg_raster = SegmentMeanShift(Component_2, spectral_detail, spatial_detail, min_segment_size,"")
        arcpy.AddMessage("Setting any Value Greater Than 125 to 1 and All Others to 0")
        segments_con=Con(seg_raster,1,0,"Value>125")
        arcpy.AddMessage("Setting all 0 Values to Null")
        delamination_raster = SetNull(segments_con, segments_con, "VALUE = 0")
        arcpy.AddMessage("Crating Polygon of all true (1) values:")
        delamination_polygon=os.path.join(output_folder,'Delamination_Polygon.shp')
        arcpy.RasterToPolygon_conversion(delamination_raster, delamination_polygon, "SIMPLIFY","VALUE")
        return