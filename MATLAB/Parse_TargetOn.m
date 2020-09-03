function targetOn_msg_struct = Parse_TargetOn(tstamp)

%Parse Target On
%   input: tstamp
%   output: datastruct
global conn;

sqlquery = "SELECT msg FROM behmsg WHERE type='TargetOn' AND tstamp="+tstamp;
sqlquery = convertStringsToChars(sqlquery);
targetOn_msg = fetch(conn,sqlquery);
targetOn_msg = string(table2array(targetOn_msg));
targetOn_msg_struct = ParseXML_behmsg_TargetOn(targetOn_msg);
end 





