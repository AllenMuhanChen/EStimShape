function message = runProliferation_3d(folderName,gaInfo,randStim,conn)
    nStim = gaInfo.stimAndTrial.nStim;
    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started.',conn);
    disp(message);

    if exist([stimPath '/' fullFolderPath '/stimIds.mat'],'file') == 0
        message = 'Parent IDs not found'; return;
    else
        load([stimPath '/' fullFolderPath '/stimIds.mat']);
        if isempty(parentIdsMorph) %#ok<USENS>
            message = 'Parent IDs not found'; return;
        end
    end

    currStimIds = cell(2,nStim);
    stimuli = cell(2,nStim);
    mstickspec_all = cell(2,nStim);

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
    nMorph = size(parentIdsMorph,2);
    nControl = size(parentIdsControl,2);
    nNew = nStim - nMorph - nControl*4;

    for linNum=1:2
        ii = 1;
        while ii <= nNew
            stim = templateStimulus;

            % SHAPES
            r = (randStim.siz/2) * rand; % 0 to s/2
            th = 2*pi*rand;
            [xx,yy] = pol2cart(th,r);
            stim.shape.x = randStim.xPos + xx;
            stim.shape.y = randStim.yPos + yy;
            stim.shape.s = randStim.siz  * (0.6+(trandn*0.4));

            % stim.shape.x = randStim.xPos + randStim.xPos/20 * randn;
            % stim.shape.y = randStim.yPos + randStim.yPos/20 * randn;
            % stim.shape.s = randStim.siz + randStim.siz/10 * randn;
            stim.shape.color = getShapeColor(randStim.fColor);
            stim.shape.texture = getRandTexture();

            % MASKS
            % already initiated

            % OCCLUDER
            % already initiated

            % ID
            stim.id.linNum = linNum;
            stim.id.genNum = genNum;
            stim.id.stimNum = ii;
            stim.id.tstamp = getPosixTimeNow;
            stim.id.type = 'ga3d';
            stim.id.descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(ii)];
            stim.id.respMatrix = [];
            stim.id.parentId = '';
            stim.id.parentStim = [];
            stim.id.isOccluded = false;
            stim.id.tagForRand = true;
            stim.id.tagForMorph = false;

            mstickspec_all{linNum,ii} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,ii} = stim.id.descId;
            stimuli{linNum,ii} = stim;

            ii = ii + 1;
            pause(0.005)
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nNew) ' random stimuli created.'],conn);

        jj = nNew + 1;
        while jj <= nNew + nMorph
            parentId = parentIdsMorph{linNum,jj-nNew};
            parentStim = getStimParams(parentId);

            % SHAPE AND MASK
            stim = applyMorphs(parentStim);

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

            mstickspec_all{linNum,jj} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,jj} = stim.id.descId;
            stimuli{linNum,jj} = stim;

            jj = jj + 1;
            pause(0.005)
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nMorph) ' morphed stimuli created.'],conn);

        kk = nNew + nMorph + 1;
        pIC = repmat(parentIdsControl(linNum,:),4,1); pIC = pIC(:);
        while kk <= nNew + nMorph + nControl*4
            parentId = pIC{kk-nNew-nMorph};
            parentStim = getStimParams(parentId);

            % SHAPE AND MASK
            stim = parentStim;
            switch mod(kk,4)
                case 0; stim.shape.texture = 'SHADE';
                case 1; stim.shape.texture = 'SPECULAR';
                case 2; stim.shape.texture = 'TWOD'; stim.shape.color = stim.shape.color*0.6;
                case 3; stim.shape.texture = 'TWOD'; stim.shape.color = stim.shape.color*0.2;
            end

            % OCCLUDER
            % already initiated

            % ID
            stim.id.linNum = linNum;
            stim.id.genNum = genNum;
            stim.id.stimNum = kk;
            stim.id.tstamp = getPosixTimeNow;
            stim.id.type = 'ga3d';
            stim.id.descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(kk)];
            stim.id.respMatrix = [];
            stim.id.parentId = parentId;
            stim.id.parentStim = parentStim;
            stim.id.tagForRand = false;
            stim.id.tagForMorph = false;
            stim.id.isControl = true;

            mstickspec_all{linNum,kk} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,kk} = stim.id.descId;
            stimuli{linNum,kk} = stim;

            kk = kk + 1;
            pause(0.005)
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(nControl) ' control stimuli created.'],conn);
    end

    saveStimuliToDb(stimuli,mstickspec_all,colnames,tableName,conn);

    occluder.leftBottom = [-1 -1];
    occluder.rightTop = [-1 -1];
    occluder.color = [0 0 0];
    saveOccluderToDb(occluder,fullFolderPath,conn)

    save([stimPath '/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([stimPath '/' fullFolderPath '/stimIds.mat'],'parentIdsMorph','currStimIds','-append');

    save([secondaryPath '/stim/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'],'parentIdsMorph','currStimIds','-append');

    fprintf('\n');
    message = ['Generated ' fullFolderPath '.'];
    logger(mfilename,folderName,['Proliferation finished. ' message],conn);
end

function texture = getRandTexture()
    probSelection = [0 0 1 0 0 0 0 0 1];
    probSelection = probSelection/sum(probSelection);
    types = {'TWOD','DOTS','SHADE','STRIPES','GRAT','HEX','QUAD','RAND3D','SPECULAR'};
    textureIdx = datasample(1:size(types,2),1,'weights',probSelection);
    texture = types{textureIdx};
end