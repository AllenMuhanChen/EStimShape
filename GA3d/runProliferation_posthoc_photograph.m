 function [message,nStim] = runProliferation_posthoc_photograph(folderName,gaInfo,postHocId,conn)
    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started for photo posthoc.',conn);
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

    sizePosGenNum = input('Enter generation number of the sizePos posthoc: ');

    nVariantConds = 10;
    
    disp('Select best center position: ');
    fprintf('\n\t\t2\n');
    fprintf('\n\t3\t0\t1\n');
    fprintf('\n\t\t4\n');
    positionCenterId = validatedInput('Enter position id: ',0:4);

    disp('Select best size: ');
    fprintf('\t1. x 1\n');
    fprintf('\t2. x 2\n');
    sizeId = validatedInput('Select best size: ',1:2);
    
    stim2get = 1;
    if sizeId > 1; stim2get = stim2get + 5; end
    idsToFetch = (0:nVariantConds:39) + stim2get;
    
    for linNum=1:2
        pIP = repmat(parentIdsPosthoc(linNum,:),nVariantConds,1);
        pIP = pIP(:);

        for jj=1:nPosthoc
            photoDescId = [folderName '_g-' num2str(sizePosGenNum) '_l-' num2str(linNum) '_s-' num2str(idsToFetch(jj))];
            parentId = pIP{jj};
            parentStim = getStimParams(parentId);
            for kk=1:nVariantConds
                stimNum = nVariantConds*(jj-1) + kk;
                
                % SHAPE AND MASK
                stim = parentStim;

                photoId = kk;

                imFile = [plotPath '/temp_photo/' photoDescId '_photo-' num2str(photoId) '.png'];

                % SAVE TEXTURE, POSITION AND SIZE TO SHAPE
                xDiff = 0; yDiff = 0;
                switch(positionCenterId)
                    case 1;  xDiff = xDiff + 5;
                    case 2;  yDiff = yDiff + 5;
                    case 3;  xDiff = xDiff - 5;
                    case 4;  yDiff = yDiff - 5;
                end
                stim.shape.x = stim.shape.x + xDiff;
                stim.shape.y = stim.shape.y + yDiff;
                stim.shape.s = stim.shape.s * sizeId;

                stim.shape.texture = 'PHOTO';

                % OCCLUDER
                % already initiated

                % ID
                stim.id.linNum = linNum;
                stim.id.genNum = genNum;
                stim.id.stimNum = stimNum;
                stim.id.tstamp = getPosixTimeNow;
                stim.id.type = 'ga3d';
                stim.id.descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(stimNum)];
                stim.id.respMatrix = [];
                stim.id.parentId = parentId;
                stim.id.parentStim = parentStim;
                stim.id.tagForRand = false;
                stim.id.tagForMorph = false;
                stim.id.saveVertSpec = false;
                stim.id.posthocId = postHocId;

                mstickspec_all{linNum,stimNum} = stim.shape.mstickspec;

                % SAVE TO MAT FILE
                currStimIds{linNum,stimNum} = stim.id.descId;
                stimuli{linNum,stimNum} = stim;

                % COPY RDS IMAGES TO CORRECT FOLDER
                destFolder = [stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_photo'];
                if ~exist(destFolder,'dir'); mkdir(destFolder); end
                copyfile(imFile,[destFolder '/' stim.id.descId '.png']);
            end
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nVariantConds) ' photo posthoc stimuli created.'],conn);
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
    logger(mfilename,folderName,['Proliferation for photograph variants posthoc finished. ' message],conn);

%     fprintf(2,['\n\n=====================================\n' upper('Enter password to copy images to rig.') '\n=====================================\n\n']);
    system(['scp -prq ' stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_photo/. m1_ram@172.30.6.25:/media/m1_ram/SSD/xper/3dga/dist/sach/images/' fullFolderPath '_PHOTO/']);
end
