%clear classes %#ok<CLCLS>


% javaaddpath('/Users/allenchen/Documents/GitHub/V1Microstim/xper-train')
% javaaddpath('/Users/allenchen/Documents/GitHub/V1Microstim/xper-train/dist/allen/xper_allen.jar')
% javaaddpath('/Users/allenchen/Documents/GitHub/V1Microstim/xper-train/xper-allen/class/org/xper/allen/specs/GaussSpec.class')


gaussSpec = org.xper.allen.specs.GaussSpec(double(0),double(0),double(0),double(0));
targetEyeWinCoords = org.xper.drawing.Coordinates2D(0,0);
targetEyeWinSize = 0;
duration = 0;
data = "bleh";

visualTrial = org.xper.allen.blockgen.VisualTrial(gaussSpec, targetEyeWinCoords, targetEyeWinSize, duration, data);
xml=visualTrial.toXml();
filepath = "/Users/allenchen/Documents/GitHub/V1Microstim/MATLAB/EStimSpecGen/test.xml";

org.xper.allen.app.simpleestim.EStimTestXMLGen.toXmlFile(xml, filepath);
org.xper.allen.app.simpleestim.SimpleEStimGenerator.main(filepath)


trialArrayList = java.util.ArrayList;
trialArrayList.add