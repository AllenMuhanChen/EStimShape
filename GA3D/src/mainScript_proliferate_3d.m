function mainScript_proliferate_3d
    getPaths;

    load([rootPath '/currState.mat']);
    conn = getDBconn(folderName);

    disp(getMstickSpec_3d(gaInfo,conn)); %#ok<NODEF>
    
    checkResponses(gaInfo,conn);
    
    disp(refactorResonses(gaInfo,conn));
    disp(selectParents(gaInfo,conn));

    gaInfo = resetGaInfo(gaInfo);
    
    gaInfo.genNum = gaInfo.genNum + 1;
    fullFolderPath = [folderName '_g-' num2str(gaInfo.genNum)];
    save([rootPath '/currentGAInfo.mat'],'gaInfo','-append');

    updateDescriptiveInfo(gaInfo,conn);
    
    logger(mfilename,folderName,['Experiment started. Id = ' fullFolderPath '.'],conn);

    exec(conn,'TRUNCATE TABLE TaskToDo');
    logger(mfilename,folderName,'TaskToDo table truncated.',conn);

    disp(runProliferation_3d(folderName,gaInfo,randStim,conn));

    close(conn); clearvars conn ans;
    save([rootPath '/currState.mat']);
    
    system('java -jar /home/r2_allen/git/EStimShape/xper-train/dist/sach/ga_sachrandgen.jar');
    mkdir(['/home/r2_allen/git/EStimShape/xper-train/xper-sach/images/' fullFolderPath]);
    try
        copyfile(['images/' fullFolderPath '/*'],['/home/r2_allen/git/EStimShape/xper-train/xper-sach/images/' fullFolderPath '/.']);
    catch
        disp("Could not copy images folder")
    end 
    if exist([respPath '/' folderName '_g-' num2str(gaInfo.genNum-1) '/acqData.mat'],'file')
        cd(analysisPath);
        mainScript_AnalyzeGen_3d(gaInfo.currentExptPrefix,gaInfo.gaRun,gaInfo.genNum-1,gaInfo.genNum-1,2,gaInfo.stimAndTrial.nStim,20,false,true);
    end
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
            try
                save([secondaryPath '/resp/' fullFolderPath '/resp.mat'], 'resp','blankResp','unitStat');
            catch
            end 
        end
    end
end

function updateDescriptiveInfo(gaInfo,conn)
    insertIntoSqlTable({getPosixTimeNow,str2double(gaInfo.currentExptPrefix),gaInfo.gaRun,gaInfo.genNum,1,0,0,0},...
                       {'tstamp','currentExptPrefix','gaRun','genNum','isRealExpt','firstTrial','lastTrial','containsAnimation'},...
                       'DescriptiveInfo',conn);
end

function gaInfo = resetGaInfo(gaInfo)
    gaInfo.stimAndTrial.nStim = 40;
    gaInfo.stimAndTrial.nReps = 5;
    gaInfo.stimAndTrial.nStimPerTrial = 4;
    gaInfo.stimAndTrial.nStimPerChunk = 500;
end