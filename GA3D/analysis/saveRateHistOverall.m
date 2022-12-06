function saveRateHistOverall(folderName,startGen,endGen,nLin,nStim)
    getPaths;
    load([stimPath '/' folderName '_tempColFit.mat'])
    hRateHist = figure('color','k','pos',[238,327,1178,478],'name','Rate histogram per lineage');
    collatedRespLin1 = collatedRespLin1(startGen:endGen*nStim,:,:); %#ok<NASGU> % for when we reject last few gens
    collatedRespLin2 = collatedRespLin2(startGen:endGen*nStim,:,:); %#ok<NASGU> % for when we reject last few gens
    
    ha(1) = subplot(121); ha(2) = subplot(122);
    for linNum=1:nLin
        r = mean(squeeze(eval(['collatedRespLin' num2str(linNum)])),2);
        histogram(ha(linNum),r,30,'DisplayStyle','stairs','linewidth',3);
        line([mean(r) mean(r)], get(ha(linNum),'ylim'),'linewidth',3,'color','w','linestyle',':','parent',ha(linNum))
        
        set(ha(linNum),'tickDir','out','color','k','xcolor','w','ycolor','w',...
            'box','off','fontname','lato','fontsize',20,'linewidth',3,...
            'ticklength',[0.02 0.02]);
        xlabel(ha(linNum),'Firing rate (spikes/sec)','fontname','lato','fontsize',28,'color','w'); 
        ylabel(ha(linNum),'Probability','fontname','lato','fontsize',28,'color','w'); 
        title(ha(linNum),['Lineage ' num2str(linNum)],'fontname','lato','fontsize',40,'color','w','interpreter','none'); 
    end
    screen2png([plotPath '/' folderName '/' folderName '_rateHist.png'],hRateHist);
    close(hRateHist);
end