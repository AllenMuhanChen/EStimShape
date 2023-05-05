function saveAllStimPerGen(linNum,genNum,sData,thumb,folderName,fullFolderName)
    getPaths;
    hAllStimPerGen = figure('color','w','pos',[47,56,683,1100],'name','Top 10 (per gen)');
    figure(hAllStimPerGen); clf(hAllStimPerGen);
    ha = tight_subplot(8,5,0.005,0.005,0.005);
    nStim = size(sData(genNum).stimuli,2);
    for stimNum=1:nStim
        m = mean(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix);
        s = std(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix)/sqrt(5);
        imshow(thumb{linNum,stimNum},'parent',ha(stimNum));
        text('units','pixels','position',[17 27],'fontsize',13,'string',num2str(stimNum),'color','c','parent',ha(stimNum));
        text('units','pixels','position',[17 110],'fontsize',13,'string',[num2str(round(m,2)) '+-' num2str(round(s,2))],'color','c','parent',ha(stimNum));
    end
    screen2png([plotPath '/' folderName '/' fullFolderName '/' fullFolderName '_l-' num2str(linNum) '_allStim.png'],hAllStimPerGen);
    close(hAllStimPerGen);
end