function mainScript_mask_3d
    getPaths;

    load([rootPath '/currState.mat']);
    conn = getDBconn(folderName);

    logger(mfilename,folderName,['Experiment started. Id = ' fullFolderPath '.'],conn);
    
    disp(getMstickSpec_3d(gaInfo,conn));
    disp(getVertices_3d(gaInfo,conn));
    disp(runOccluders_3d(gaInfo,randStim.occluderColor,conn));

    close(conn); clearvars conn ans;
    save([rootPath '/currState.mat']);
end