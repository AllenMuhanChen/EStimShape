function message = getMstickSpec_3d(gaInfo,conn)
    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    load([stimPath '/' fullFolderPath '/stimParams.mat']);
    
    for l=1:2
        message = ['Fetching mstickspec from DB and saving in MAT for lineage ' num2str(l) '.'];
        logger(mfilename,folderName,message,conn); disp(message);
        for s=1:gaInfo.stimAndTrial.nStim
            descId = [fullFolderPath '_l-' num2str(l) '_s-' num2str(s)];
            mstickspec = getMstickspec_perStim(descId,conn);
            
            stimuli{l,s}.shape.mstickspec = mstickspec; %#ok<AGROW>
        end
    end
    save([stimPath '/' fullFolderPath '/stimParams.mat'],'stimuli','-append');
    message = ['All mstickspec fetched from DB and saved for ' fullFolderPath '.'];
    logger(mfilename,folderName,message,conn);
end

function mstickspec = getMstickspec_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    mstickspec = fetch(conn,['select mstickspec from StimObjData where descId = ''' descId '''' ]);
    mstickspec = mstickspec{1,1}{1};
end
