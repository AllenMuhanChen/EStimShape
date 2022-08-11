function [message,nStim] = runProliferation_posthoc_zuckerRadChange(folderName,gaInfo,postHocId,conn)
    mainScript_zucker_3d(gaInfo);

    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started for zucker and radius posthoc.',conn);
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
    
    nVariantConds = 10;
    
    for linNum=1:2
        pIP = repmat(parentIdsPosthoc(linNum,:),nVariantConds,1);
        pIP = pIP(:);

        jj = 1;
        while jj <= nPosthoc*nVariantConds
            parentId = pIP{jj};
            parentStim = getStimParams(parentId);

            imagePath = '';
            
            % SHAPE AND MASK
            stim = parentStim;
            stim.id.tagForMorph = false;
            switch mod(jj,nVariantConds)
                case 1;  stim.shape.texture = 'ZUCKER2D'; imagePath = [plotPath '/temp_drape/' parentId '_2D.png'];
                case 2;  stim.shape.texture = 'ZUCKER3D'; imagePath = [plotPath '/temp_drape/' parentId '_3D.png'];
                case 3;  stim.shape.texture = 'TWOD'; stim.shape.color = stim.shape.color*0.6;
                case 4;  stim.shape.texture = 'SHADE'; 
                case 5;  stim.shape.texture = 'SHADE'; stim.id.tagForMorph = true; stim.id.radiusProfile = 1;
                case 6;  stim.shape.texture = 'SHADE'; stim.id.tagForMorph = true; stim.id.radiusProfile = 2;
                case 7;  stim.shape.texture = 'SHADE'; stim.id.tagForMorph = true; stim.id.radiusProfile = 3;
                case 8;  stim.shape.texture = 'SHADE'; stim.id.tagForMorph = true; stim.id.radiusProfile = 4;
                case 9;  stim.shape.texture = 'SHADE'; stim.id.tagForMorph = true; stim.id.radiusProfile = 5;
                case 0;  stim.shape.texture = 'SHADE'; stim.id.tagForMorph = true; stim.id.radiusProfile = 6;
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
            stim.id.saveVertSpec = false;
            stim.id.posthocId = postHocId;

            mstickspec_all{linNum,jj} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,jj} = stim.id.descId;
            stimuli{linNum,jj} = stim;
            
            % COPY RDS IMAGES TO CORRECT FOLDER
            if ~isempty(imagePath)
                destFolder = [stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_drape'];
                if ~exist(destFolder,'dir'); mkdir(destFolder); end
                copyfile(imagePath,[destFolder '/' stim.id.descId '.png']);
            end
            
            jj = jj + 1;
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nVariantConds) ' zucker and radius profile posthoc stimuli created.'],conn);
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
    logger(mfilename,folderName,['Proliferation for zucker and radius profile variants posthoc finished. ' message],conn);
    
%     fprintf(2,['\n\n=====================================\n' upper('Enter password to copy images to rig.') '\n=====================================\n\n']);
    system(['scp -prq ' stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_drape/. m1_ram@172.30.6.25:/media/m1_ram/SSD/xper/3dga/dist/sach/images/' fullFolderPath '_drape/']);
end

function mainScript_zucker_3d(gaInfo)   
    genNum = input('Enter generation number of the sizePos posthoc: ');
    fullFolderPath = [gaInfo.currentExptPrefix '_r-' num2str(gaInfo.gaRun) '_g-' num2str(genNum)];
        
    disp(generateAndSaveZucker(fullFolderPath));
end

function message = generateAndSaveZucker(fullFolderPath)
    getPaths;
    
    nVariantConds = 10;
    nPostHocStim = 4;
    
    % get the size to run
    disp('Select best size: ');
    fprintf('\t1. x 1\n');
    fprintf('\t2. x 2\n');
    sizeId = validatedInput('Select best size: ',1:2);
    
    % change 1-2 to 1,6 <= these are the ids of the size conditions in
    % the sizepos posthoc
    if sizeId > 1; sizeId = sizeId + 4; end
    
    % ids based on sizePos posthoc
    % 1-10 are the same stim
    idsToFetch = (0:nVariantConds:39) + sizeId;
    
    load([stimPath '/' fullFolderPath '/stimParams.mat']);
    
    % save rds params for each stimulus
    for l=1:2
        for s=1:nPostHocStim
            stim = stimuli{l,idsToFetch(s)};
            parentId = stim.id.parentId;
            
            im_drape = imread([plotPath '/temp_drape/' fullFolderPath '_l-' num2str(l) '_s-' num2str(idsToFetch(s)) '.png']);
            im_bw = imread([plotPath '/temp_drape/' fullFolderPath '_l-' num2str(l) '_s-' num2str(idsToFetch(s)) '_bw.png']);

            im_2d = getZuckerStim(im_drape);
            im_2d_cutup = cutupshape(im_2d,im_bw);

            % grating 
            im_grating = getBestGrating(im_drape);
            im_3d_grating = getZuckerStim(im_grating,im_drape);
            im_3d_grating_cutup = cutupshape(im_3d_grating,im_bw);

            im_2d_cutup = padarray(im_2d_cutup,[32 768/2]);
            im_3d_grating_cutup = padarray(im_3d_grating_cutup,[32 768/2]);
            
            imwrite(im_2d_cutup,[plotPath '/temp_drape/' parentId '_2D.png']);
            imwrite(im_3d_grating_cutup,[plotPath '/temp_drape/' parentId '_3D.png']);
            
        end
    end
    message = ['Zucker stimuli saved for posthoc stimuli from ' fullFolderPath '.'];
end


function im_cutup = cutupshape(im,im_ref)
    im_bool = smoothRef(mean(im_ref,3));
    im_cutup = im.*repmat(im_bool,1,1,3);
end

function im_bool = smoothRef(im_ref)
    kernel = ones(81,81)/100;
    im_ref = padarray(im_ref,[40 40],0);
    im_bool = conv2(im_ref,kernel,'valid');
    im_bool = im_bool/max(im_bool(:));
end

function im_grating = getBestGrating(im_drape)
    getPaths;
    co = nan(1,28);
    for ii=1:28
        im_g = imread([plotPath '/zucker/gratings/grating_' num2str(ii) '_drape.png']);
        co(ii) = corr2(mean(im_g,3),mean(im_drape,3));
    end
    [~,idx] = min(co);
    im_grating = imread([plotPath '/zucker/gratings/grating_' num2str(idx) '_drape.png']);
end

function im_2d = getZuckerStim(im,multIm)
    getPaths;
    if ~exist('multIm','var'); multIm = im; end

    % im and im_2d are nxnx3
    im2 = nan(size(im));
    im = mean(im,3);
    im = im+1;

    col = imread([plotPath '/zucker/freqcmap.png']);
    col = squeeze(col(1,:,:));
    x=linspace(1,256,2200);
    r = interp1(x,double(col(:,1)),1:256);
    g = interp1(x,double(col(:,2)),1:256);
    b = interp1(x,double(col(:,3)),1:256);
    col = [r; g; b]'/255;

    for ii=1:size(im,1)
        for jj=1:size(im,2)
            im2(ii,jj,:) = col(im(ii,jj),:);
        end
    end

    im3 = double(multIm)/255;
    im_2d = im2.*im3;
end
