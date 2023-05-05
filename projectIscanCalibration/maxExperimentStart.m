function [timestamp] = maxExperimentStart(conn)
%     global conn;
    sqlquery= 'SELECT MAX(tstamp) FROM BehMsg WHERE type=''ExperimentStart''';
    timestamp=fetch(conn,sqlquery);
    timestamp = table2array(timestamp);
    timestamp = cast(timestamp, "uint64");
end 