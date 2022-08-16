function mainScript_posthoc_3d
    getPaths;

    load([rootPath '/currState.mat']); getPaths;
    conn = getDBconn(folderName);

    disp('Select posthoc to run: ');
    fprintf('\t1. Size, position variants\n');
    fprintf('\t2. Size grid\n');
    fprintf('\t3. Size, lighting variants\n');
    fprintf('\t4. RDS\n');
    fprintf('\t5. Fingerprints\n');
    fprintf('\t6. Photographs (textures, glass)\n');
    fprintf('\t7. 2D variants (scramble, low pass)\n');
    fprintf('\t8. Occluded\n');
    fprintf('\t9. Contrast\n');
    fprintf('\t10. Zucker/Radius change\n');
    fprintf('\t11. Single Gabor\n');
    fprintf('\t12. Double Gabor\n');
    
    posthocId = validatedInput('Enter posthoc id: ',[1 4 6 9 10 11]);
    
    disp(getMstickSpec_3d(gaInfo,conn)); %#ok<NODEF>
    
    checkResponses(gaInfo,conn); 
    
    disp(refactorResonses(gaInfo,conn));

    if exist([respPath '/' folderName '_g-' num2str(gaInfo.genNum) '/acqData.mat'],'file')
        cd(analysisPath);
        mainScript_AnalyzeGen_3d(gaInfo.currentExptPrefix,gaInfo.gaRun,gaInfo.genNum,gaInfo.genNum,2,gaInfo.stimAndTrial.nStim,20,false,true);
    end
    
    disp(selectParents_posthoc(gaInfo,false,conn));
    
    gaInfo.genNum = gaInfo.genNum + 1;
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    save([rootPath '/currentGAInfo.mat'],'gaInfo','-append');

    gaInfo.posthocId = posthocId;
    updateDescriptiveInfo(gaInfo,conn);
    
    logger(mfilename,folderName,['Experiment started. Id = ' fullFolderPath '.'],conn);

    exec(conn,'TRUNCATE TABLE TaskToDo');
    logger(mfilename,folderName,'TaskToDo table truncated.',conn);

    modifyTrialStructure(gaInfo,folderName,conn);
    gaInfo.stimAndTrial.nStimPerTrial = 4;
    gaInfo.doStereo = false;
    
    switch(posthocId)
        case 1;  [message,nStim] = runProliferation_posthoc_sizePos(folderName,gaInfo,posthocId,conn);
        case 2;  [message,nStim] = runProliferation_posthoc_sizeGrid(folderName,gaInfo,posthocId,conn);
        case 3;  [message,nStim] = runProliferation_posthoc_sizeLight(folderName,gaInfo,posthocId,conn);
        case 4;  [message,nStim] = runProliferation_posthoc_RDS(folderName,gaInfo,posthocId,conn); gaInfo.stimAndTrial.nStimPerTrial = 2; gaInfo.doStereo = true;
        case 5;  [message,nStim] = runProliferation_posthoc_fingerprint(folderName,gaInfo,posthocId,conn);
        case 6;  [message,nStim] = runProliferation_posthoc_photograph(folderName,gaInfo,posthocId,conn); % gaInfo.stimAndTrial.nStimPerTrial = 2;
        case 7;  [message,nStim] = runProliferation_posthoc_2dvariants(folderName,gaInfo,posthocId,conn);
        case 8;  [message,nStim] = runProliferation_posthoc_occluded(folderName,gaInfo,posthocId,conn);
        case 9;  [message,nStim] = runProliferation_posthoc_contrast(folderName,gaInfo,posthocId,conn);
        case 10; [message,nStim] = runProliferation_posthoc_zuckerRadChange(folderName,gaInfo,posthocId,conn);
        case 11; [message,nStim] = runProliferation_posthoc_singleGabor(folderName,gaInfo,posthocId,randStim,conn); gaInfo.stimAndTrial.nStimPerTrial = 8;
    end
    disp(message);
    
    gaInfo.stimAndTrial.nStim = nStim;
    updateInternalStateForPostHoc(gaInfo,conn);
    modifyTrialStructure(gaInfo,folderName,conn); % ??
    
    close(conn); clearvars conn ans;
    save([rootPath '/currState.mat']);
    
    system('java -jar /Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/dist/sach/ga_sachrandgen.jar');
    mkdir(['/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images/' fullFolderPath]);
    copyfile(['images/' fullFolderPath '/*'],['/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images/' fullFolderPath '/.']);
    
    if posthocId == 1 
        system(['ssh ram@172.30.9.11 "./projectMakePhoto/masterSubmitScript.sh ' fullFolderPath '"']);
    end
end

function updateInternalStateForPostHoc(gaInfo,conn)
    nStim = gaInfo.stimAndTrial.nStim * 2 * gaInfo.stimAndTrial.nReps;
    nBlank = ceil((gaInfo.stimAndTrial.nStim * 2)/gaInfo.stimAndTrial.nStimPerChunk) * gaInfo.stimAndTrial.nReps;
    nFinger = 0;
    nTask = ceil((nStim + nBlank + nFinger)/gaInfo.stimAndTrial.nStimPerTrial);
    updateInternalState(nTask,gaInfo,conn);
end

function checkResponses(gaInfo,conn)
    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    
    if ~exist([respPath '/' fullFolderPath '/resp.mat'],'file')
        if validatedInput('Parse real resp? (0/1): ',[0 1])
            getResp_real(gaInfo,conn);
        else % if validatedInput('Continue to fake resp? (0/1): ',[0 1])
            nSimulatedCells = 1;
            [resp,blankResp,unitStat] = getResp_fake(gaInfo.stimAndTrial.nStim*2,nSimulatedCells,gaInfo.stimAndTrial.nReps,gaInfo.stimAndTrial.nStimPerChunk,0); %#ok<ASGLU>
            save([respPath '/' fullFolderPath '/resp.mat'], 'resp','blankResp','unitStat');
            save([secondaryPath '/resp/' fullFolderPath '/resp.mat'], 'resp','blankResp','unitStat');
        end
    end
end

function updateDescriptiveInfo(gaInfo,conn)
    if gaInfo.posthocId == 4
        insertIntoSqlTable({getPosixTimeNow,str2double(gaInfo.currentExptPrefix),gaInfo.gaRun,gaInfo.genNum,1,0,0,1},...
                       {'tstamp','currentExptPrefix','gaRun','genNum','isRealExpt','firstTrial','lastTrial','containsAnimation'},...
                       'DescriptiveInfo',conn);
    else
        insertIntoSqlTable({getPosixTimeNow,str2double(gaInfo.currentExptPrefix),gaInfo.gaRun,gaInfo.genNum,1,0,0,0},...
                       {'tstamp','currentExptPrefix','gaRun','genNum','isRealExpt','firstTrial','lastTrial','containsAnimation'},...
                       'DescriptiveInfo',conn);
    end
end