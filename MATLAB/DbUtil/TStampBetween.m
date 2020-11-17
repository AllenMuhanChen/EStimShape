function [type_tstamp] = TStampBetween(tstamp1,tstamp2, type)
%TSTAMPBETWEEN returns tstamp of a specified type between two tstamps in
%BehMsg
global conn;
sqlquery = sprintf("SELECT tstamp FROM behmsg WHERE type='%s' AND tstamp<%u AND tstamp>%u", type, tstamp2, tstamp1);
%sqlquery = 'SELECT tstamp FROM behmsg WHERE type="'+type+'" AND tstamp<'+tstamp2+' AND tstamp>'+tstamp1;
type_tstamp = fetch(conn,sqlquery);
type_tstamp = table2array(type_tstamp);
end

