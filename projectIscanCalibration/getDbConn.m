% function conn = getDbConn()
%     databaseName = 'alexandriya_180218_test';
%     serverAddress = '172.30.6.80';
%     conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
% end

function conn = getDbConn()
    databaseName = 'ram_161030_maskedStim';
    serverAddress = '172.30.6.27';
    conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
end

