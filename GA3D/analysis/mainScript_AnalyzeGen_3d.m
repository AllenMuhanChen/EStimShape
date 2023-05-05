% clear; clc; close all hidden;
% 
% prefix = '170517';
% runNum = 91;
% nGen = 6;
% nLin = 2;
% nStim = 40;
% nControl = 20;

% mainScript_AnalyzeGen_3d('170517',91,1,6,2,40,20,false,false)
function mainScript_AnalyzeGen_3d(prefix,runNum,startGen,endGen,nLin,nStim,nControl,doSaveRasters,returnToSource,monkeyId)
    getPaths;
    
    nPosthocStim = 4; % nVariantConds = 8;

    gens = startGen:endGen;
    nGen = endGen - startGen + 1;
    folderName = [prefix '_r-' num2str(runNum)];
    mkdir([plotPath '/' folderName]);
    blank_mean = nan(nGen,1); blank_sem = nan(nGen,1);
    best_mean = nan(nGen,nLin); best_sem = nan(nGen,nLin);
    posthocGens = zeros(nGen,1);
    
    for genNum=1:nGen
        genId = gens(genNum);
        fullFolderName = [prefix '_r-' num2str(runNum) '_g-' num2str(genId)];

        mkdir([plotPath '/' folderName '/' fullFolderName]);
        mkdir([plotPath '/' folderName '/' fullFolderName '/rasters']);
        aData = load([respPath '/' fullFolderName '/acqData.mat']);
        rData(genNum) = load([respPath '/' fullFolderName '/resp.mat']); %#ok<AGROW>
        sData(genNum) = load([stimPath '/' fullFolderName '/stimParams.mat']); %#ok<AGROW>

        genResp = mean(squeeze(rData(genNum).resp),2);
        linResp(:,1) = genResp(1:nStim);
        linResp(:,2) = genResp(nStim+1:2*nStim);
        cols = (genResp - min(genResp)) / (max(genResp) - min(genResp));
        blank_mean(genNum) = mean(squeeze(rData(genNum).blankResp));
        blank_sem(genNum) = std(squeeze(rData(genNum).blankResp))/sqrt(length(squeeze(rData(genNum).blankResp)));

        for linNum=1:nLin
            [~,idx] = max(linResp(:,linNum));
            idx = nStim*(linNum-1) + idx;
            best_mean(genNum,linNum) = mean(squeeze(rData(genNum).resp(idx,:,:)));
            best_sem(genNum,linNum) = std(squeeze(rData(genNum).resp(idx,:,:)))/sqrt(size(rData(genNum).resp,3));

            postHocId = sData(genNum).stimuli{1}.id.posthocId;
            thumb = saveRastersPerGen(nStim,nLin,linNum,genNum,sData,rData,aData,postHocId,folderName,fullFolderName,cols,doSaveRasters);

            if isfield(sData(genNum).stimuli{1}.id,'posthocId')
                if postHocId > 0
                    % saveAllStimPerGen(linNum,genNum,sData,thumb,folderName,fullFolderName);
                    % savePosthocComparisons(linNum,genNum,sData,thumb,postHocId,nPosthocStim,folderName,fullFolderName);
                    posthocGens(genNum) = 1;
                else
                    saveTopTenPerGen(linNum,genNum,linResp,sData,thumb,folderName,fullFolderName);
                    saveControlsPerGen(genNum,genId,nStim,nControl,thumb,linNum,sData,folderName,fullFolderName)
                    savePsthOverlayPerGen(nStim,linNum,aData,cols,folderName,fullFolderName)
                end
            end
        end
        saveIsiPerGen(aData.respStruct,folderName,fullFolderName);
    end

    endGen = endGen - sum(posthocGens);
    if startGen ~= endGen && endGen > 0 && startGen == 1 % endGA
        saveTopTenOverall(folderName,sData,startGen,endGen,nLin,nStim);
        saveBlankAndBest(endGen,best_mean(1:endGen,:),best_sem(1:endGen,:),blank_mean(1:endGen),blank_sem(1:endGen),folderName);
        saveControlComparisons(folderName,sData,endGen,nLin,nStim,nControl);
        saveTopHundred(folderName,sData,startGen,endGen,nLin,nStim);
        saveRateHistOverall(folderName,startGen,endGen,nLin,nStim);
%         todo_saveTopControls(folderName,sData,nGen,nLin,nStim,nControl)
    end

    close all;
    
    if returnToSource
        cd(srcPath);
    end
end