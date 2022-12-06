function saveBlankAndBest(nGen,best_mean,best_sem,blank_mean,blank_sem,folderName)
    getPaths;
    hBlankAndBest = figure('color','k','position',[680,399,833,699]); 
    h = gca; hold(h,'on');
    errorbar(h,1:nGen,blank_mean,blank_sem,'c','linewidth',2);
    errorbar(1:nGen,best_mean(:,1),best_sem(:,1),'m','linewidth',2);
    errorbar(1:nGen,best_mean(:,2),best_sem(:,2),'g','linewidth',2)
    hL = legend({'Blank','Best Lin 1','Best Lin 2'},'location','northwest');
    set(hL,'color',[0.7 0.7 0.7],'linewidth',2,'edgecolor',[0.7 0.7 0.7]);
    plot(h,1:nGen,blank_mean,'co','linewidth',2,'markersize',10,'markerfacecolor','k');
    plot(h,1:nGen,best_mean(:,1),'mo','linewidth',2,'markersize',10,'markerfacecolor','k');
    plot(h,1:nGen,best_mean(:,2),'go','linewidth',2,'markersize',10,'markerfacecolor','k');

    set(h,'tickDir','out','color','k','xcolor','w','ycolor','w',...
        'box','off','fontname','lato','fontsize',16,'linewidth',3,...
        'ticklength',[0.02 0.02],'xlim',[0 nGen+1],...
        'xtick',1:nGen,'xcolor','w','ycolor','w');

    xlabel(h,'Generation Number','fontname','lato','fontsize',16,'color','w'); 
    ylabel(h,'Firing Rate','fontname','lato','fontsize',16,'color','w'); 
    title(h,'Blank and Best Stimuli','fontname','lato','fontsize',20,'color','w','interpreter','none'); 
    screen2png([plotPath '/' folderName '/' folderName '_blankAndBest.png'],hBlankAndBest);
    close(hBlankAndBest);
end