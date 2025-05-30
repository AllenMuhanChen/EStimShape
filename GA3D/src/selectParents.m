function message = selectParents(gaInfo,conn)
    getPaths;
    genNum = gaInfo.genNum;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    nStim = gaInfo.stimAndTrial.nStim;

    getPaths;
    logger(mfilename,folderName,'Parents are being selected.',conn);

    load([stimPath '/' folderName '_tempColFit.mat']);

    currStimIds = {}; %#ok<NASGU> % this is saved

    allStimuli = cell(size(collatedStimIds));

    for g=1:gaInfo.genNum
        load([stimPath '/' folderName '_g-' num2str(g) '/stimParams.mat']);
        allStimuli(:,(gaInfo.stimAndTrial.nStim*(g-1)+1):g*gaInfo.stimAndTrial.nStim) = stimuli;
    end

    stimToExclude = getStimToExclude(allStimuli); % the ids of disrupted stimuli

    nMorph   = 0.4 * nStim;
    nControl = 0.5 * nStim / 4;

    parentIdsMorph = cell(2,nMorph);
    parentIdsControl = cell(2,nControl);

    isSingleElectrode = size(collatedZRespLin1,2) == 1;

    for l=1:2
        % r = eval(['collatedZRespLin'  num2str(l) ';']);
        r = mean(squeeze(eval(['collatedRespLin'  num2str(l) ';'])),2);

        if isSingleElectrode
            [pMorphIds,pControlIds] = selectParents_1d(r,nMorph,nControl,stimToExclude(l,:),nStim);
        else
            f = selectParents_getFitness(r);
            pMorphIds  = selectParents_core(f,nMorph,genNum);
        end

        parentIdsMorph(l,:) = collatedStimIds(l,sort(pMorphIds));
        parentIdsControl(l,:) = collatedStimIds(l,sort(pControlIds));
    end

    genNum = genNum + 1;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    cleanDirectories;

    save([stimPath '/' fullFolderPath '/stimIds.mat'],'currStimIds','parentIdsMorph','parentIdsControl');
    try
        save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'],'currStimIds','parentIdsMorph','parentIdsControl');
    catch
        disp("Could not save to Secondary Path")
    end
    message = ['Parents saved for gen ' num2str(genNum)];
    logger(mfilename,folderName,message,conn);
end

function pMorphIds = selectParents_core(f,nMorph,genNum)
    % ================= MORPH ============================
    % initialize fitness space for morph
    ellipticalSpaceCoeff = 0.15 * (genNum + 1); % based on 0.5 for g=1, and 3 for g=11;

    nBinsRA = 10;
    nBinsK  = 10;
    nBins   = [nBinsK,nBinsRA];

    % find fitness space for morph
    fitnessSpace(:,1) = f.r .* f.a;
    fitnessSpace(:,2) = f.k;

    % bin stimuli
    edges{1} = linspace(min(fitnessSpace(:,1)),max(fitnessSpace(:,1)),nBinsRA+1);
    edges{2} = linspace(min(fitnessSpace(:,2)),max(fitnessSpace(:,2)),nBinsK+1);

    [~,bin(:,2)] = histc(fitnessSpace(:,1),edges{1});
    [~,bin(:,1)] = histc(fitnessSpace(:,2),edges{2});

    bin(bin(:,2) > nBinsRA,2) = nBinsRA;
    bin(bin(:,1) > nBinsK,1) = nBinsK;

    % make probability matrix for space

    [t1,t2] = meshgrid(1:nBins(2),1:nBins(1));
    probSelectionPerBin = floor(10*sqrt((t1/nBins(1)/ellipticalSpaceCoeff).^3 + (t2/nBins(2)).^3)/sqrt(3))/10;
    probSelectionPerBin = probSelectionPerBin/max(probSelectionPerBin(:));

    % find selection prob for each stimulus
    selectionProbPerStim = probSelectionPerBin(sub2ind(nBins,bin(:,1),bin(:,2)));

    % select morph parents
    pMorphIds = randsample(1:length(selectionProbPerStim),nMorph,true,selectionProbPerStim)';
end

function [pMorphIds,pControlIds] = selectParents_1d(r,nMorph,nControl,stimToExclude,nStim)
    stimToExclude = find(stimToExclude);

    decileGroups = [3 2 2 2 1];

    selectionVectorMorph    = [1/16 2/16 3/16 4/16 6/16];
    selectionVectorMorph    = selectionVectorMorph * nMorph;

    % selectionVectorControl  = [0 0 0 1*nControl/5 4*nControl/5];

    [~,ind]         = sort(r);
    deciled         = reshape(ind(:,1),size(ind,1)/sum(decileGroups),sum(decileGroups));

    pMorphIds = [];
    % pControlIds = [];

    startingBlockForGrouping = 1;
    for jj=1:length(selectionVectorMorph)
        blocksToGroup = decileGroups(jj);
        endingBlockForGrouping = startingBlockForGrouping + blocksToGroup - 1;
        stimToSample = deciled(:,startingBlockForGrouping:endingBlockForGrouping);
        stimToSample = stimToSample(:);
        stimToSample(ismember(stimToSample,intersect(stimToSample,stimToExclude))) = [];

        if isempty(stimToSample)
            stimToSample = deciled(:,(startingBlockForGrouping-1):endingBlockForGrouping);
            stimToSample = stimToSample(:);
            stimToSample(ismember(stimToSample,intersect(stimToSample,stimToExclude))) = [];
        end
        
        sampledStim = datasample(stimToSample,selectionVectorMorph(jj));
        pMorphIds = [pMorphIds; sampledStim]; %#ok<*AGROW>

        % sampledStim = datasample(stimToSample,selectionVectorControl(jj),'Replace',false);
        % pControlIds = [pControlIds; sampledStim]; %#ok<*AGROW>

        startingBlockForGrouping = startingBlockForGrouping + blocksToGroup;
    end

    % instead of probabilistically picking controls, just pick the top
    % nControls stimuli from the last generation's non-control stimuli
    % (morphs and random).
    
    % TODO: if a posthoc has been run, remove those also (like controls are
    % removed) before selecting parents for controls.
    nNonControl = nStim - nControl*4;
    lastGenNonControls = nan(size(r));
    
    if (length(r) == nStim) % first generation
        lastGenNonControls = r;
        [~,idxForControl] = sort(lastGenNonControls,'descend');
        pControlIds = idxForControl(1:nControl);
    else
        lastGenNonControls(end-nStim+1:end-nControl*4) = r(end-nStim+1:end-nControl*4);
        [~,idxForControl] = sort(lastGenNonControls);
        pControlIds = idxForControl(nNonControl-nControl+1:nNonControl);
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
