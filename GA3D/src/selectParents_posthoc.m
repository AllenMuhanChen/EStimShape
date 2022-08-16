function message = selectParents_posthoc(gaInfo,doManual,conn)
    getPaths;
    genNum = gaInfo.genNum;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    
    logger(mfilename,folderName,'Posthoc parents are being selected.',conn);

    load([stimPath '/' folderName '_tempColFit.mat']);

    ch = 1; % validatedInput('Same parents? (1/0): ',0:1);
    
    if ch && checkForPreviousPosthocs(gaInfo)
        load([stimPath '/' folderName '_g-' num2str(genNum) '/stimIds.mat']);
    else
        allStimuli = cell(size(collatedStimIds));

        for g=1:gaInfo.genNum
            load([stimPath '/' folderName '_g-' num2str(g) '/stimParams.mat']);
            allStimuli(:,(gaInfo.stimAndTrial.nStim*(g-1)+1):g*gaInfo.stimAndTrial.nStim) = stimuli;
        end

        stimToExclude = getStimToExclude(allStimuli); % the ids of disrupted stimuli

        nPosthoc = 4;
        parentIdsPosthoc = cell(2,nPosthoc);

        isSingleElectrode = size(collatedZRespLin1,2) == 1;

        for l=1:2
            % r = eval(['collatedZRespLin'  num2str(l) ';']);
            r = mean(squeeze(eval(['collatedRespLin'  num2str(l) ';'])),2);

            if isSingleElectrode
                if doManual
                    pPosthocIds = selectPosthocParents_1d_manual(r,stimToExclude(l,:));
                else
                    pPosthocIds = selectPosthocParents_1d(r,stimToExclude(l,:));
                end
            end

            parentIdsPosthoc(l,:) = collatedStimIds(l,sort(pPosthocIds));
        end
    end
    
    genNum = genNum + 1;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    cleanDirectories;

    currStimIds = {}; %#ok<NASGU> % this is saved
    save([stimPath '/' fullFolderPath '/stimIds.mat'],'currStimIds','parentIdsPosthoc');
    save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'],'currStimIds','parentIdsPosthoc');

    message = ['Parents saved for posthoc run; alias gen ' num2str(genNum)];
    logger(mfilename,folderName,message,conn);
end


function pPosthocIds = selectPosthocParents_1d(r,stimToExclude)
    stimToExclude = find(stimToExclude);

    decileGroups = [4 4 2];

    selectionVector    = [0 1 3];

    [~,ind]         = sort(r);
    deciled         = reshape(ind(:,1),size(ind,1)/sum(decileGroups),sum(decileGroups));

    pPosthocIds = [];

    startingBlockForGrouping = 1;
    for jj=1:length(selectionVector)
        blocksToGroup = decileGroups(jj);
        endingBlockForGrouping = startingBlockForGrouping + blocksToGroup - 1;
        stimToSample = deciled(:,startingBlockForGrouping:endingBlockForGrouping);
        stimToSample = stimToSample(:);
        stimToSample(ismember(stimToSample,intersect(stimToSample,stimToExclude))) = [];

        sampledStim = datasample(stimToSample,selectionVector(jj),'Replace',false);
        pPosthocIds = [pPosthocIds; sampledStim]; %#ok<*AGROW>

        startingBlockForGrouping = startingBlockForGrouping + blocksToGroup;
    end
end

function stimToExclude = getStimToExclude(allStimuli)
    stimToExclude = nan(size(allStimuli));
    for l=1:size(allStimuli,1)
        for s=1:size(allStimuli,2)
            stim = allStimuli{l,s};
            stimToExclude(l,s) = stim.id.isControl || (stim.id.posthocId > 0);
        end
    end
end

function postHocPresent = checkForPreviousPosthocs(gaInfo)
    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    load([stimPath '/' folderName '_g-' num2str(gaInfo.genNum) '/stimParams.mat']);
    postHocPresent = stimuli{1}.id.posthocId > 0; %#ok<USENS>
end