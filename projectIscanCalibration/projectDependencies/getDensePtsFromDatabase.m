function dPts = getDensePtsFromDatabase(did,conn,folderName,genNum)
    setdbprefs('DataReturnFormat','numeric');
    id = fetch(conn,['select id from StimObjData where descriptiveId = ''' did{1} '''']);

    if exist(['/Users/Ramanujan/Dropbox/xper_sach7/xper-sach/densePts/' folderName '_g-' num2str(genNum) '/' num2str(id) '.dat'],'file')
        dPts = load(['/Users/Ramanujan/Dropbox/xper_sach7/xper-sach/densePts/' folderName '_g-' num2str(genNum) '/' num2str(id) '.dat']);
    elseif exist(['/Users/Ramanujan/Dropbox/xper_sach7/dist/densePts/' folderName '_g-' num2str(genNum) '/' num2str(id) '.dat'],'file')
        dPts = load(['/Users/Ramanujan/Dropbox/xper_sach7/dist/densePts/' folderName '_g-' num2str(genNum) '/' num2str(id) '.dat']);
    elseif exist(['/Users/Ramanujan/Dropbox/xper_sach7/dist/sach/densePts/' folderName '_g-' num2str(genNum) '/' num2str(id) '.dat'],'file')
        dPts = load(['/Users/Ramanujan/Dropbox/xper_sach7/dist/sach/densePts/' folderName '_g-' num2str(genNum) '/' num2str(id) '.dat']);
    else
        dPts = [];
    end
end