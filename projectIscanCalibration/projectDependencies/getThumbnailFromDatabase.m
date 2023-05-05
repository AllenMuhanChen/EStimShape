function I = getThumbnailFromDatabase(did,conn,folderName,genNum)
    setdbprefs('DataReturnFormat','numeric');
    id = fetch(conn,['select id from StimObjData where descriptiveId = ''' did{1} '''']);

    if exist(['/Users/Ramanujan/Dropbox/xper_sach7/xper-sach/images/' folderName '_g-' num2str(genNum) '/' num2str(id) '.png'],'file')
        I = imread(['/Users/Ramanujan/Dropbox/xper_sach7/xper-sach/images/' folderName '_g-' num2str(genNum) '/' num2str(id) '.png']);
    elseif exist(['/Users/Ramanujan/Dropbox/xper_sach7/dist/images/' folderName '_g-' num2str(genNum) '/' num2str(id) '.png'],'file')
        I = imread(['/Users/Ramanujan/Dropbox/xper_sach7/dist/images/' folderName '_g-' num2str(genNum) '/' num2str(id) '.png']);
    elseif exist(['/Users/Ramanujan/Dropbox/xper_sach7/dist/sach/images/' folderName '_g-' num2str(genNum) '/' num2str(id) '.png'],'file')
        I = imread(['/Users/Ramanujan/Dropbox/xper_sach7/dist/sach/images/' folderName '_g-' num2str(genNum) '/' num2str(id) '.png']);
    else
        I = [];
    end
end