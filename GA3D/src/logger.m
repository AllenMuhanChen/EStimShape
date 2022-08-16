function logger(from,exptId,message,conn)
    getPaths;
    tstamp = getPosixTimeNow;
    str = [num2str(tstamp) ': ' from ': ' message '\n'];

    fileID = fopen([logPath '/' exptId '.txt'],'a');
    try
        fprintf(fileID,str);
        fclose(fileID);
    catch e
        disp("Warning, couldn't save log")
    end 
    
    
    insertIntoSqlTable({tstamp [exptId ': ' from ': ' message]},{'tstamp','memo'},'ExpLog',conn);
end

