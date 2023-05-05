function saveAllStimEver
    getPaths;
    
    folderName = '170806_r-271';
    
    nGen = 7;
    nStim = 40;
    nStimToPlot = 20;
    
    sData = getSdata(nGen,folderName);
    load([stimPath '/' folderName '_tempColFit.mat'])
    
    nonControlIds = getNonControlIds(nGen);
    
    resp = [squeeze(mean(collatedRespLin1(nonControlIds,:,:),3)); squeeze(mean(collatedRespLin2(nonControlIds,:,:),3))];
    cols = (resp - min(resp)) / (max(resp) - min(resp));
    cols = reshape(cols,length(nonControlIds),2);
    
    hAllStimEver = figure('color','w','pos',[47,5,1143,800],'name','All stimuli ever');
    for linNum=1:2
        clf(hAllStimEver)
        ha = tight_subplot(nGen,nStimToPlot,0.005,0.005,0.005);
        for genNum=1:nGen
            fullFolderName = [folderName '_g-' num2str(genNum)];
            if genNum == 1
                genCols = cols(1:nStim,linNum);
                randBorder = ones(nStim,1);
                [thumb,pid] = getThumb(nStim,linNum,sData,genNum,genCols,randBorder,fullFolderName);
            else
                randBorder = zeros(20,1); randBorder(1:4) = 1;
                genCols = cols(20*genNum+1:20*(genNum+1),linNum);
                [thumb,pid] = getThumb(20,linNum,sData,genNum,genCols,randBorder,fullFolderName);
            end
            
            
            [~,idx] = sort(genCols,'descend');
            for stimNum=1:nStimToPlot
                imshow(thumb{idx(stimNum)},'parent',ha(nStimToPlot*(genNum-1)+stimNum));
                imwrite(thumb{idx(stimNum)},['~/Desktop/temp/l-' num2str(linNum) '_g-' num2str(genNum) '_s-' num2str(idx(stimNum)) '.png']);
                
                if pid(idx(stimNum),1) ~= 0
%                     text('units','pixels','position',[78 87],'fontsize',13,'string',num2str(pid(idx(stimNum),2)),'color','c','parent',ha(10*(genNum-1)+stimNum));
%                     text('units','pixels','position',[20 87],'fontsize',13,'string',num2str(pid(idx(stimNum),1)),'color','c','parent',ha(10*(genNum-1)+stimNum));
                end
%                 text('units','pixels','position',[78 24],'fontsize',13,'string',num2str(idx(stimNum)),'color','k','parent',ha(10*(genNum-1)+stimNum));
            end
            
        end
        screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_allStimEver.png'],hAllStimEver);
    end
end

function sData = getSdata(nGen,folderName)
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
    
    for stimNum=1:nStim
        stim = sData(genNum).stimuli{linNum,stimNum};   
        if ~isempty(stim.id.parentId)
            [~,~,gen,~,stm] = splitDelimitedStimID2(stim.id.parentId);
            pid(stimNum,:) = [gen stm];
        end
        
        im = imread([thumbPath '/' fullFolderName '/' num2str(stim.id.tstamp) '.png']);
        im = imcrop(im,[150 150 300 300]);
%         if randBorder(stimNum)
%             im = addborderimage(im,10,[0 255 0],'out');
%         else
%             im = addborderimage(im,10,[0 0 255],'out');
%         end
        im = addborderimage(im,30,255*[genCols(stimNum) 0 0],'out');
        thumb{stimNum} = im;        
    end
end

function nonControlIds = getNonControlIds(nGen)
    nonControlIds = 1:40;
    for ii=2:nGen
        nonControlIds = [nonControlIds (40*(ii-1) + 1):(40*ii - 20)];
    end
end

function randIds = getRandIds(nGen)
    randIds = 1:40;
    for ii=2:nGen
        randIds = [randIds (40*(ii-1) + 1):(40*(ii-1) + 4)];
    end
end