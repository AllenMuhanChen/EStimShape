function stimObjData_struct = Parse_StimObjData(tstamp)
global conn;

sqlquery = "SELECT spec FROM stimobjdata WHERE id="+tstamp;
sqlquery = convertStringsToChars(sqlquery);
stimObjData_msg = fetch(conn, sqlquery);
stimObjData_msg = string(table2array(stimObjData_msg));
stimObjData_struct = ParseXML_stimObjData(stimObjData_msg);
end 