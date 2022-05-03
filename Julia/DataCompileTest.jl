using Pkg
#=
Pkg.add("MySQL")
Pkg.add("DBInterface")
Pkg.add("EzXML")
Pkg.add("XMLDict")
Pkg.add("DataFrames")
Pkg.add("DataFramesMeta")
Pkg.add("TimesDates")
Pkg.add("Dates")
=#
using MySQL
using DBInterface
using EzXML
using XMLDict
using DataFrames
using TimesDates
using Dates
using DataFramesMeta
include("./DBUtil.jl")

global conn = DbUtil.connect()
date = Date(2022,05,03)

#behMsg = DbUtil.getBehMsg(DbUtil.today)
behMsg = DbUtil.getBehMsg(date)
stimSpec = DbUtil.getStimSpec(date)
stimObjData = DbUtil.getStimObjData(date)
## DEMO Find all TrialStarts & TrialStops to find trials 
#df = DataFrame()
trialStarts = behMsg[behMsg.type .== "TrialStart", :tstamp]
trialStops = behMsg[behMsg.type .== "TrialStop", :tstamp]

#BALANCE trialStart and trialStop 
if length(trialStarts) != length(trialStops)

    #the first trialStop is before the first trialStop
    if first(trialStops) < first(trialStarts)
        popfirst!(trialStops);
    
    #the last trialStart is after the last trialStop
    elseif last(trialStart) > last(trialStops)
        pop!(trialStarts);
    end 
end

"""
Given a trialStart and trialStop time in microseconds, check if there are any tstamps in between trialStart and trialStop. return true if yes. return false if no. 
"""
function checkForMsgType(trialStart::Int64, trialStop::Int64, msgTypeTstamps::Vector{Int64})::Bool
    for msgTypeTstamp in msgTypeTstamps
        if msgTypeTstamp >= trialStart && msgTypeTstamp <= trialStop
            return true
        end
    end 
    return false
end

df = DataFrame();
df.trialStart = trialStarts
df.trialStop = trialStops

#trialComplete tstamps from behMsg. Filter down to where there is only trialCompletes between trialStarts and trialStops
trialCompletes = behMsg[behMsg.type .== "TrialComplete", :tstamp]
df = filter([:trialStart, :trialStop] => (x,y)->checkForMsgType(x,y,trialCompletes), df)
df.trialComplete = trialCompletes

#ChoiceSelectionSuccess tstamps from behMsg. Filter down to only where there is choiceSelectionSuccess
choiceSelectionSuccesses = behMsg[behMsg.type .== "ChoiceSelectionSuccess", :tstamp]
df = filter([:trialStart, :trialStop] => (x,y)->checkForMsgType(x,y,choiceSelectionSuccesses), df)
df.choiceSelectionSuccess = choiceSelectionSuccesses;

#stimSpecIds from behMsg trialCompletes
trialCompleteXml = filter([:tstamp] => x -> issubset(x,df.trialComplete), behMsg)
getStimSpecId = DbUtil.makeXMLParser(["stimSpecId"]);
stimSpecIds = parse.(Int64,getStimSpecId.(stimSpecsXml))
df.stimSpecId = stimSpecIds;

#StimSpec spec XML strings from stimSpecIds & stimSpec
stimSpecsDf = filter([:id] => x -> issubset(x, stimSpecIds), stimSpec);
df.stimSpec = stimSpecsDf[:,:spec]

#StimSpec data XML string from stimSpecIds % stimSpec
stimSpecDataDf = stimSpecsDf[:,:data]
df.stimSpecData = stimSpecDataDf

#choiceObjIds parsed from stimSpec xml 
getChoiceObjData = DbUtil.makeXMLParser(["choiceObjData", "long"])
choiceObjDataIds = getChoiceObjData.(df.stimSpec); #vector of vector of strings!
choiceObjDataIds = ((list) -> parse.(Int64, list)).(choiceObjDataIds); #broadcast anonymous function here to iterate over elements twice to parse this out.
df.choiceObjDataId = choiceObjDataIds;

#BUILDING DATAFRAME FOR export
data = DataFrame();

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
getQmp = DbUtil.makeXMLParser(["qualitativeMorphParameters","org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams",
"objCenteredPosQualMorph","newTangent"])



















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