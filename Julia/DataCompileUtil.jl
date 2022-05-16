

module DataCompileUtil
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

export compileTrainingData, checkForMsgType

    
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

"""
1. Collects all trialStarts and trialStops from behMsg
2. Corrects for misaligned trialStart-trialStop by: 
A) first making sure the first trialStart is before the first
    trialStop and the last trialStart is before the last trialStop.
B) Finding the first pair of misaligned trialStart-trialStop 
    and depending on whether there are excess trialStarts or trialStops
    removes the appropiate one
3. Parses through SQL msg and specs to get the wanted data and puts
    it in a data frame. 
"""
function compileTrainingData(behMsg, stimSpec, stimObjData)
    trialStarts = behMsg[behMsg.type .== "TrialStart", :tstamp]
    trialStops = behMsg[behMsg.type .== "TrialStop", :tstamp]
    
    #BALANCE trialStart and trialStop 
    
    #the first trialStop is before the first trialStart
    while first(trialStops) < first(trialStarts)
        popfirst!(trialStops);
    end 
        # the last trialStart is after the last trialStop
    while last(trialStarts) > last(trialStops)
        pop!(trialStarts);
    end 
    
    while size(trialStarts,1) != size(trialStops,1)
        if length(trialStarts) > length(trialStops)
            diffLength = length(trialStops) - length(trialStarts)
            firstBadTrial = findall(x->x==0, trialStarts[1:(end-diffLength)] .< trialStops)[1]
            deleteat!(trialStops, firstBadTrial)
        else #length(trialStops) > length(trialStarts)
            diffLength = length(trialStops) - length(trialStarts)
            firstBadTrial = findall(x->x==0, trialStops[1:(end-diffLength)] .> trialStarts)[1]
            deleteat!(trialStops, firstBadTrial)
        end 
    end 
    
    df = DataFrame();
    df.trialStart = trialStarts
    df.trialStop = trialStops
    
    #
    firstTrialStart = df[1,:trialStart]
    lastTrialStop = df[end,:trialStop]
    # behMsg = filter([:tstamp] => x -> x>=firstTrialStart && x<=lastTrialStop, behMsg)
    # firstStimSpec = filter([:tstamp]=>x->x==minimum(behMsg[:,:tstamp]), behMsg)
    # stimSpec = filter([:id]=> x -> x>=firstStimSpec,stimSpec)
    # stimObjData = filter([:id]=> x -> x>=firstStimSpec,stimObjData)
    
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
    stimSpecIds = parse.(Int64,getStimSpecId.(trialCompleteXml[:,:msg]))
    df.stimSpecId = stimSpecIds;
    
    #StimSpec spec XML strings from stimSpecIds & stimSpec
    stimSpecsDf = filter([:id] => x -> issubset(x, stimSpecIds), stimSpec);
    df.stimSpec = stimSpecsDf[:,:spec]
    
    #StimSpec data XML string from stimSpecIds % stimSpec
    stimSpecDataDf = stimSpecsDf[:,:data]
    df.stimSpecData = stimSpecDataDf
    
    #sampleObjId parsed from stimSpecXml
    getSampleObjDataId = DbUtil.makeXMLParser(["sampleObjData"])
    sampleObjDataIds = getSampleObjDataId.(df.stimSpec)
    sampleObjDataIds = parse.(Int64, sampleObjDataIds)
    df.sampleObjDataId = sampleObjDataIds

    #sampleObjData_SPEC
    sampleObjDataDf = filter([:id]=>x->issubset(x,df.sampleObjDataId), stimObjData)
    sampleObjDataSpec = sampleObjDataDf[:, :spec]
    df.sampleObjDataSpec = sampleObjDataSpec


    #choiceObjIds parsed from stimSpec xml 
    getChoiceObjDataId = DbUtil.makeXMLParser(["choiceObjData", "long"])
    choiceObjDataIds = getChoiceObjDataId.(df.stimSpec); #vector of vector of strings!
    choiceObjDataIds = ((list) -> parse.(Int64, list)).(choiceObjDataIds); #broadcast anonymous function here to iterate over elements twice to parse this out.
    df.choiceObjDataId = choiceObjDataIds
    
    #choiceObjData_DATA
    function getChoiceData(stimObjDataIds::Vector{Int64})
        choiceObjDataDf = filter([:id]=>x->issubset(x,stimObjDataIds),stimObjData) 
        choiceObjData = choiceObjDataDf[:,:data]
        return choiceObjData
    end 
    choiceObjDataData = getChoiceData.(df.choiceObjDataId)
    df.choiceObjDataData = choiceObjDataData
    
    

    return df
end 

end 