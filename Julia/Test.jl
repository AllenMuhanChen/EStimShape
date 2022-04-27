using Pkg
Pkg.add("MySQL")
Pkg.add("DBInterface")
Pkg.add("EzXML")
Pkg.add("XMLDict")

using MySQL
using DBInterface
using EzXML
using XMLDict

MySQL.Connection
conn = DBInterface.connect(MySQL.Connection, "mysql://172.30.6.80", "xper_rw", "up2nite", db="allen_estimshape_dev_220404")

sql = "SELECT id FROM StimObjData";
results = DBInterface.execute(conn::MySQL.Connection, sql);

for row in results
    #@show propertynames(row)
    #println(row.id)
end 

sql = "SELECT MAX(id) FROM StimObjData";
results = DBInterface.execute(conn::MySQL.Connection, sql);

for row in results
    @show propertynames(row)
    println(row[1])
end



