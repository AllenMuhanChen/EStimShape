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

include("./DBUtil.jl")


## CONNECT TO DB & PREPARE STATEMENT
global conn;
connect()
sql = "SELECT spec FROM StimObjData WHERE id=1649102620041630";

# DEMOS FOR PARSING RESULTS

## DEMO FOR ITERATING OVER RESULT SET
results = DBInterface.execute(conn::MySQL.Connection, sql);
for row in results
    #@show propertynames(row)
    xml_string = row.spec
    xml = parse_xml(xml_string)

    @show xml["dimensions"]["width"]
end 

## DEMO FOR USING DATAFRAME
results = DBInterface.execute(conn::MySQL.Connection, sql) |> DataFrame;
xml_string = results[1,:spec]
xml = parse_xml(xml_string)
@show xml["dimensions"]["width"]

## DEMO WITH MAKEXMLPARSER
xmlFunc = makeXMLParser(["dimensions","width"])
@show xmlFunc(xml_string)




