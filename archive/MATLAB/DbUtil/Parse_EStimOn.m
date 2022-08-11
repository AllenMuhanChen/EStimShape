function [eStimOn_msg_struct] = Parse_EStimOn(tstamp)
global conn;
%% Fetching data from database and converting to string
sqlQuery = "SELECT msg FROM behmsg WHERE tstamp="+tstamp;
eStimOn_msg = fetch(conn,sqlQuery);
eStimOn_msg = table2array(eStimOn_msg); string(eStimOn_msg);

%% Parsing XML
eStimOn_msg_struct = ParseXML_behmsg_EStimOn(eStimOn_msg);
end 