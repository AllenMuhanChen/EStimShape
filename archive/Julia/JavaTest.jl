using Pkg
Pkg.add("JavaCall")

using JavaCall
JavaCall.addClassPath("/home/r2_allen/git/EStimShape/xper-train/dist/xper.jar")
JavaCall.addClassPath("/home/r2_allen/git/EStimShape/xper-train/dist/3d/xper_3d.jar")
JavaCall.addClassPath("/home/r2_allen/git/EStimShape/xper-train/dist/allen/xper_allen.jar")
JavaCall.addClassPath("/home/r2_allen/git/EStimShape/xper-train/dist/allen/noisyMStickPngGen.jar")
JavaCall.init()

## 
jlm = @jimport org.xper.allen.app.nafc.MStickGeneratorTwo
j_u_arrays = @jimport java.util.Arrays

numDistractorsTypes = ["1,2,3,4"]
numDistractorsNumTrials = ["0,10,0,0"]
sampleScaleUpperLim = 8
sampleRadiusLowerLim = 0
sampleRadiusUpperLim = 0
eyeWinSize = 8
choiceRadiusLowerLim=12
choiceRadiusUpperLim=12
distractorDistanceLowerLim=0
distractorDistanceUpperLim=0
distractorScaleUpperLim=sampleScaleUpperLim
numMMCategories=2
numQMDistractorsTypes=["0,1,2,3"]
numQMDistractorsNumTrials=["0,10,0,0"]
numQMCategoriesTypes=["1,2,3"]
numQMCategoresNumTrials=["10,0,0"]


#jcall(jlm,
#"main",
#JavaCall.jvoid,
#(jintArray,           jintArray,               jdouble,             jdouble,              jdouble,              jdouble,    jdouble,              jdouble,              jdouble,                    jdouble,                    jdouble,                 jint,            jintArray,             jintArray,               jintArray,             jintArray          ),
# numDistractorsTypes, numDistractorsNumTrials, sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim, distractorDistanceUpperLim, distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMCategoresNumTrials, numQMDistractorsTypes, numQMCategoresNumTrials
#)

@show jcall(jlm,
"main",
JavaCall.jvoid,
(Array{JavaCall.JString,1},),
string.([numDistractorsTypes, numDistractorsNumTrials, sampleScaleUpperLim, sampleRadiusLowerLim, sampleRadiusUpperLim, eyeWinSize, choiceRadiusLowerLim, choiceRadiusUpperLim, distractorDistanceLowerLim, distractorDistanceUpperLim, distractorScaleUpperLim, numMMCategories, numQMDistractorsTypes, numQMCategoresNumTrials, numQMDistractorsTypes, numQMCategoresNumTrials]))