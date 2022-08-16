function conn = getDBconn(folderName)
    databaseName = 'allen_estimshape_ga_dev_220812';
    serverAddress = '172.30.6.80';
%     serverAddress = 'localhost';
    conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
    if exist('folderName','var')
        %logger(mfilename,folderName,['Connected to MySQL database: ' databaseName ' on ' serverAddress '.'],conn);
    end
end