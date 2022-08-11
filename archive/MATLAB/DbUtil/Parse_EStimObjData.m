function [stimObjData_table] = Parse_EStimObjData(id)
global conn;
sqlquery = sprintf("SELECT * FROM v1microstim.estimobjdata WHERE id=%u", id);
stimObjData_table = fetch(conn, sqlquery);
end