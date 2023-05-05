function saveControlsPerGen(genNum,genId,nStim,nControl,thumb,linNum,sData,folderName,fullFolderName)
    getPaths;
    hControlsPerGen = figure('color','w','pos',[47,6,844,1058],'name','Controls (per gen)');
    if genId > 1
        figure(hControlsPerGen); clf(hControlsPerGen);
        ha = tight_subplot(nControl/4,4,0.005,0.005,0.005);
        firstControl = nStim-nControl+1;
        for stimNum=firstControl:nStim
            imshow(thumb{linNum,stimNum},'parent',ha(stimNum-firstControl+1));
            m = mean(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix);
            s = std(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix)/sqrt(5);
            text('units','pixels','position',[30 40],'fontsize',17,'string',num2str(stimNum),'color','c','parent',ha(stimNum-firstControl+1));
            text('units','pixels','position',[30 170],'fontsize',17,'string',[num2str(round(m,2)) '+-' num2str(round(s,2))],'color','c','parent',ha(stimNum-firstControl+1));
        end
        screen2png([plotPath '/' folderName '/' fullFolderName '/' fullFolderName '_l-' num2str(linNum) '_controls.png'],hControlsPerGen);
    end
    close(hControlsPerGen);
end