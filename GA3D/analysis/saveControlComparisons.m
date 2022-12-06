function saveControlComparisons(folderName,sData,nGen,nLin,nStim,nControl)
    getPaths;
    hControlComparisons = figure('color','k','position',[680,628,1164,470]); 
    controlResp = nan(4,2*(nGen-1)*nControl/4);
    
    firstControl = nStim-nControl+1;
    count = 1;
    for genNum=2:nGen
        for linNum=1:nLin
            for stimNum=firstControl:nStim
                controlResp(count) = mean(sData(genNum).stimuli{linNum,stimNum}.id.respMatrix);
                count = count + 1;
            end        
        end
    end
    
    [pKW,~,stats] = kruskalwallis(controlResp',[],'off');
    multCompareStats = multcompare(stats);
    
    h = subplot(121);
    groupLabels = {'SHADE','HIGH 2D','LOW 2D','SPEC'};
    hBoxPlot = notBoxPlot(controlResp',1:4);
    d = [hBoxPlot.data];
    set(d,'markerfacecolor',[0 1 1],'color',[0,0.4,0])
    alpha(0.5);
    
    set(h,'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',16,'linewidth',3,...
        'ticklength',[0.02 0.02],'XTickLabel',groupLabels,...
        'xtick',1:4,'xcolor','w','ycolor','w');

    xlabel(h,'Firing rate','fontname','lato','fontsize',16,'color','w','interpreter','none'); 
    ylabel(h,'Stimulus categories','fontname','lato','fontsize',16,'color','w','interpreter','none'); 
    title(h,'Control stimuli','fontname','lato','fontsize',20,'color','w','interpreter','none'); 
    
    hText = annotation('textbox',[.1 .1 .3 .3],'string',['KW p \leq 10^{' num2str(ceil(log10(pKW))) '}']);
    set(hText,'Position',[0.15 0.8 0.2 0.1],'FitBoxToText','on',...
        'FontName','lato','FontSize',16,'BackgroundColor','k',...
        'LineStyle','none','Color','w');
    
    h = subplot(122);
    resp3d = (controlResp(1,:) + controlResp(4,:))/2;
    resp2d = (controlResp(2,:) + controlResp(3,:))/2;
    scatter(h,resp3d,resp2d,40,'markerfacecolor','w');
    set(h,'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',16,'linewidth',3,...
        'ticklength',[0.02 0.02]);

    xlabel(h,'Firing rate - 3D Stimuli','fontname','lato','fontsize',16,'color','w','interpreter','none'); 
    ylabel(h,'Firing rate - 2D Stimuli','fontname','lato','fontsize',16,'color','w','interpreter','none'); 
    title(h,'Control stimuli','fontname','lato','fontsize',20,'color','w','interpreter','none'); 
    
    line([0 max(get(h,'xlim'))],[0 max(get(h,'xlim'))],'linewidth',3,'linestyle',':');
    
    screen2png([plotPath '/' folderName '/' folderName '_controlComparisons.png'],hControlComparisons);
    close(hControlComparisons);
end