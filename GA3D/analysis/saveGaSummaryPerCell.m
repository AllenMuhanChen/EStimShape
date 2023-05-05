function saveGaSummaryPerCell
close all
    loadedFile = load('plots/population/ids.mat');
    population = loadedFile.population;
    cellsToDo = [112]; % [8,67,97,104,116,131,143,152,153,164];
    for cc=1:length(cellsToDo)
        cellId = cellsToDo(cc);
        nGen = population(cellId).nGen - population(cellId).nPostHoc;
        folderName = [num2str(population(cellId).prefix) '_r-' num2str(population(cellId).runNum)];
        saveGaSummaryPerCell_main(folderName,nGen,population(cellId).monkeyId);
    end
end

function saveGaSummaryPerCell_main(folderName,nGen,monkeyId)
    getPaths;
    
    nStim = 40;
    nStimToPlot = 7;
    
    sData = getSdata(nGen,folderName,monkeyId);
    load([stimPath '/' folderName '_tempColFit.mat'])
    
    [nonControlIds,twoDIds] = getNonControlIds(nGen);
    
    allResp = [squeeze(collatedRespLin1(1:nGen*nStim,:,:)); squeeze(collatedRespLin2(1:nGen*nStim,:,:))];
    for ii=1:size(allResp,1); allResp(ii,:) = removeoutliers(allResp(ii,:)'); end
    allResp = nanmean(allResp,2);
    nonCtrlResp = [allResp(nonControlIds); allResp(nGen*nStim+nonControlIds)];
    nonCtrlResp = reshape(nonCtrlResp,[length(nonControlIds),2]);
    twoDResp = [allResp(twoDIds); allResp(nGen*nStim+twoDIds)];
    twoDResp = reshape(twoDResp,[length(twoDIds),2]);
    cols = (allResp - nanmin(allResp)) / (nanmax(allResp) - nanmin(allResp));
    cols = reshape(cols,nGen*nStim,2);
    
    hAllStimEver = figure('color','w','pos',[187,42,911,741],'name','All stimuli ever');
    for linNum=1:2
        clf(hAllStimEver)
        ha = tight_subplot(nGen+2,nStimToPlot+4,0.005,0.005,0.005);
        ha = reshape(ha,nStimToPlot+4,nGen+2)';
        for genNum=1:nGen
            fullFolderName = [folderName '_g-' num2str(genNum)];
            if genNum == 1
                genCols{genNum} = cols(1:nStim,linNum);
                randBorder = ones(nStim,1);
                [thumb{genNum},pid] = getThumb(nStim,linNum,sData,genNum,genCols{genNum},randBorder,fullFolderName);
            else
                randBorder = zeros(nStim,1); randBorder(1:4) = 1;
                allGenCols = cols(nStim*(genNum-1)+1 : nStim*genNum,linNum);
                [thumb{genNum},pid] = getThumb(nStim,linNum,sData,genNum,allGenCols,randBorder,fullFolderName);
                genCols{genNum} = allGenCols(1:20);
                controlCols{genNum} = allGenCols(21:nStim);
            end
            
            [~,idx] = sort(genCols{genNum},'descend');
            for stimNum=1:nStimToPlot
                imshow(thumb{genNum}{idx(stimNum)},'parent',ha(genNum,stimNum));
                % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
            end
            
            stimOrder = [4 1 2 3];
            for stimNum=1:4
                if genNum == 1
                    axis(ha(genNum,nStimToPlot+stimNum),'off');
                else
                    [~,idx] = max(controlCols{genNum});
                    stimIdx =  4*(ceil(idx/4)-1);
                    imshow(thumb{genNum}{20+stimIdx+stimOrder(stimNum)},'parent',ha(genNum,nStimToPlot+stimNum));
                end
            end
            
            if genNum == 1
                hGenStim = figure('color','w','pos',[187,42,911,356],'name','All stimuli ever');
                ha_t = tight_subplot(4,10,0.005,0.005,0.005);
                [~,idx] = sort(genCols{genNum},'descend');
                for stimNum=1:nStim
                    imshow(thumb{genNum}{idx(stimNum)},'parent',ha_t(stimNum));
                end
                screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_cellSummary_gen1.png'],hGenStim);
                close(hGenStim);
            elseif genNum == 2
                hGenStim = figure('color','w','pos',[187,42,911,182],'name','All stimuli ever');
                ha_t = tight_subplot(2,10,0.005,0.005,0.005);
                [~,idx] = sort(genCols{genNum}(1:20),'descend');
                for stimNum=1:20
                    imshow(thumb{genNum}{idx(stimNum)},'parent',ha_t(stimNum));
                end
                screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_cellSummary_gen2.png'],hGenStim);
            
                clf(hGenStim);
                ha_t = tight_subplot(2,10,0.005,0.005,0.005);
                idx = [24 21 28 25 32 29 36 33 40 37 22 23 26 27 30 31 34 35 38 39];
                for stimNum=1:20
                    imshow(thumb{genNum}{idx(stimNum)},'parent',ha_t(stimNum));
                end
                screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_cellSummary_gen2_controls.png'],hGenStim);
                close(hGenStim);
            end
        end
        
        [~,idx] = sort(nonCtrlResp(:,linNum),'descend');
        allNonCtrlIds = [nonControlIds nGen*nStim+nonControlIds];
        idx = allNonCtrlIds(idx);
        gens = ceil(idx/nStim);
        stims = mod(idx,nStim);
        stims(stims==0) = nStim;
        
        for stimNum=1:nStimToPlot
            imshow(thumb{gens(stimNum)}{stims(stimNum)},'parent',ha(nGen+1,stimNum));
            % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
        end
        
        hGenStim = figure('color','w','pos',[187,42,911,356],'name','All stimuli ever');
        ha_t = tight_subplot(4,10,0.005,0.005,0.005);
        for stimNum=1:nStim
            imshow(thumb{gens(stimNum)}{stims(stimNum)},'parent',ha_t(stimNum));
        end
        screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_cellSummary_topStim.png'],hGenStim);
        close(hGenStim);
        
        gens = fliplr(gens); stims = fliplr(stims);
        for stimNum=1:nStimToPlot
            imshow(thumb{gens(stimNum)}{stims(stimNum)},'parent',ha(nGen+2,stimNum));
            % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
        end
        
        hGenStim = figure('color','w','pos',[187,42,911,356],'name','All stimuli ever');
        ha_t = tight_subplot(4,10,0.005,0.005,0.005);
        for stimNum=1:nStim
            imshow(thumb{gens(stimNum)}{stims(stimNum)},'parent',ha_t(stimNum));
        end
        screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_cellSummary_bottomStim.png'],hGenStim);
        close(hGenStim);
        
        [~,idx] = sort(twoDResp(:,linNum),'descend');
        all2dIds = [twoDIds nGen*nStim+twoDIds];
        idx = all2dIds(idx);
        gens = ceil(idx/nStim);
        stims = mod(idx,nStim);
        stims(stims==0) = nStim;
        
        for stimNum=1:4
            imshow(thumb{gens(stimNum)}{stims(stimNum)},'parent',ha(nGen+1,nStimToPlot+stimNum));
            % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
        end
        
        gens = fliplr(gens); stims = fliplr(stims);
        for stimNum=1:4
            imshow(thumb{gens(stimNum)}{stims(stimNum)},'parent',ha(nGen+2,nStimToPlot+stimNum));
            % imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
        end
        screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_cellSummary_KN.png'],hAllStimEver);
    end
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
        % im = addborderimage(im,50,[127 127 127],'out');
        
        thumb{stimNum} = im;        
    end
end

function [nonControlIds,twoDIds] = getNonControlIds(nGen)
    nonControlIds = 1:40; twoDIds = []; twoDbaseIds = [22,23,26,27,30,31,34,35,38,39];
    for genNum=2:nGen
        nonControlIds = [nonControlIds (40*(genNum-1) + 1):(40*genNum - 20)];
        twoDIds = [twoDIds 40*(genNum-1) + twoDbaseIds];
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