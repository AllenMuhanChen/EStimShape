function conn = getDBconn(folderName)
    databaseName = 'ram_180616_3dma';
    serverAddress = '172.30.6.27';
%     serverAddress = 'localhost';
    conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
    if exist('folderName','var')
        logger(mfilename,folderName,['Connected to MySQL database: ' databaseName ' on ' serverAddress '.'],conn);
    end
end