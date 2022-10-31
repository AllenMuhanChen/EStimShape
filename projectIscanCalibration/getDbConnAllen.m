% function conn = getDbConn()
%     databaseName = 'alexandriya_180218_test';
%     serverAddress = '172.30.6.80';
%     conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
% end

function conn = getDbConnAllen()
    databaseName = 'allen_estimshape_train_221020';
    serverAddress = '172.30.6.80';
    conn = database(databaseName,'xper_rw','up2nite','Vendor','MySQL','Server',serverAddress);
end

