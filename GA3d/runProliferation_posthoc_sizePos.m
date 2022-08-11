function [message,nStim] = runProliferation_posthoc_sizePos(folderName,gaInfo,postHocId,conn)
    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started for 3D variants posthoc.',conn);
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
    
    % original      #1
    % pos           #4
    % size          #3
    
    nVariantConds = 10;
    
    for linNum=1:2
        pIP = repmat(parentIdsPosthoc(linNum,:),nVariantConds,1); 
        pIP = pIP(:);
        
        jj = 1;
        while jj <= nPosthoc*nVariantConds
            parentId = pIP{jj};
            parentStim = getStimParams(parentId);

            % SHAPE AND MASK
            stim = parentStim;
            switch mod(jj,nVariantConds)
                case 1;                                  stim.id.saveVertSpec = true;
                case 2;  stim.shape.x = stim.shape.x + 5; 
                case 3;  stim.shape.x = stim.shape.x - 5;
                case 4;  stim.shape.y = stim.shape.y + 5;
                case 5;  stim.shape.y = stim.shape.y - 5;
                case 6;                                  stim.id.saveVertSpec = true;
                case 7;  stim.shape.x = stim.shape.x + 5; 
                case 8;  stim.shape.x = stim.shape.x - 5;
                case 9;  stim.shape.y = stim.shape.y + 5;
                case 0;  stim.shape.y = stim.shape.y - 5;
            end
            
            if mod(jj,nVariantConds) > 5 || mod(jj,nVariantConds) == 0
                stim.shape.s = stim.shape.s * 2;
            end
            
            % OCCLUDER
            % already initiated
            
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
            stim.id.posthocId = postHocId;

            mstickspec_all{linNum,jj} = stim.shape.mstickspec;
            
            % SAVE TO MAT FILE
            currStimIds{linNum,jj} = stim.id.descId;
            stimuli{linNum,jj} = stim;
            
            jj = jj + 1;
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nVariantConds) ' position variant posthoc stimuli created.'],conn);
    end
    
    nStim = size(stimuli,2);
    
    saveStimuliToDb(stimuli,mstickspec_all,colnames,tableName,conn);
    
    occluder.leftBottom = [-1 -1];
    occluder.rightTop = [-1 -1];
    occluder.color = [0 0 0];
    saveOccluderToDb(occluder,fullFolderPath,conn)
    
    save([stimPath '/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([stimPath '/' fullFolderPath '/stimIds.mat'],'currStimIds','-append');

    save([secondaryPath '/stim/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'],'currStimIds','-append');

    fprintf('\n');
    message = ['Generated ' fullFolderPath '.'];
    logger(mfilename,folderName,['Proliferation for 3d variants posthoc finished. ' message],conn);
end