function message = runRandGen_3d(folderName,gaInfo,randStim,conn)
    nStim = gaInfo.stimAndTrial.nStim;
    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    cleanDirectories;
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,['RandGen started. ' message],conn);
    disp(message);

    if exist([stimPath '/' fullFolderPath '/stimIds.mat'],'file')
        message = 'Run exists.';
        logger(mfilename,folderName,'This experiment id (gaRun) exists. Fix this.',conn);
        return;
    end
    
    currStimIds = cell(2,nStim);
    stimuli = cell(2,nStim);
    mstickspec_all = cell(2,nStim);
    parentIds = {};  %#ok<NASGU>
    genNum = 1;

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
    mstickspec = '';
    dataspec = formatAsXML_dataspec(blankStim.id);
    insertIntoSqlTable({blankStim.id.tstamp,blankStim.id.descId,javaspec,mstickspec,matspec,dataspec},colnames,tableName,conn);
    
    blank = blankStim; %#ok<NASGU>
    
    logger(mfilename,folderName,'Blank inserted.',conn);

    for linNum = 1:2
        count = 1;
        while count <= nStim
            stim = templateStimulus;
            
            % SHAPES
            r = (randStim.siz/2) * rand; % 0 to s/2
            th = 2*pi*rand;
            [xx,yy] = pol2cart(th,r);
            
            stim.shape.x = randStim.xPos + xx;
            stim.shape.y = randStim.yPos + yy;
            stim.shape.s = randStim.siz  * (0.6+(trandn*0.4));
            
            stim.shape.color = getShapeColor(randStim.fColor);
            stim.shape.texture = getRandTexture();
            stim.shape.doClouds = false;
            
            % MASKS
            % already initiated
            
            % OCCLUDER
            % already initiated
            
            % ID
            stim.id.linNum = linNum; 
            stim.id.genNum = genNum;
            stim.id.stimNum = count;
            stim.id.tstamp = getPosixTimeNow;
            stim.id.type = 'ga3d';
            stim.id.descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(count)];
            stim.id.respMatrix = [];
            stim.id.parentId = '';
            stim.id.parentStim = [];
            stim.id.isOccluded = false;
            stim.id.tagForRand = true;
            stim.id.tagForMorph = false;
            
            mstickspec_all{linNum,count} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,count} = stim.id.descId;
            stimuli{linNum,count} = stim;
            
            count = count + 1;
            pause(0.005)
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': ' num2str(count-1) ' random stimuli created.'],conn);
    end
    saveStimuliToDb(stimuli,mstickspec_all,colnames,tableName,conn);
    
    occluder.leftBottom = [-1 -1];
    occluder.rightTop = [-1 -1];
    occluder.color = [0 0 0];
    saveOccluderToDb(occluder,fullFolderPath,conn)
    
    save([stimPath '/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([stimPath '/' fullFolderPath '/stimIds.mat'], 'currStimIds', 'parentIds');

    save([secondaryPath '/stim/' fullFolderPath '/stimParams.mat'], 'stimuli','blank');
    save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'], 'currStimIds', 'parentIds');

    fprintf('\n');
    message = ['Generated ' fullFolderPath '.'];
    logger(mfilename,folderName,['RandGen finished. ' message],conn);
end

function texture = getRandTexture()
    probSelection = [0 0 1 0 0 0 0 0 1];
    probSelection = probSelection/sum(probSelection);
    types = {'TWOD','DOTS','SHADE','STRIPES','GRAT','HEX','QUAD','RAND3D','SPECULAR'};
    textureIdx = datasample(1:size(types,2),1,'weights',probSelection);
    texture = types{textureIdx};
end