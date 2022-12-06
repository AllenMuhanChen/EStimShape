function plotSphereViews(th,ph,r,intensity,clim)
    subplot(346); hold on; title('front');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    PlotSphereIntensity(th, ph, r, intensity); view(0,90); set(gca,'clim',clim);
    axis(gca,'off')
    
    subplot(348); hold on; title('back');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    h = PlotSphereIntensity(th, ph, r, intensity); view(0,90); set(gca,'clim',clim);
    t = hgtransform('Parent',gca); set(h,'Parent',t);
    Txy = makehgtform('yrotate',pi);
    set(t,'Matrix',Txy)
    axis(gca,'off')
    
    subplot(342); hold on; title('top');
    h1 = line([0 0 0],[0 1.3 0],'linewidth',5);
    h2 = PlotSphereIntensity(th, ph, r, intensity); view(0,90); set(gca,'clim',clim);
    t = hgtransform('Parent',gca); set(h1,'Parent',t); set(h2,'Parent',t);
    Txy = makehgtform('xrotate',pi/2);
    set(t,'Matrix',Txy)
    axis(gca,'off')
    
    subplot(3,4,10); hold on; title('bottom');
    h1 = line([0 0 0],[0 1.3 0],'linewidth',5);
    h2 = PlotSphereIntensity(th, ph, r, intensity); view(0,90); set(gca,'clim',clim);
    t = hgtransform('Parent',gca); set(h1,'Parent',t); set(h2,'Parent',t);
    Txy = makehgtform('xrotate',-pi/2);
    set(t,'Matrix',Txy)
    axis(gca,'off')
    
    subplot(345); hold on; title('left');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    h = PlotSphereIntensity(th, ph, r, intensity); view(0,90); set(gca,'clim',clim);
    t = hgtransform('Parent',gca); set(h,'Parent',t);
    Txy = makehgtform('yrotate',pi/2);
    set(t,'Matrix',Txy)
    axis(gca,'off')
    
    subplot(347); hold on; title('right');
    line([0 0 0],[0 1.3 0],'linewidth',5);
    h = PlotSphereIntensity(th, ph, r, intensity); view(0,90); set(gca,'clim',clim);
    t = hgtransform('Parent',gca); set(h,'Parent',t);
    Txy = makehgtform('yrotate',-pi/2);
    set(t,'Matrix',Txy)
    axis(gca,'off')
end