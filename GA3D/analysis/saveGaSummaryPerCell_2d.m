function saveGaSummaryPerCell_2d
close all
    loadedFile = load('plots/population/ids.mat');
    population = loadedFile.population;
    cellsToDo = [73 229 231 435]; % [8,67,97,104,116,131,143,152,153,164];
    for cc=1:length(cellsToDo)
        cellId = find([population.runNum] == cellsToDo(cc));
        nGen = population(cellId).nGen - population(cellId).nPostHoc;
        folderName = [num2str(population(cellId).prefix) '_r-' num2str(population(cellId).runNum)];
        saveGaSummaryPerCell_main(folderName,nGen,population(cellId).monkeyId);
    end
end

function saveGaSummaryPerCell_main(folderName,nGen,monkeyId)
    getPaths;
    % if ~exist([plotPath '/' folderName '/summaries/'],'dir')
    %     mkdir([plotPath '/' folderName '/summaries/']);
    % end
    
    nStim = 40;    
    sData = getSdata(nGen,folderName,monkeyId);
    load([stimPath '/' folderName '_tempColFit.mat'])
    
    [nonControlIds,twoDIds,controlIds] = getNonControlIds(nGen);
    nNonCtrls = length(nonControlIds);
    
    allResp = [squeeze(collatedRespLin1(1:nGen*nStim,:,:)); squeeze(collatedRespLin2(1:nGen*nStim,:,:))];
    for ii=1:size(allResp,1); allResp(ii,:) = removeoutliers(allResp(ii,:)'); end
    allResp = nanmean(allResp,2);
    nonCtrlResp = [allResp(nonControlIds) allResp(nGen*nStim+nonControlIds)];
    twoDResp = [allResp(twoDIds) allResp(nGen*nStim+twoDIds)];
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
    end
    
    % control tetrads
    controlbaseIds = [24,21,22,23,28,25,26,27,32,29,30,31,36,33,34,35,40,37,38,39];
    a = repmat(2:nGen,nStim/2,1);
    b = a(:);
    a = repmat(controlbaseIds,nGen-1,1)';
    c = a(:);
    a = ones(length(controlIds),1);
    stimId = [a b c; a+1 b c];
    
    hFig = figure('color','w','pos',[-1989,443,1974,493]);
    ha = tight_subplot(4,16,0.001,0,0); ha = reshape(ha,16,4)'; ha = ha(:);
    ctrlResp_2d = ctrlResp;
    ctrlResp_2d(1:4:end,:) = nan;
    ctrlResp_2d(2:4:end,:) = nan;
    [temp,idx] = sort(ctrlResp_2d(:),'descend');
    idx(isnan(temp)) = [];
    
    doneStim = []; tetradCount=1; hCount = 1;
    while hCount<=16*4
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
                imshow(thumb{gg,ll}{ss},'parent',ha(hCount));
                hCount = hCount + 1;
            end
        end
        tetradCount = tetradCount+1;
    end
    % screen2png([plotPath '/' folderName '/summaries/' folderName '_controlTetrads.png'],hFig);
    screen2png(['~/Desktop/' folderName '_tetradsOnly.png'],hFig);
    close(hFig);
    
    % % control tetrads
    % controlbaseIds = [24,21,22,23,28,25,26,27,32,29,30,31,36,33,34,35,40,37,38,39];
    % a = repmat(2:nGen,nStim/2,1);
    % b = a(:);
    % a = repmat(controlbaseIds,nGen-1,1)';
    % c = a(:);
    % a = ones(length(controlIds),1);
    % stimId = [a b c; a+1 b c];
    % 
    % clf(hFig);
    % ha = tight_subplot(2,8,0.005,0.005,0.005);
    % [~,idx] = sort(ctrlResp(:),'descend');
    % 
    % doneStim = []; tetradCount=1; hCount = 1;
    % hOrder = [1 2 9 10 3 4 11 12 5 6 13 14 7 8 15 16];
    % while hCount<=16
    %     currStimId = idx(tetradCount);
    %     if ~sum(doneStim == currStimId)
    %         if ~mod(currStimId,4)
    %             stimIds = 4*floor((currStimId-1)/4) + (1:4);
    %         else
    %             stimIds = 4*floor((currStimId)/4) + (1:4);
    %         end
    %         doneStim = [doneStim; stimIds];
    %         for ii=1:4
    %             ll = stimId(stimIds(ii),1); gg = stimId(stimIds(ii),2); ss = stimId(stimIds(ii),3);
    %             imshow(thumb{gg,ll}{ss},'parent',ha(hOrder(hCount)));
    %             hCount = hCount + 1;
    %         end
    %     end
    %     tetradCount = tetradCount+1;
    % end
    % % screen2png([plotPath '/' folderName '/summaries/' folderName '_controlTetrads.png'],hFig);
    % screen2png(['~/Desktop/' folderName '_controlTetrads.png'],hFig);
    
    % top 3d
    clf(hFig);
    ha = tight_subplot(4,4,0.005,0.005,0.005);
    [~,idx] = sort(nonCtrlResp(:),'descend');
    stimIdx = [[ones(40,1) ; mat2vec(repmat(2:nGen,20,1)) ; ones(40,1) ; mat2vec(repmat(2:nGen,20,1))] ...
        [ones(length(nonControlIds),1); 2*ones(length(nonControlIds),1)] ...
        [[1:40 repmat(1:20,1,nGen-1)]'; [1:40 repmat(1:20,1,nGen-1)]'] ...
        ];
    stimIdx = stimIdx(idx,:);
    
    for stimNum=1:16
        imshow(thumb{stimIdx(stimNum,1),stimIdx(stimNum,2)}{stimIdx(stimNum,3)},'parent',ha(stimNum));
    end
    screen2png(['~/Desktop/summaries/' folderName '_3d_top.png'],hFig);
    
    % top 2d
    clf(hFig);
    twoDBaseIds = [22,23,26,27,30,31,34,35,38,39];
    ha = tight_subplot(4,4,0.005,0.005,0.005);
    [~,idx] = sort(twoDResp(:),'descend');
    stimIdx = [[mat2vec(repmat(2:nGen,10,1)) ; mat2vec(repmat(2:nGen,10,1))] ...
        [ones(length(twoDIds),1); 2*ones(length(twoDIds),1)] ...
        [repmat(twoDBaseIds,1,nGen-1)'; repmat(twoDBaseIds,1,nGen-1)'] ...
        ];
    stimIdx = stimIdx(idx,:);
    
    for stimNum=1:16
        imshow(thumb{stimIdx(stimNum,1),stimIdx(stimNum,2)}{stimIdx(stimNum,3)},'parent',ha(stimNum));
    end
    screen2png(['~/Desktop/summaries/' folderName '_2d_top.png'],hFig);
    
    set(hFig,'pos',[187,42,740/2,741])
    % bottom 3d
    clf(hFig);
    ha = tight_subplot(4,2,0.005,0.005,0.005);
    [~,idx] = sort(nonCtrlResp(:));
    stimIdx = [[ones(40,1) ; mat2vec(repmat(2:nGen,20,1)) ; ones(40,1) ; mat2vec(repmat(2:nGen,20,1))] ...
        [ones(length(nonControlIds),1); 2*ones(length(nonControlIds),1)] ...
        [[1:40 repmat(1:20,1,nGen-1)]'; [1:40 repmat(1:20,1,nGen-1)]'] ...
        ];
    stimIdx = stimIdx(idx,:);
    stimIdx = flipud(stimIdx(1:8,:));
    
    for stimNum=1:8
        imshow(thumb{stimIdx(stimNum,1),stimIdx(stimNum,2)}{stimIdx(stimNum,3)},'parent',ha(stimNum));
    end
    screen2png(['~/Desktop/summaries/' folderName '_3d_bottom.png'],hFig);
    
    % bottom 2d
    clf(hFig);
    twoDBaseIds = [22,23,26,27,30,31,34,35,38,39];
    ha = tight_subplot(4,2,0.005,0.005,0.005);
    [~,idx] = sort(twoDResp(:));
    stimIdx = [[mat2vec(repmat(2:nGen,10,1)) ; mat2vec(repmat(2:nGen,10,1))] ...
        [ones(length(twoDIds),1); 2*ones(length(twoDIds),1)] ...
        [repmat(twoDBaseIds,1,nGen-1)'; repmat(twoDBaseIds,1,nGen-1)'] ...
        ];
    stimIdx = stimIdx(idx,:);
    stimIdx = flipud(stimIdx(1:8,:));
    
    for stimNum=1:8
        imshow(thumb{stimIdx(stimNum,1),stimIdx(stimNum,2)}{stimIdx(stimNum,3)},'parent',ha(stimNum));
    end
    screen2png(['~/Desktop/summaries/' folderName '_2d_bottom.png'],hFig);
    
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
                thumbPath = '/Volumes/Ram Backup/Dropbox/Documents/Hopkins/NHP2PV4/projectXper/3dma/xper_sach7/xper-sach/images';
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

function [nonControlIds,twoDIds,controlIds] = getNonControlIds(nGen)
    nonControlIds = 1:40; twoDIds = []; controlIds = [];
    twoDbaseIds = [22,23,26,27,30,31,34,35,38,39];
    controlbaseIds = [24,21,22,23,28,25,26,27,32,29,30,31,36,33,34,35,40,37,38,39];
    for genNum=2:nGen
        nonControlIds = [nonControlIds (40*(genNum-1) + 1):(40*genNum - 20)];
        twoDIds = [twoDIds 40*(genNum-1) + twoDbaseIds];
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