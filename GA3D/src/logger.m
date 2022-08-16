function logger(from,exptId,message,conn)
    getPaths;
    tstamp = getPosixTimeNow;
    str = [num2str(tstamp) ': ' from ': ' message '\n'];

    fileID = fopen([logPath '/' exptId '.txt'],'a');
    fprintf(fileID,str);
    fclose(fileID);
    
    insertIntoSqlTable({tstamp [exptId ': ' from ': ' message]},{'tstamp','memo'},'ExpLog',conn);
end

