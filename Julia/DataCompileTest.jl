using Pkg
Pkg.add("MySQL")
Pkg.add("DBInterface")
Pkg.add("EzXML")
Pkg.add("XMLDict")
Pkg.add("DataFrames")
Pkg.add("DataFramesMeta")
Pkg.add("TimesDates")
Pkg.add("Dates")
Pkg.add("Plots")
Pkg.add("Printf")

using MySQL
using DBInterface
using EzXML
using XMLDict
using DataFrames
using TimesDates
using Dates
using DataFramesMeta
using Printf
include("./DbUtil.jl")
include("./DataCompileUtil.jl")

global conn = DbUtil.connect()
date1 = Date(2022,05,9)
date2 = Date(2022,05,13)
dates = (date1,date2)

#behMsg = DbUtil.getBehMsg(DbUtil.today)
behMsg = DbUtil.getBehMsg(dates)
stimSpec = DbUtil.getStimSpec(dates)
stimObjData = DbUtil.getStimObjData(dates)
## DEMO Find all TrialStarts & TrialStops to find trials 
df = DataCompileUtil.compileTrainingData(behMsg, stimSpec, stimObjData)


data = DataFrame()
#Choices
choicesAsIndcs = parse.(Int64,filter([:tstamp,:type]=> (x,y)->issubset(x, df.choiceSelectionSuccess)&&y=="ChoiceSelectionSuccess", behMsg)[: ,:msg]).+ 1
#choicesAsIndcs = parse.(Int64,behMsg[behMsg.type .== "ChoiceSelectionSuccess", :msg]) .+1 #convert from 0-index to 1-index
choicesStimObjIds =getindex.(df.choiceObjDataId, choicesAsIndcs); #getindex is basically List.get(index) 
choicesStimObjDataDf = filter([:id]=> x->issubset(x,choicesStimObjIds), stimObjData)
choices = choicesStimObjDataDf[:, :data]
data.choice = choices;

#Noise
#NoiseType
getNoiseType = DbUtil.makeXMLParser(["noiseData","noiseType"])
data.noiseType = getNoiseType.(df.stimSpecData)
#noiseChanceBounds
getNoiseChanceBounds = DbUtil.makeXMLParser(["noiseData", "noiseChanceBounds", "double"])
noiseChanceBounds = getNoiseChanceBounds.(df.stimSpecData)
data.noiseChanceBounds = ((list)-> parse.(Float64, list)).(noiseChanceBounds)
#morph params
isObjectCenteredPositionFlag = DbUtil.makeXMLParser(["qualitativeMorphParameters","org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams",
"objectCenteredPositionFlag"])
isCurvatureRotationFlag = DbUtil.makeXMLParser(["qualitativeMorphParameters","org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams",
"curvatureRotationFlag"])
isRadProfileFlag = DbUtil.makeXMLParser(["qualitativeMorphParameters","org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams",
"radProfileFlag"])
data.objectCenteredPositionFlag = isObjectCenteredPositionFlag.(df.stimSpecData)
data.curvatureRotationFlag = isCurvatureRotationFlag.(df.stimSpecData)
data.radProfileFlag = isRadProfileFlag.(df.stimSpecData)

#Analyzing Specific QM
tstamp = 1652461503514337
getStimObjIds = DbUtil.makeXMLParser(["choiceObjData", "long"])
checkStimObjIds = x->issubset(tstamp,parse.(Int64,getStimObjIds(x)))
target = filter([:stimSpec]=>x->checkStimObjIds(x),df)
isRadProfileFlag.(target.stimSpecData)


## SAMPLE PLOTTING
using Plots
function plotChoices(data::DataFrame, title::String)
    numTrials = size(data,1) 
    numMatches = size(filter(x -> x=="Match", data.choice),1)
    numQM = size(filter(x -> x=="QM", data.choice),1)
    numRand = size(filter(x -> x=="RAND", data.choice),1)
    percentMatches = numMatches / numTrials;
    percentQM = numQM / numTrials;
    percentRand = numRand / numTrials;
    
    
    # y = [percentMatches, percentQM, percentRand]
    n = [numMatches, numQM, numRand]
    y = n./numTrials * 100
    p = plot(y, st=:bar, texts=[@sprintf("%.2f%%, n=%d", y[i],n[i]) for i in 1:size(y,1)], label=title)
    plot!(title=title)
    plot!(xticks=(1:3, ["Match","QM Distractor","Rand Distractor"]))
    return p
end 



#Choices: ALL
plot()
p1 = plotChoices(data, "Choice Percentage: ALL")

# Choices: Noisy
plot()
noisy = filter([:noiseType] => x->x!="NONE", data)
p2 = plotChoices(noisy, "Choice Percentage: Noisy Only")

# Choices: No Noise
plot()
notNoisy = filter([:noiseType] => x->x=="NONE", data)
p3 = plotChoices(notNoisy, "Choice Percentage")


## Morph params
objectCenteredMorphs = filter([:objectCenteredPositionFlag] => x->x=="true",data)
curvatureRotationMorphs = filter([:curvatureRotationFlag] => x->x=="true",data)
radProfileMorphs = filter([:radProfileFlag] => x->x=="true",data)

function plotChoices!(data::DataFrame, title::String)
    numTrials = size(data,1) 
    numMatches = size(filter(x -> x=="Match", data.choice),1)
    numQM = size(filter(x -> x=="QM", data.choice),1)
    numRand = size(filter(x -> x=="RAND", data.choice),1)
    percentMatches = numMatches / numTrials;
    percentQM = numQM / numTrials;
    percentRand = numRand / numTrials;
    
    
    # y = [percentMatches, percentQM, percentRand]
    n = [numMatches, numQM, numRand]
    y = n./numTrials * 100
    p = plot!(y, st=:bar,label=title, fillalpha =0.3)
    plot!(xticks=(1:3, ["Match","QM Distractor","Rand Distractor"]))
  
    return p
end 
plot()
plot!(title="Qualitative Morph Types")
plotChoices!(objectCenteredMorphs, "Object Centered Morph")
plotChoices!(curvatureRotationMorphs, "Curvature Rotation")
plotChoices!(radProfileMorphs, "Rad Profile Morph")

##Morph Param Singletons
objectCenteredMorphs = filter([:objectCenteredPositionFlag, :curvatureRotationFlag, :radProfileFlag] => (x,y,z)->x=="true"&& y=="false" && z=="false",data)
curvatureRotationMorphs = filter([:objectCenteredPositionFlag, :curvatureRotationFlag, :radProfileFlag] => (x,y,z)->x=="false"&& y=="true" && z=="false",data)
radProfileMorphs = filter([:objectCenteredPositionFlag, :curvatureRotationFlag, :radProfileFlag] => (x,y,z)->x=="false"&& y=="false" && z=="true",data)

plot()
plot!(title="Singleton Qualitative Morph Types")
plotChoices!(objectCenteredMorphs, "Object Centered Pos Morph ONLY")
plotChoices!(curvatureRotationMorphs, "Curvature Rotation Morph ONLY")
plotChoices!(radProfileMorphs, "Rad Profile Morph ONLY")





## 
#=
## DEMO SUBSET into xml of spec
stimObjData = DbUtil.getStimObjData(date)
getWidth = DbUtil.makeXMLParser(["dimensions","width"])
widthChecker = DbUtil.makeXMLChecker(getWidth, "8.0")

filter(:spec => widthChecker, stimObjData) #subset into where dimensions.width="8.0" in spec

## DEMO RETURN DATA FROM XML spec
df = DataFrame()
df.width = getWidth.(stimObjData.spec)

## DEMO MATCH IDS ACROSS TABLES
stimSpec = DbUtil.getStimSpec(date)
filter([:id] => x -> issubset(x, stimSpecIds), stimSpec)
=#