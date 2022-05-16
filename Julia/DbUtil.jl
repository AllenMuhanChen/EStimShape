module DbUtil

export makeXMLParser, connect, conn, today, yesterday
using Pkg
Pkg.add("MySQL")
Pkg.add("DBInterface")
Pkg.add("EzXML")
Pkg.add("XMLDict")
Pkg.add("DataFrames")
Pkg.add("TimesDates")
Pkg.add("Dates")
Pkg.add("DataFramesMeta")

using MySQL
using DBInterface
using EzXML
using XMLDict
using DataFrames
using DataFramesMeta
using TimesDates
using Dates

defaultHost =  "mysql://172.30.6.80"
defaultSchema = "allen_estimshape_train_220503"
username = "xper_rw"
password = "up2nite"

today = DateTime(Dates.today());
## CONNECT
function connect()
    return global conn = DBInterface.connect(MySQL.Connection, defaultHost, username, password, db= defaultSchema)
end 
function connect(schema::String)
    return global conn = DBInterface.connect(MySQL.Connection, defaultHost, username, password, db=schema)
end 
function connect(host::String, schema::String)
    return global conn = DBInterface.connect(MySQL.Connection, host, username, password, db=schema)
end 

## DATETIME/UNIX TIME
datetime2epoch(x::DateTime) = (Dates.value(x) - Dates.UNIXEPOCH)*1_000
unix2date(x::Int64) = Dates.Date(Dates.unix2datetime(floor(Int64,(x)/1000000)))


## getStimSpec
function getStimSpec(timerange::Tuple{Int64, Int64})
    sql = "SELECT * FROM StimSpec WHERE id > ? && id < ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [timerange[1] timerange[2]]) |> DataFrame
    return results
end 
function getStimSpec(after::Int64)
    sql = "SELECT * FROM StimSpec WHERE id > ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [after]) |> DataFrame
    return results
end 
function getStimSpec(dateTime::DateTime)
    dayInMicros = datetime2epoch(DateTime(dateTime))
    nextDayInMicros = dayInMicros+24*60*60*1_000_000
    global conn = DbUtil.connect(defaultSchema)
    stimSpec = DbUtil.getStimSpec((dayInMicros,nextDayInMicros));
   return stimSpec
end
function getStimSpec(date::Date)
    return getStimSpec(DateTime(date))
end  
function getStimSpec(daterange::Tuple{Date, Date})
    firstDateTime = DateTime(daterange[1])
    lastDateTime = DateTime(daterange[2])

    firstDayInMicros = datetime2epoch(firstDateTime)
    lastDayInMicros = datetime2epoch(lastDateTime) + 24*60*60*1_000_000

    global conn = DbUtil.connect(defaultSchema)
    stimSpec = DbUtil.getStimSpec((firstDayInMicros,lastDayInMicros));

    return stimSpec;
end 

## getStimObjData
function getStimObjData(timerange::Tuple{Int64, Int64})
    sql = "SELECT * FROM StimObjData WHERE id > ? && id < ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [timerange[1] timerange[2]]) |> DataFrame
    return results
end 
function getStimObjData(after::Int64)
    sql = "SELECT * FROM StimObjData WHERE id > ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [after]) |> DataFrame
    return results
end 
function getStimObjData(dateTime::DateTime)
    dayInMicros = datetime2epoch(DateTime(dateTime))
    nextDayInMicros = dayInMicros+24*60*60*1_000_000
    global conn = DbUtil.connect(defaultSchema)
    behMsg = DbUtil.getStimObjData((dayInMicros,nextDayInMicros));
   return behMsg
end
function getStimObjData(date::Date)
    return getStimObjData(DateTime(date))
end  
function getStimObjData(daterange::Tuple{Date, Date})
    firstDateTime = DateTime(daterange[1])
    lastDateTime = DateTime(daterange[2])
    firstDayInMicros = datetime2epoch(firstDateTime)
    lastDayInMicros = datetime2epoch(lastDateTime) + 24*60*60*1_000_000
    global conn = DbUtil.connect(defaultSchema)
    stimObjData = DbUtil.getStimObjData((firstDayInMicros,lastDayInMicros));
    return stimObjData;
end 

## getBehMsg
function getBehMsg()
    sql = "SELECT * FROM BehMsg"
    results = DBInterface.execute(conn::MySQL.Connection, sql) |> DataFrame;
    return results
end 
function getBehMsg(timerange::Tuple{Int64, Int64})
    sql = "SELECT * FROM BehMsg WHERE tstamp > ? && tstamp < ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [timerange[1] timerange[2]]) |> DataFrame
    return results
end 
function getBehMsg(after::Int64)
    sql = "SELECT * FROM BehMsg WHERE tstamp > ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [after]) |> DataFrame
    return results
end 
function getBehMsg(dateTime::DateTime)
    dayInMicros = datetime2epoch(DateTime(dateTime))
    nextDayInMicros = dayInMicros+24*60*60*1_000_000
    global conn = DbUtil.connect(defaultSchema)
    behMsg = DbUtil.getBehMsg((dayInMicros,nextDayInMicros));
    return behMsg
end 
function getBehMsg(date::Date)  
   return getBehMsg(DateTime(date))
end 
function getBehMsg(daterange::Tuple{Date, Date})
    firstDateTime = DateTime(daterange[1])
    lastDateTime = DateTime(daterange[2])
    firstDayInMicros = datetime2epoch(firstDateTime)
    lastDayInMicros = datetime2epoch(lastDateTime) + 24*60*60*1_000_000
    global conn = DbUtil.connect(defaultSchema)
    behMsg = DbUtil.getBehMsg((firstDayInMicros,lastDayInMicros));
    return behMsg;
end 

## Experiment Start / Stop and utils for extracting data for most recent block
function getLastBlock()
    return (getMaxExperimentStart(), getMaxExperimentStop())
end
function getMaxExperimentStop()
    sql = "SELECT max(tstamp) FROM BehMsg WHERE type = 'ExperimentStop'"
    results = DBInterface.execute(conn::MySQL.Connection, sql) |> DataFrame;
    return results[1,1]
end 
function getMaxExperimentStart()
    sql = "SELECT max(tstamp) FROM BehMsg WHERE type = 'ExperimentStart'"
    results = DBInterface.execute(conn::MySQL.Connection, sql) |> DataFrame;
    return results[1,1]
end
"""
    Finds first trialStart of the most recent block and extracts the stimSpecId from the msg
"""
function getFirstStimSpecId(experimentStart::Int64)
    global conn = DbUtil.connect(defaultSchema)
    sql = " SELECT msg FROM BehMsg WHERE tstamp = (SELECT min(tstamp)) && type = 'TrialStart' && tstamp>?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [experimentStart]) |> DataFrame
    getStimSpecId = makeXMLParser(["stimSpecId"])
    return parse(Int64,getStimSpecId(results[1,1]))
end 


## XML PARSING / CHECKING
function makeXMLParser(tree::Vector{String})
    return function(xml_string::String)
         xml = parse_xml(xml_string)
         for attribute in tree
            xml = xml[attribute]
         end 
         return xml
        
     end 
end 

function makeXMLChecker(parser, val)
    return function(xml_string::String)
       return parser(xml_string) == val
    end 
end 

## ROUTINES

"""
Counts the number of trial completes on specified date in specified database schema. If no database schema is provided, default is DBUtil.defaultSchema
"""
function countTrialCompletes(Date, schema::String)
    dayInMicros = datetime2epoch(DateTime(Date))
    nextDayInMicros = dayInMicros+24*60*60*1_000_000
    global conn = DbUtil.connect(schema)
   
    behMsg = DbUtil.getBehMsg((dayInMicros,nextDayInMicros));

    trialCompletes = @subset(behMsg, :type .== "TrialComplete")
   return nrow(trialCompletes)
end 



end 
