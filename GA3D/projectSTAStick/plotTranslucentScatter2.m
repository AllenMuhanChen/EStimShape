function plotTranslucentScatter2(th,ph,r,col)
    r = r/max(r);
    uniR = unique(r);
    for rr=1:length(uniR)
        ind = r == uniR(rr);
        h = PlotSphereIntensity(th(ind),ph(ind),ones(sum(ind),1),col(ind));
        t = hgtransform('Parent',gca);
        set(h,'Parent',t);
        Txy = makehgtform('scale',rr);
        set(t,'Matrix',Txy)
        view(0,90); alpha(0.2); drawnow; hold on;
    end
end