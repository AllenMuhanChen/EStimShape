function saveTopTenPerGen(linNum,genNum,linResp,sData,thumb,folderName,fullFolderName)
    getPaths;
    hTopTenPerGen = figure('color','w','pos',[47,164,1129,900],'name','Top 10 (per gen)');
    [~,idx] = sort(linResp(:,linNum),'descend');
    idx = [idx(1:10);idx(end-9:end)];
    figure(hTopTenPerGen); clf(hTopTenPerGen);
    ha = tight_subplot(4,5,0.005,0.005,0.005);
    for ii=1:20
        m = mean(sData(genNum).stimuli{linNum,idx(ii)}.id.respMatrix);
        s = std(sData(genNum).stimuli{linNum,idx(ii)}.id.respMatrix)/sqrt(5);
        imshow(thumb{linNum,idx(ii)},'parent',ha(ii));
        text('units','pixels','position',[30 40],'fontsize',17,'string',num2str(idx(ii)),'color','c','parent',ha(ii));
        text('units','pixels','position',[30 180],'fontsize',17,'string',[num2str(round(m,2)) '+-' num2str(round(s,2))],'color','c','parent',ha(ii));
    end
    screen2png([plotPath '/' folderName '/' fullFolderName '/' fullFolderName '_l-' num2str(linNum) '_topTen.png'],hTopTenPerGen);
    close(hTopTenPerGen);
end