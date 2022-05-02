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
date = Date(2022,05,02)

#behMsg = DbUtil.getBehMsg(DbUtil.today)
behMsg = DbUtil.getBehMsg(date)

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

#Look for trialCompletes and filter df trials to only include trialCompletes, add trialCompletes to the dataframe. 
df = DataFrame();
df.trialStart = trialStarts
df.trialStop = trialStops

trialCompletes = behMsg[behMsg.type .== "TrialComplete", :tstamp]
df = filter([:trialStart, :trialStop] => (x,y)->checkForMsgType(x,y,trialCompletes), df)
df.trialCompletes = trialCompletes

#Filter for ChoiceSelectionSuccess
choiceSelectionSuccesses = behMsg[behMsg.type .== "ChoiceSelectionSuccess", :tstamp]
df = filter([:trialStart, :trialStop] => (x,y)->checkForMsgType(x,y,choiceSelectionSuccesses), df)
df.choiceSelectionSuccess = choiceSelectionSuccesses





















#TODO: Have to get stimSpec Id somehow
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
filter([:id] => x -> issubset(x, df.trialStart), stimObjData)

