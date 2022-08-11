 function [message,nStim] = runProliferation_posthoc_singleGabor(folderName,gaInfo,postHocId,randStim,conn)
    genNum = gaInfo.genNum;

    getPaths;
    fullFolderPath = [folderName '_g-' num2str(genNum)];
    message = ['Generating ' fullFolderPath '.'];
    logger(mfilename,folderName,'Proliferation started for single gabor posthoc.',conn);
    disp(message);

    if exist([stimPath '/' fullFolderPath '/stimIds.mat'],'file') == 0
        message = 'Parent IDs not found'; return;
    else
        load([stimPath '/' fullFolderPath '/stimIds.mat'],'parentIdsPosthoc');
        if isempty(parentIdsPosthoc) 
            message = 'Parent IDs not found'; return;
        end
    end
    parentStim = getStimParams(parentIdsPosthoc{1});

    colnames = {'id','descId','javaspec','mstickspec','matspec','dataspec'};
    tableName = 'StimObjData';

    load('templateStimulus.mat','templateStimulus');
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

    blank = blankStim;

    logger(mfilename,folderName,'Blank inserted.',conn);

    load([stimPath '/' folderName '_tempColFit.mat']); %#ok<LOAD>
    nStim = 40;

    currStimIds = cell(2,nStim);
    stimuli = cell(2,nStim);
    mstickspec_all = cell(2,nStim);
    
    gaborParams = getGaborParams;
    saveGaborImages(gaborParams,fullFolderPath);
    
    for linNum=1:2
        for stimNum=1:nStim
            stim = parentStim;

            % SHAPE
            stim.shape.x = randStim.xPos;
            stim.shape.y = randStim.yPos;
            stim.shape.s = randStim.siz;
            stim.shape.texture = 'GABOR1';
            stim.shape.gaborParams = gaborParams(2*(linNum-1)+stimNum);

            % ID
            stim.id.linNum = linNum;
            stim.id.genNum = genNum;
            stim.id.stimNum = stimNum;
            stim.id.tstamp = getPosixTimeNow;
            stim.id.type = 'ga3d';
            stim.id.descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(stimNum)];
            stim.id.respMatrix = [];
            stim.id.parentId = parentStim.id.descId;
            stim.id.parentStim = parentStim;
            stim.id.tagForRand = false;
            stim.id.tagForMorph = false;
            stim.id.saveVertSpec = false;
            stim.id.posthocId = postHocId;

            mstickspec_all{linNum,stimNum} = stim.shape.mstickspec;

            % SAVE TO MAT FILE
            currStimIds{linNum,stimNum} = stim.id.descId;
            stimuli{linNum,stimNum} = stim;
        end
        logger(mfilename,folderName,['Gen ' num2str(genNum) ', lin ' num2str(linNum) ': 40 gabor1 posthoc stimuli created.'],conn);
    end

    nStim = size(stimuli,2);

    saveStimuliToDb(stimuli,mstickspec_all,colnames,tableName,conn);

    occluder.leftBottom = [-1 -1];
    occluder.rightTop = [-1 -1];
    occluder.color = [0 0 0];
    saveOccluderToDb(occluder,fullFolderPath,conn)

    save([stimPath '/' fullFolderPath '/stimParams.mat'],'stimuli','blank','gaborParams');
    save([stimPath '/' fullFolderPath '/stimIds.mat'],'currStimIds','-append');

    save([secondaryPath '/stim/' fullFolderPath '/stimParams.mat'],'stimuli','blank','gaborParams');
    save([secondaryPath '/stim/' fullFolderPath '/stimIds.mat'],'currStimIds','-append');

    fprintf('\n');
    message = ['Generated ' fullFolderPath '.'];
    logger(mfilename,folderName,['Proliferation for gabor variants posthoc finished. ' message],conn);

    system(['ssh m1_ram@172.30.6.25 ''mkdir /home/m1_ram/Documents/xper/3dga/dist/sach/images/' fullFolderPath '_GABOR1''']);
    system(['scp -prq ' stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_gabor1/* m1_ram@172.30.6.25:/home/m1_ram/Documents/xper/3dga/dist/sach/images/' fullFolderPath '_GABOR1/.']);
 end

function params = getGaborParams()
    % same across all stim and cells
    param.pos = [0 0];
    param.cont = 1;
    
    % unique to cell
    param.sw = input('Enter sf (0.5-6): ');
    param.siz = input('Enter size (0.1-1.5)pi: ');
    param.aRatio = validatedInput('Enter aspect ratio (0.5 1 2): ',[0.5 1 2]);
    
    % repeat values
    ori = linspace(0,2*pi,9);
    ori = ori(validatedInput('Enter ori (1-4): ',1:4));
    ori = [ori ori+pi/2];
    phase = [0 pi/2 pi 3*pi/2];
    cols = getAllColours();
    
    % repeat params
    o = repmat(1:2,40,1); o = o(:);
    p = repmat(1:4,10,1); p = [p(:);p(:)];
	c = repmat(1:10,1,8); c = c(:);
    ori = ori(o); % 2*pi*rand(1,80);
    phase = phase(p);
    cols = cols(c,:);
    
    for ii=1:80
        param.ori = ori(ii);
        param.phase = phase(ii);
        param.col = [cols(ii,1:3); cols(ii,4:6)];
        
        params(ii) = param;
    end
end

function saveGaborImages(params,fullFolderPath)
    getPaths;
    nPix = [640 480]*2;
    [x,y] = meshgrid(linspace(-4*pi,4*pi,nPix(1)),linspace(-3*pi,3*pi,nPix(2)));
    
    % COPY IMAGES TO CORRECT FOLDER
    destFolder = [stimPath '/' fullFolderPath '/thumbnails/' fullFolderPath '_gabor1'];
    if ~exist(destFolder,'dir'); mkdir(destFolder); end
    
    for linNum=1:2
        for stimNum=1:40
            param = params(40*(linNum-1)+stimNum);
            [gb,al] = getGabor(param,x,y);

            descId = [fullFolderPath '_l-' num2str(linNum) '_s-' num2str(stimNum)];
            % imFile = [plotPath '/temp_gabor/' descId '.png'];
            imFile = [destFolder '/' descId '.png'];
            
            al = round(al,3); gb1 = 0.3 + repmat(al,1,1,3).*(gb-0.3);
            % imwrite(gb,imFile,'Background',[0.3 0.3 0.3],'Alpha',al);
            
            % change to 2048x1024
            gb1 = padarray(gb1,[0 384],0);
            gb1 = padarray(gb1,32,0);
            imwrite(gb1,imFile);
        end
    end
end

function [gb,al] = getGabor(param,x,y)
    theta = param.ori;
    lambda = param.sw;
    psi = param.phase;
    sigma = param.siz;
    alpha = param.cont;
    gamma = param.aRatio;
    
    sigma_x = sigma;
    sigma_y = sigma/gamma;

    x_theta=x*cos(theta)+y*sin(theta);
    y_theta=-x*sin(theta)+y*cos(theta);

    gb1 = (1+cos(2*pi/lambda*x_theta+psi))/2;
    gb2 = (1+cos(2*pi/lambda*x_theta+psi+pi))/2;
    
    al = alpha.*exp(-.5*(x_theta.^2/sigma_x^2+y_theta.^2/sigma_y^2));
    
    gb1 = padarray(gb1,size(gb1)/2);
    gb2 = padarray(gb2,size(gb2)/2);
    al = padarray(al,size(al)/2);
    
    shift = round(fliplr(param.pos)./[-abs(x(1,1)-x(1,2)) abs(y(1,1)-y(2,1))]);
    gb1 = circshift(gb1,shift);
    gb2 = circshift(gb2,shift);
    al = circshift(al,shift);
    
    win1 = centerCropWindow2d(size(al),size(x));
    gb1 = imcrop(gb1,win1);
    gb2 = imcrop(gb2,win1);
    al = imcrop(al,win1);
    
    gb1 = repmat(gb1,1,1,3);
    gb2 = repmat(gb2,1,1,3);
    
    c1 = repmat(reshape(param.col(1,:),[1,1,3]),size(gb1,1),size(gb1,2),1);
    c2 = repmat(reshape(param.col(2,:),[1,1,3]),size(gb1,1),size(gb1,2),1);
    
    gb = gb1 .* c1 + gb2 .* c2;
end

function cols = getAllColours
    cols( 1,:) = [1 1 1 0 0 0];
    cols( 2,:) = [1 0 0 0 0 0];
    cols( 3,:) = [0 1 0 0 0 0];
    cols( 4,:) = [0 0 1 0 0 0];
    cols( 5,:) = [0 1 1 0 0 0];
    cols( 6,:) = [1 0 1 0 0 0];
    cols( 7,:) = [1 1 0 0 0 0];
    cols( 8,:) = [1 0 0 0 1 1];
    cols( 9,:) = [0 1 0 1 0 1];
    cols(10,:) = [0 0 1 1 1 0];
end