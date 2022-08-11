function [message,nStim] = runProliferation_posthoc_occluded(folderName,gaInfo,postHocId,conn)
    genNum = gaInfo.genNum;
    nStim = gaInfo.stimAndTrial.nStim;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started for occluded posthoc.',conn);
    disp(message);

    if exist([stimPath '/' fullFolderPath '/stimIds.mat'],'file') == 0
        message = 'Parent IDs not found'; return;
    else
        load([stimPath '/' fullFolderPath '/stimIds.mat']);
        if isempty(parentIdsPosthoc) %#ok<NODEF>
            message = 'Parent IDs not found'; return;
        end
    end

    colnames = {'id','descId','javaspec','mstickspec','matspec','dataspec'};
    tableName = 'StimObjData';

    load('templateStimulus.mat');
    blankStim = templateStimulus;
    blankStim.id.type = 'blank';
    blankStim.id.descId = [fullFolderPath '_s-BLANK'];
    blankStim.id.tstamp = getPosixTimeNow;
    blankStim.id.linNum = 0;
    blankStim.id.genNum = genNum;

    matspec = savejson('',blankStim);
    javaspec = formatAsXML_javaspec(blankStim);
    mstickspec = blankStim.shape.mstickspec;
    dataspec = formatAsXML_dataspec(blankStim.id);
    insertIntoSqlTable({blankStim.id.tstamp,blankStim.id.descId,javaspec,mstickspec,matspec,dataspec},colnames,tableName,conn);

    blank = blankStim; %#ok<NASGU>

    logger(mfilename,folderName,'Blank inserted.',conn);

    load([stimPath '/' folderName '_tempColFit.mat']);
    nPosthoc = size(parentIdsPosthoc,2);

    currStimIds = cell(2,nPosthoc);
    stimuli = cell(2,nPosthoc);
    mstickspec_all = cell(2,nPosthoc);
    
    occluder_lb = nan(nStim*2,3);
    occluder_rt = nan(nStim*2,3);

    nVariantConds = 8;
    
    sppGenNum = input('Enter generation number of the sizePos posthoc: ');

    for linNum=1:2
        pIP = repmat(parentIdsPosthoc(linNum,:),nVariantConds,1);
        pIP = pIP(:);

        jj = 1;
        while jj <= nPosthoc*nVariantConds
            parentId = pIP{jj};
            parentStim = getStimParams(parentId);
            
            s = 1 + 8*floor((jj-1)/8);
            descId = [folderName '_g-' num2str(sppGenNum) '_l-' num2str(linNum) '_s-' num2str(s)];
            [dPts,occluderZpos] = getDpts(descId,conn);
            
            % SHAPE
            stim = parentStim;
            stim.shape.dPts = dPts;
            stim.shape.texture = 'SHADE';
            stim.shape.s = stim.shape.s;

            % MASK
            stim.mask = getMaskBasedOnDpts(dPts,[true true]);
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
            occluder_lb(nStim*(linNum-1) + jj,:,:) = stim.occluder.leftBottom;
            occluder_rt(nStim*(linNum-1) + jj,:,:) = stim.occluder.rightTop;

            % ID
            stim.id.linNum = linNum;
            stim.id.genNum = genNum;
            stim.id.stimNum = jj;
            stim.id.tstamp = getPosixTimeNow;
            stim.id.type = 'ga3d';
            stim.id.descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(jj)];
            stim.id.respMatrix = [];
            stim.id.parentId = parentId;
            stim.id.parentStim = parentStim;
            stim.id.tagForRand = false;
            stim.id.tagForMorph = false;
            stim.id.saveVertSpec = false;
            stim.id.posthocId = postHocId;
            stim.id.isOccluded = true;

            mstickspec_all{linNum,jj} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,jj} = stim.id.descId;
            stimuli{linNum,jj} = stim;

            jj = jj + 1;
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nVariantConds) ' occluded posthoc stimuli created.'],conn);
    end
    nStim = size(stimuli,2);

    [stimuli,occluder] = makeUniformOccluders(stimuli,occluder_lb,occluder_rt,[0.1 0.1 0.1]);
    saveStimuliToDb(stimuli,mstickspec_all,colnames,tableName,conn);
    saveOccluderToDb(occluder,fullFolderPath,conn);
    % updateMasksInDb(stimuli,conn);

    save([stimPath '/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([stimPath '/' fullFolderPath '/stimIds.mat'],'currStimIds','-append');

    save([secondaryPath '/stim/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'],'currStimIds','-append');

    fprintf('\n');
    message = ['Generated ' fullFolderPath '.'];
    logger(mfilename,folderName,['Proliferation for lighting variants posthoc finished. ' message],conn);
    
    hFigure = figure('position',[2590,396,1214,420],'color','w');
    for l=1:2
        for s=1:nStim
            stim = stimuli{l,s};
            % SAVE THUMBNAIL AND SCHEMATIC
            clf;
            h1 = subplot(121); h2 = subplot(122);
            plotStim(h1,h2,stim);
            plotStim_equalizeAxes([h1 h2]);
            screen2png([stimPath '/' fullFolderPath '/thumbnails/' stim.id.descId '.png'],hFigure);
            screen2png([secondaryPath '/stim/' fullFolderPath '/thumbnails/' stim.id.descId '.png'],hFigure);
        end
    end
    close(hFigure); 
end

function [dPts,occluderZpos] = getDpts(descId,conn)
    vert = getVertices_perStim(descId,conn);
    eval(['vert = [' char(vert{1})' '];']);
    uniquePoints = unique(vert,'rows');
    px = uniquePoints(:,1); py = uniquePoints(:,2); pz = uniquePoints(:,3);
    boundaryIdx = boundary(px,py,1);
    boundarpyts = [px(boundaryIdx) py(boundaryIdx)];
    boundarpyts = interparc(100,boundarpyts(:,1),boundarpyts(:,2),'spline');
    dPts = getDensePoints(boundarpyts,[],100);

    occluderZpos = max(pz);
end

function vert = getVertices_perStim(descId,conn)
    setdbprefs('DataReturnFormat','cellarray');
    vert = fetch(conn,['select vertspec from StimObjData_vert where descId = ''' descId '''' ]);
end