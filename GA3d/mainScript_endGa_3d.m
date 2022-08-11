function mainScript_endGa_3d
    getPaths;

    load([rootPath '/currState.mat']);
    
    conn = getDBconn(folderName);
    
    if validatedInput('Include last gen? (1/0): ',[0 1])
        disp(getMstickSpec_3d(gaInfo,conn)); %#ok<NODEF>
        
        checkResponses(gaInfo,conn);
        disp(refactorResonses(gaInfo,conn));
        
        exec(conn,'TRUNCATE TABLE TaskToDo');
        logger(mfilename,folderName,'TaskToDo table truncated.',conn);
    else
        gaInfo.genNum = gaInfo.genNum-1; %#ok<NODEF>
    end
    
    close(conn); clearvars conn ans;
    save([rootPath '/currState.mat']);
    
    if validatedInput('Run analysis? (1/0): ',[0 1])
        cd(analysisPath);
        doRasters = validatedInput('Run rasters? (1/0): ',[0 1]);
        mainScript_AnalyzeGen_3d(gaInfo.currentExptPrefix,gaInfo.gaRun,1,gaInfo.genNum,2,gaInfo.stimAndTrial.nStim,20,doRasters,true);
    end
end

function checkResponses(gaInfo,conn)
    getPaths;
    folderName = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun)];
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    
    if ~exist([respPath '/' fullFolderPath '/resp.mat'],'file')
        if validatedInput('Parse real resp? (0/1): ',[0 1])
            getResp_real(gaInfo,conn);
        elseif validatedInput('Continue to fake resp? (0/1): ',[0 1])
            nSimulatedCells = 1;
            [resp,blankResp,unitStat] = getResp_fake(gaInfo.stimAndTrial.nStim*2,nSimulatedCells,gaInfo.stimAndTrial.nReps,gaInfo.stimAndTrial.nStimPerChunk,0); %#ok<ASGLU>
            save([respPath '/' fullFolderPath '/resp.mat'], 'resp','blankResp','unitStat');
            save([secondaryPath '/resp/' fullFolderPath '/resp.mat'], 'resp','blankResp','unitStat');
        end
    end
end