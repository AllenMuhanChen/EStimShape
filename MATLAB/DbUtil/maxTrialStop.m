function [timestamp] = maxTrialStop()
    global conn;
    sqlquery= 'SELECT MAX(tstamp) FROM behmsg WHERE type=''TrialStop''';
    timestamp=fetch(conn,sqlquery);
    timestamp = table2array(timestamp);
end 