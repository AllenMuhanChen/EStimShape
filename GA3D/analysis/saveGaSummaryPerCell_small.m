function saveGaSummaryPerCell_small
close all
    loadedFile = load('plots/population/ids.mat');
    population = loadedFile.population;
    cellsToDo = 271; % [73 229 231 435]; % [8,67,97,104,116,131,143,152,153,164];
    for cc=1:length(cellsToDo)
        cellId = find([population.runNum] == cellsToDo(cc));
        nGen = population(cellId).nGen - population(cellId).nPostHoc;
        folderName = [num2str(population(cellId).prefix) '_r-' num2str(population(cellId).runNum)];
        saveGaSummaryPerCell_main(folderName,nGen,population(cellId).monkeyId);
    end
end

function saveGaSummaryPerCell_main(folderName,nGen,monkeyId)
    getPaths;
    if ~exist([plotPath '/' folderName '/summaries/'],'dir')
        mkdir([plotPath '/' folderName '/summaries/']);
    end
    
    nStim = 40;    
    sData = getSdata(nGen,folderName,monkeyId);
    load([stimPath '/' folderName '_tempColFit.mat'])
    
    [nonControlIds,twoDIds,threeDIds,controlIds] = getNonControlIds(nGen);
    nNonCtrls = length(nonControlIds);
    
    allResp = [squeeze(collatedRespLin1(1:nGen*nStim,:,:)); squeeze(collatedRespLin2(1:nGen*nStim,:,:))];
    for ii=1:size(allResp,1); allResp(ii,:) = removeoutliers(allResp(ii,:)'); end
    allResp = nanmean(allResp,2);
    nonCtrlResp = [allResp(nonControlIds) allResp(nGen*nStim+nonControlIds)];
    twoDResp = [allResp(twoDIds) allResp(nGen*nStim+twoDIds)];
    threeDResp = [allResp(threeDIds) allResp(nGen*nStim+threeDIds)];
    ctrlResp = [allResp(controlIds) allResp(nGen*nStim+controlIds)];
    cols = (allResp - nanmin(allResp)) / (nanmax(allResp) - nanmin(allResp));
    cols = reshape(cols,nGen*nStim,2);
    
    hFig = figure('color','w','pos',[187,42,740,741]);
    for linNum=1:2
        for genNum=1:nGen
            fullFolderName = [folderName '_g-' num2str(genNum)];
            if genNum == 1
                genCols{genNum,linNum} = cols(1:nStim,linNum);
                randBorder = ones(nStim,1);
                thumb{genNum,linNum} = getThumb(nStim,linNum,sData,genNum,genCols{genNum,linNum},randBorder,fullFolderName);
            else
                randBorder = zeros(nStim,1); randBorder(1:4) = 1;
                allGenCols = cols(nStim*(genNum-1)+1 : nStim*genNum,linNum);
                thumb{genNum,linNum} = getThumb(nStim,linNum,sData,genNum,allGenCols,randBorder,fullFolderName);
                genCols{genNum,linNum} = allGenCols(1:20);
                controlCols{genNum,linNum} = allGenCols(21:nStim);
            end
        end
        
        clf(hFig);
        ha = tight_subplot(4,4,0.005,0.005,0.005);
        [~,idx] = sort(nonCtrlResp(:,linNum),'descend');
        % allNonCtrlIds = [nonControlIds nGen*nStim+nonControlIds];
        idx = nonControlIds(idx);
        gens = ceil(idx/nStim);
        stims = mod(idx,nStim);
        stims(stims==0) = nStim;
        
        for stimNum=1:16
            imshow(thumb{gens(stimNum),linNum}{stims(stimNum)},'parent',ha(stimNum));
            % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
        end
        % screen2png([plotPath '/' folderName '/summaries/' folderName '_l-' num2str(linNum) '_top.png'],hFig);
        screen2png(['~/Desktop/summaries/' folderName '_l-' num2str(linNum) '_top.png'],hFig);
    end
    
    % control tetrads
    controlbaseIds = [24,21,22,23,28,25,26,27,32,29,30,31,36,33,34,35,40,37,38,39];
    threeDbaseIds = [24,23,28,27,32,31,36,35,40,37];
    a = repmat(2:nGen,nStim/2,1);
    b = a(:);
    a = repmat(controlbaseIds,nGen-1,1)';
    c = a(:);
    a = ones(length(controlIds),1);
    stimId = [a b c; a+1 b c];
    
    clf(hFig);
    ha = tight_subplot(4,4,0.005,0.005,0.005);
    ctrlResp_3d = ctrlResp;
    ctrlResp_3d(3:4:end,:) = nan;
    ctrlResp_3d(4:4:end,:) = nan;
    [temp,idx] = sort(ctrlResp_3d(:),'descend');
    idx(isnan(temp)) = [];
    
    doneStim = []; tetradCount=1; hCount = 1;
    hOrder = [1 2 5 6 3 4 7 8 9 10 13 14 11 12 15 16];
    while hCount<=16
        currStimId = idx(tetradCount);
        if ~sum(doneStim == currStimId)
            if ~mod(currStimId,4)
                stimIds = 4*floor((currStimId-1)/4) + (1:4);
            else
                stimIds = 4*floor((currStimId)/4) + (1:4);
            end
            doneStim = [doneStim; stimIds];
            for ii=1:4
                ll = stimId(stimIds(ii),1); gg = stimId(stimIds(ii),2); ss = stimId(stimIds(ii),3);
                imshow(thumb{gg,ll}{ss},'parent',ha(hOrder(hCount)));
                hCount = hCount + 1;
            end
        end
        tetradCount = tetradCount+1;
    end
    % screen2png([plotPath '/' folderName '/summaries/' folderName '_controlTetrads.png'],hFig);
    screen2png(['~/Desktop/summaries/' folderName '_controlTetrads.png'],hFig);
    
    
%     % bottom solid
%     a = repmat(2:nGen,nStim/2,1);
%     b = [ones(nStim,1); a(:)];
%     a = repmat(1:nStim/2,nGen-1,1)';
%     c = [transpose(1:nStim); a(:)];
%     a = ones(nNonCtrls,1);
%     stimId = [a b c; a+1 b c];
%     clf(hFig); set(hFig,'pos',[187,42,370,741]);
%     ha = tight_subplot(4,2,0.005,0.005,0.005);
%     [~,idx] = sort(nonCtrlResp(:));
%     
%     for stimNum=1:8
%         ll = stimId(idx(stimNum),1); gg = stimId(idx(stimNum),2); ss = stimId(idx(stimNum),3);
%         imshow(thumb{gg,ll}{ss},'parent',ha(stimNum));
%         % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
%     end
%     screen2png([plotPath '/' folderName '/summaries/' folderName '_bot.png'],hFig);
%     
%     % top 2d
%     a = repmat(2:nGen,nStim/4,1);
%     b = a(:);
%     a = repmat((nStim/2+1):nStim,nGen-1,1)';
%     non2dIds = sort([4*(0:4) + 1 4*(1:5)]);
%     a(non2dIds,:) = [];
%     c = a(:);
%     a = ones(length(twoDIds),1);
%     
%     stimId = [a b c; a+1 b c];
%     clf(hFig); set(hFig,'pos',[187,42,370,741]);
%     ha = tight_subplot(4,2,0.005,0.005,0.005);
%     [~,idx] = sort(twoDResp(:),'descend');
%     
%     for stimNum=1:8
%         ll = stimId(idx(stimNum),1); gg = stimId(idx(stimNum),2); ss = stimId(idx(stimNum),3);
%         imshow(thumb{gg,ll}{ss},'parent',ha(stimNum));
%         % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
%     end
%     screen2png([plotPath '/' folderName '/summaries/' folderName '_top2d.png'],hFig);
end

function sData = getSdata(nGen,folderName,monkeyId)
    getPaths;
    for genNum=1:nGen
        fullFolderName = [folderName '_g-' num2str(genNum)];
        sData(genNum) = load([stimPath '/' fullFolderName '/stimParams.mat']); %#ok<AGROW>
    end
end

function [thumb,pid] = getThumb(nStim,linNum,sData,genNum,genCols,randBorder,fullFolderName)
    getPaths;
    thumb = cell(nStim,1);
    pid = zeros(nStim,2);
    
    contrastHack = 0.2;
    for stimNum=1:nStim
        stim = sData(genNum).stimuli{linNum,stimNum};
        
        if ~isempty(stim.id.parentId)
            [~,~,gen,~,stm] = splitDelimitedStimID2(stim.id.parentId);
            pid(stimNum,:) = [gen stm];
        end
        
        tex = stim.shape.texture;
        col = stim.shape.color;
        if strcmp(tex,'TWOD') && contrastHack == 0.2
            contrastHack = 0.7;
            contrast = 0.7;
        elseif strcmp(tex,'TWOD') && contrastHack == 0.7
            contrastHack = 0.2;
            contrast = 0.2;
        else
            contrast = 1;
        end
        
        doRedBack = false;
        redoImage = false;
        if doRedBack
            im = makeImageFromSpec(stim.id.tstamp,stim.shape.mstickspec,tex,contrast,col,[genCols(stimNum) 0 0]);
        else
            if redoImage
                im = makeImageFromSpec(stim.id.tstamp,stim.shape.mstickspec,tex,contrast,col,[0.5 0.5 0.5]);
            else
                im = imread([thumbPath '/' fullFolderName '/' num2str(stim.id.tstamp) '.png']);
            end
        end
        im = imcrop(im,[100 100 400 400]);
%         if randBorder(stimNum)
%             im = addborderimage(im,10,[0 255 0],'out');
%         else
%             im = addborderimage(im,10,[0 0 255],'out');
%         end
        im = addborderimage(im,50,255*[genCols(stimNum) 0 0],'out');
        thumb{stimNum} = im;        
    end
end

function [nonControlIds,twoDIds,threeDIds,controlIds] = getNonControlIds(nGen)
    nonControlIds = 1:40; twoDIds = []; controlIds = []; threeDIds = [];
    twoDbaseIds = [22,23,26,27,30,31,34,35,38,39];
    controlbaseIds = [24,21,22,23,28,25,26,27,32,29,30,31,36,33,34,35,40,37,38,39];
    threeDbaseIds = [24,23,28,27,32,31,36,35,40,37];
    for genNum=2:nGen
        nonControlIds = [nonControlIds (40*(genNum-1) + 1):(40*genNum - 20)];
        twoDIds = [twoDIds 40*(genNum-1) + twoDbaseIds];
        threeDIds = [threeDIds 40*(genNum-1) + threeDbaseIds];
        controlIds = [controlIds 40*(genNum-1) + controlbaseIds];
    end
end

function randIds = getRandIds(nGen)
    randIds = 1:40;
    for ii=2:nGen
        randIds = [randIds (40*(ii-1) + 1):(40*(ii-1) + 4)];
    end
end

function im = makeImageFromSpec(fileName,spec,texture,contrast,col,redLevel)
    imgGenPath = pwd;
    javaLibPath = ['-Djava.library.path=' imgGenPath '/dep/native/lwjgl/macos'];
    javaJarPath_genRand = [imgGenPath '/dep/generateStimuli.jar'];
    javaJarPath_genMorph = [imgGenPath '/dep/morphStimuli.jar'];
    imagePathCell = [imgGenPath '/dep/tempImage'];

    scale = 12;
    
    if ~exist([imagePathCell '/' num2str(fileName) '_spec.xml'],'file')
        fid = fopen([imagePathCell '/' num2str(fileName) '_spec.xml'],'w+');
        fwrite(fid,spec);
        fclose(fid);
    end
    if ~exist([imagePathCell '/' num2str(fileName) '.png'],'file')
        morphStr = ['java ' javaLibPath ' -jar ' javaJarPath_genMorph  ' ' imagePathCell ' ' num2str(fileName) ' ' num2str(fileName) ' 0 ' texture ' ' num2str(col(1)) ' ' num2str(col(2)) ' ' num2str(col(3)) ' ' num2str(contrast) ' ' num2str(scale) ' false ' num2str(redLevel(1)) ' ' num2str(redLevel(2)) ' ' num2str(redLevel(3))];
        system(morphStr);
    end
    im = imread([imagePathCell '/' num2str(fileName) '.png']);
end