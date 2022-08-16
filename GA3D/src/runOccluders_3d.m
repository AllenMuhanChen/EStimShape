function message = runOccluders_3d(gaInfo,occluderColor,conn)
    nStim = gaInfo.stimAndTrial.nStim;
    genNum = gaInfo.genNum;

    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(genNum)];

    cleanDirectories;

    logger(mfilename,folderName,'Masking started.',conn);

    load([stimPath '/' fullFolderPath '/stimParams.mat']);

    occluder_lb = nan(nStim*2,3);
    occluder_rt = nan(nStim*2,3);

    hFigure = figure('position',[2590,396,1214,420],'color','w');
    for linNum = 1:2
        for stimNum = 1:nStim
            % LOAD DPTS
            load([stimPath '/' fullFolderPath '/vert/' fullFolderPath '_l-' num2str(linNum) '_s-' num2str(stimNum) '_vert']);

            % GET STIM
            stim = stimuli{linNum,stimNum};

            % SHAPE
            stim.shape.dPts = dPts;

            % MASK
            stim.mask = getMaskBasedOnDpts(dPts,[stim.mask.isActive]);
            stim.mask(1).z = occluderZpos;
            stim.mask(2).z = occluderZpos;
            if isempty(stim.mask)
                stim.id.isOccluded = false;
            end

            % OCCLUDER
            limitPoints = dPts;
            limitPoints = [limitPoints; [stim.mask(1).x stim.mask(1).y] + stim.mask(1).s]; %#ok<AGROW>
            limitPoints = [limitPoints; [stim.mask(1).x stim.mask(1).y] - stim.mask(1).s]; %#ok<AGROW>
            limitPoints = [limitPoints; [stim.mask(2).x stim.mask(2).y] + stim.mask(2).s]; %#ok<AGROW>
            limitPoints = [limitPoints; [stim.mask(2).x stim.mask(2).y] - stim.mask(2).s]; %#ok<AGROW>
            stim.occluder.leftBottom = [min(limitPoints) occluderZpos];
            stim.occluder.rightTop = [max(limitPoints) occluderZpos];
            occluder_lb(nStim*(linNum-1) + stimNum,:,:) = stim.occluder.leftBottom;
            occluder_rt(nStim*(linNum-1) + stimNum,:,:) = stim.occluder.rightTop;

            % ID
            stim.id.tagForRand = 0;
            stim.id.tagForMorph = 0;
            stim.id.isOccluded = true;

            % SAVE TO MAT FILE
            stimuli{linNum,stimNum} = stim; %#ok<AGROW>

            % SAVE THUMBNAIL AND SCHEMATIC
            clf;
            h1 = subplot(121); h2 = subplot(122);
            plotStim(h1,h2,stim);
            plotStim_equalizeAxes([h1 h2]);
            screen2png([stimPath '/' fullFolderPath '/thumbnails/' stim.id.descId '.png'],hFigure);
            screen2png([secondaryPath '/stim/' fullFolderPath '/thumbnails/' stim.id.descId '.png'],hFigure);
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nStim) ' masks created.'],conn);
    end
    close(hFigure);

    [stimuli,occluder] = makeUniformOccluders(stimuli,occluder_lb,occluder_rt,occluderColor);
    saveOccluderToDb(occluder,fullFolderPath,conn)
    updateMasksInDb(stimuli,conn);

    save([stimPath '/' fullFolderPath '/stimParams.mat'], 'stimuli','-append');
    save([secondaryPath '/stim/' fullFolderPath '/stimParams.mat'], 'stimuli','-append');

    message = ['Masks and occluders saved for ' fullFolderPath '.'];
    logger(mfilename,folderName,message,conn);
end
