function logger(from,exptId,message,conn)
    getPaths;
    tstamp = getPosixTimeNow;
    str = [num2str(tstamp) ': ' from ': ' message '\n'];

    fileID = fopen([logPath '/' exptId '.txt'],'a');
    try
        fprintf(fileID,str);
        fclose(fileID);
        insertIntoSqlTable({tstamp [exptId ': ' from ': ' message]},{'tstamp','memo'},'ExpLog',conn);
    catch e
        disp("Warning, couldn't save log")
    end 
    
    
   
end

