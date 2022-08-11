function plotStim_equalizeAxes(ha)
    xLims = nan(length(ha),2);
    yLims = nan(length(ha),2);

    for ii=1:length(ha)
        xLims(ii,:) = get(ha(ii),'xlim');
        yLims(ii,:) = get(ha(ii),'ylim');
    end
    
    x = [min(xLims(:,1)) max(xLims(:,2))];
    y = [min(yLims(:,1)) max(yLims(:,2))];
    
    for ii=1:length(ha)
        set(ha(ii),'xlim',x);
        set(ha(ii),'ylim',y);
    end 
end

