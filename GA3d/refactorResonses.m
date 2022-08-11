function message = refactorResonses(gaInfo,conn)
    genNum = gaInfo.genNum;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    nStim = gaInfo.stimAndTrial.nStim;
    getPaths;
    logger(mfilename,folderName,'Saving responses in respective stim files.',conn);

    load([respPath '/' folderName '_g-' num2str(genNum) '/resp.mat']);
    fullResp = resp; %#ok<NODEF>
    resp = resp(:,unitStat==1,:);

    if exist([stimPath '/' folderName '_g-' num2str(genNum) '/stimParams.mat'],'file')
        load([stimPath '/' folderName '_g-' num2str(genNum) '/stimParams.mat']);
    else
        message = 'Resp file does not exist.';
        return;
    end

    for l=1:2
        disp(['Refactoring lineage ' num2str(l) '.'])
        for s=1:nStim
            stimuli{l,s}.id.respMatrix = squeeze(resp((l-1)*nStim + s,:,:)); %#ok<*AGROW>
        end
        logger(mfilename,folderName,['Lin ' num2str(l) ' stim responses saved.'],conn);
    end

    fullBlankResp = blankResp; %#ok<NODEF>
    blankResp = blankResp(:,unitStat==1,:); %#ok<*NASGU>
    save([stimPath '/' folderName '_g-' num2str(genNum) '/stimParams.mat'],'stimuli','-append');
    save([respPath '/' folderName '_g-' num2str(genNum) '/resp.mat'], 'resp','blankResp','fullResp','fullBlankResp','unitStat','-append');
    
    save([secondaryPath '/stim/' folderName '_g-' num2str(genNum) '/stimParams.mat'],'stimuli','-append');
    save([secondaryPath '/resp/' folderName '_g-' num2str(genNum) '/resp.mat'], 'resp','blankResp','fullResp','fullBlankResp','unitStat','-append');

    if exist([stimPath '/' folderName '_tempColFit.mat'], 'file')
        load([stimPath '/' folderName '_tempColFit.mat']);
    else
        collatedRespLin1 = [];
        collatedRespLin2 = [];
        collatedZRespLin1 = [];
        collatedZRespLin2 = [];
        collatedStimIds = {};
    end

    load([stimPath '/' folderName '_g-' num2str(genNum) '/stimIds.mat']);
    
    collatedRespLin1 = [collatedRespLin1; resp(1:nStim,:,:)];
    collatedRespLin2 = [collatedRespLin2; resp(nStim+1:nStim*2,:,:)];
    
    m = nanmean(resp,3);
    s = nanstd(resp,[],3);
    mb = squeeze(nanmean(blankResp,3));
    sb = squeeze(nanstd(blankResp,[],3));
    
    r = (m-repmat(mb,nStim*2,1))./(s+repmat(sb,nStim*2,1));
    
    collatedZRespLin1 = [collatedZRespLin1; r(1:nStim,:)];
    collatedZRespLin2 = [collatedZRespLin2; r(nStim+1:nStim*2,:)];
    
    collatedStimIds = horzcat(collatedStimIds,currStimIds);
    
    save([stimPath '/' folderName '_tempColFit.mat'],'collatedRespLin1','collatedRespLin2','collatedStimIds','collatedZRespLin1','collatedZRespLin2');
    save([secondaryPath '/stim/' folderName '_tempColFit.mat'],'collatedRespLin1','collatedRespLin2','collatedStimIds','collatedZRespLin1','collatedZRespLin2');
    
    message = 'Saved refactored resp.';
    logger(mfilename,folderName,['Responses saved and collated for genNum ' num2str(genNum) '.'],conn);
end

