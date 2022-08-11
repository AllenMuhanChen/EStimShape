function [message,nStim] = runProliferation_posthoc_RDS(folderName,gaInfo,postHocId,conn)
    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started for RDS posthoc.',conn);
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

    % 3D: behind, behind, fixation, front, front => 5
    % 2D: behind, behind, fixation, front, front => 5

    disp('Select best center position: ');
    fprintf('\n\t\t2\n');
    fprintf('\n\t3\t0\t1\n');
    fprintf('\n\t\t4\n');
    positionCenterId = validatedInput('Enter position id: ',0:4);

    disp('Select best size: ');
    fprintf('\t1. x 1\n');
    fprintf('\t2. x 2\n');
    sizeId = validatedInput('Select best size: ',1:2);

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
                case 1;  depthId = 1; doSilh = 0; stim.shape.texture = 'RDS';
                case 2;  depthId = 2; doSilh = 0; stim.shape.texture = 'RDS';
                case 3;  depthId = 3; doSilh = 0; stim.shape.texture = 'RDS';
                case 4;  depthId = 4; doSilh = 0; stim.shape.texture = 'RDS';
                case 5;  depthId = 0; doSilh = 0; stim.shape.texture = 'RDK';
                case 6;  depthId = 1; doSilh = 1; stim.shape.texture = 'RDS';
                case 7;  depthId = 2; doSilh = 1; stim.shape.texture = 'RDS';
                case 8;  depthId = 3; doSilh = 1; stim.shape.texture = 'RDS';
                case 9;  depthId = 4; doSilh = 1; stim.shape.texture = 'RDS';
                case 0;  depthId = 0; doSilh = 1; stim.shape.texture = 'RDK';
            end

            xDiff = 0; yDiff = 0;
            switch(positionCenterId)
                case 1;  xDiff = xDiff + 5;
                case 2;  yDiff = yDiff + 5;
                case 3;  xDiff = xDiff - 5;
                case 4;  yDiff = yDiff - 5;
            end

            % SAVE POSITION AND SIZE TO SHAPE
            stim.shape.x = stim.shape.x + xDiff;
            stim.shape.y = stim.shape.y + yDiff;
            stim.shape.s = stim.shape.s * sizeId;

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
            stim.id.saveVertSpec = false;
            stim.id.posthocId = postHocId;

            mstickspec_all{linNum,jj} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,jj} = stim.id.descId;
            stimuli{linNum,jj} = stim;

            % COPY RDS IMAGES TO CORRECT FOLDER
            destFolder = [stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_RDS'];
            if ~exist(destFolder,'dir'); mkdir(destFolder); end
            if depthId > 0 % RDS
                srcImage = [plotPath '/temp_RDS/' parentId '_depth-' num2str(depthId) '_silh-' num2str(doSilh) '_L.png'];
                desImage = [destFolder '/' stim.id.descId '_L.png'];
                copyfile(srcImage,desImage);
                
                srcImage = [plotPath '/temp_RDS/' parentId '_depth-' num2str(depthId) '_silh-' num2str(doSilh) '_R.png'];
                desImage = [destFolder '/' stim.id.descId '_R.png'];
                copyfile(srcImage,desImage);
            else % RDK
                numFrames = length(dir([plotPath '/temp_RDK/img/' parentId '_silh-' num2str(doSilh) '_f-*.png']));
                for ii=1:numFrames % hardcoded for now
                    srcImage = [plotPath '/temp_RDK/img/' parentId '_silh-' num2str(doSilh) '_f-' num2str(ii) '.png'];
                    desImage = [destFolder '/' stim.id.descId '_f-' num2str(ii) '.png'];
                    copyfile(srcImage,desImage);
                end
            end

            jj = jj + 1;
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nVariantConds) ' RDS posthoc stimuli created.'],conn);
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
    logger(mfilename,folderName,['Proliferation for RDS variants posthoc finished. ' message],conn);

%     fprintf(2,['\n\n=====================================\n' upper('Enter password to copy images to rig.') '\n=====================================\n\n']);
    system(['scp -prq ' stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_RDS/. m1_ram@172.30.6.25:/media/m1_ram/SSD/xper/3dga/dist/sach/images/' fullFolderPath '_RDS/']);
end
