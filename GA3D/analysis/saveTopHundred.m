function saveTopHundred(folderName,sData,startGen,endGen,nLin,nStim)
    getPaths;
    load([stimPath '/' folderName '_tempColFit.mat'])
    hHundred = figure('color','w','pos',[12,6,1098,1099],'name','Top 100 (overall)');
    collatedRespLin1 = collatedRespLin1(startGen:endGen*nStim,:,:); %#ok<NASGU> % for when we reject last few gens
    collatedRespLin2 = collatedRespLin2(startGen:endGen*nStim,:,:); %#ok<NASGU> % for when we reject last few gens
    for linNum=1:nLin
        [r,idx] = sort(mean(squeeze(eval(['collatedRespLin' num2str(linNum)])),2),'descend');
        % [r,idx] = sort(eval(['collatedZRespLin' num2str(linNum)]),'descend');
        cols = (r - min(r)) / (max(r) - min(r));
        if length(idx) > 100
            idx = idx(1:100);
        end
        figure(hHundred); clf(hHundred);
        ha = tight_subplot(10,10,0.005,0.005,0.005);
        for ii=1:length(idx)
            stimNum = idx(ii);
            id = collatedStimIds{linNum,stimNum}; %#ok<USENS>
            [~,~,genNum,~,genStimNum] = splitDelimitedStimID2(id);
            stim = sData(genNum).stimuli{linNum,genStimNum};
            m = mean(stim.id.respMatrix);
            s = std(stim.id.respMatrix)/sqrt(5);
            im = imread([thumbPath '/' folderName '_g-' num2str(genNum) '/' num2str(stim.id.tstamp) '.png']);
            im = imcrop(im,[150 150 300 300]);
            im = addborderimage(im,30,255*[cols(ii) 0 0],'out');
            imshow(im,'parent',ha(ii));
%             text('units','pixels','position',[15 20],'fontsize',10,'string',num2str(genNum),'color','c','parent',ha(ii));
%             text('units','pixels','position',[77 20],'fontsize',10,'string',num2str(genStimNum),'color','c','parent',ha(ii));
%             text('units','pixels','position',[17 87],'fontsize',10,'string',[num2str(round(m,2)) '+-' num2str(round(s,2))],'color','c','parent',ha(ii));
        end
        screen2png([plotPath '/' folderName '/' folderName '_l-' num2str(linNum) '_topHundred.png'],hHundred);
    end
    close(hHundred);
end