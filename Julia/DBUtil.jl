module DbUtil

export makeXMLParser, connect, conn
using Pkg
Pkg.add("MySQL")
Pkg.add("DBInterface")
Pkg.add("EzXML")
Pkg.add("XMLDict")
Pkg.add("DataFrames")
Pkg.add("TimesDates")
Pkg.add("Dates")

using MySQL
using DBInterface
using EzXML
using XMLDict
using DataFrames
using TimesDates
using Dates

defaultHost =  "mysql://172.30.6.80"
defaultSchema = "allen_estimshape_dev_220404"
username = "xper_rw"
password = "up2nite"

function connect()
    return global conn = DBInterface.connect(MySQL.Connection, defaultHost, username, password, db= defaultSchema)
end 
function connect(schema::String)
    return global conn = DBInterface.connect(MySQL.Connection, defaultHost, username, password, db=schema)
end 
function connect(host::String, schema::String)
    return global conn = DBInterface.connect(MySQL.Connection, host, username, password, db=schema)
end 

function getBehMsg()
    sql = "SELECT * FROM BehMsg"
    results = DBInterface.execute(conn::MySQL.Connection, sql) |> DataFrame;
    return results
end 
function getBehMsg(after::Int64)
    sql = "SELECT * FROM BehMsg WHERE tstamp > ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [after]) |> DataFrame
    return results
end 
function getBehMsg(timerange::Tuple{Int64, Int64})
    sql = "SELECT * FROM BehMsg WHERE tstamp > ? && tstamp < ?"
    statement = DBInterface.prepare(conn::MySQL.Connection, sql);
    results = DBInterface.execute(statement, [timerange[1] timerange[2]]) |> DataFrame
    return results
end 


function makeXMLParser(tree::Vector{String})
    return function(xml_string::String)
         xml = parse_xml(xml_string)
         for attribute in tree
            xml = xml[attribute]
         end 
         return xml
        
     end 
end 






end 