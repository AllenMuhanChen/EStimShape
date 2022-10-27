function plotEyeCoords(c,l,r,t,b,eye,h)
    if strcmp(eye,'left')
        x = 1; y = 2;
    else
        x = 3; y = 4; 
    end

    hold(h,'on');
    plot(l(:,x),l(:,y),'ro','linewidth',2); plot(nanmedian(l(:,x)),nanmedian(l(:,y)),'rx','markersize',20,'linewidth',2);
    plot(r(:,x),r(:,y),'bo','linewidth',2); plot(nanmedian(r(:,x)),nanmedian(r(:,y)),'bx','markersize',20,'linewidth',2);
    plot(c(:,x),c(:,y),'co','linewidth',2); plot(nanmedian(c(:,x)),nanmedian(c(:,y)),'cx','markersize',20,'linewidth',2);
    plot(t(:,x),t(:,y),'go','linewidth',2); plot(nanmedian(t(:,x)),nanmedian(t(:,y)),'gx','markersize',20,'linewidth',2);
    plot(b(:,x),b(:,y),'wo','linewidth',2); plot(nanmedian(b(:,x)),nanmedian(b(:,y)),'wx','markersize',20,'linewidth',2);
    
    title([eye ' iscan'],'fontname','times new roman','fontsize',24,'color','w');
    
    
    
    set(h,'color','k','linewidth',2,'box','off','xcolor','w','ycolor','w',...
        'tickdir','out','ticklength',[0.03 0.03],...
        'fontsize',20,'fontname','times new roman',...
        'xlim',[-5 5],'xtick',[-5 -2.5 0 2.5 5],'ylim',[-5 5],'ytick',[-5 -2.5 0 2.5 5]);
    grid(h,'on');
    axis([nanmedian(c(:,x))-1.25 nanmedian(c(:,x))+1.25 nanmedian(c(:,y))-1.25 nanmedian(c(:,y))+1.25])
end

