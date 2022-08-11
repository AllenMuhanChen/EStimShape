
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

lastExperimentStart = DbUtil.getMaxExperimentStart()

behMsg = DbUtil.getBehMsg(lastExperimentStart)
#Issue here is that stimSpec and stimObjData ids are much earlier, during generation
## One solution to this problem is to get all stimSpec and stimObjData from the entire day.
#but this wastes space, and we may have to deal with data that shouldn't be there. 
date = unix2date(lastExperimentStart)
firstStimSpec = DbUtil.getFirstStimSpecId(lastExperimentStart)
stimSpec = DbUtil.getStimSpec(firstStimSpec)
stimObjData = DbUtil.getStimObjData(firstStimSpec)

df = DataCompileUtil.compileTrainingData(behMsg, stimSpec, stimObjData)