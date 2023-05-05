function saveIsiPerGen(respStruct,folderName,fullFolderName)
    getPaths;
    hIsiPerGen = figure('color','k','pos',[680,379,823,719]);
    isi = [];
    for ii=1:size(respStruct,1)
        for jj=1:size(respStruct,2)
            spikes = [respStruct(ii,jj).preSpikes;respStruct(ii,jj).spikes;respStruct(ii,jj).postSpikes];
            isi = [isi;diff(spikes)]; %#ok<AGROW>
        end
    end
    histogram(isi*1000,'DisplayStyle','stairs','linewidth',5);
    
    set(gca,'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',20,'linewidth',3,...
        'ticklength',[0.02 0.02]);
    xlabel('ISI (ms)','fontname','lato','fontsize',28,'color','w'); 
    ylabel('Probability','fontname','lato','fontsize',28,'color','w'); 
    title(['ISI - ' fullFolderName],'fontname','lato','fontsize',40,'color','w','interpreter','none'); 
    
    isi(isi>0.01) = [];
    hInset = axes('position', [0.4 0.3 0.5 0.5]);
    histogram(hInset,isi*1000,'DisplayStyle','stairs','linewidth',5);
    
    set(hInset,'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',20,'linewidth',3,...
        'ticklength',[0.02 0.02],'xtick',0:2:10);
  
    screen2png([plotPath '/' folderName '/' fullFolderName '/' fullFolderName '_ISI.png'],hIsiPerGen);
    close(hIsiPerGen);
end

