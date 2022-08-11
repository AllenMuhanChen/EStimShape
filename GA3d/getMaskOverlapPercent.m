function percentOverlap = getMaskOverlapPercent(mask)
    nPts = 500;
    xx = linspace(mask(1).x-mask(1).s*1.2,mask(1).x+mask(1).s*1.2,nPts);
    yy = linspace(mask(1).y-mask(1).s*1.2,mask(1).y+mask(1).s*1.2,nPts);
    
    [X,Y] = meshgrid(xx,yy);
    X = X(:); Y = Y(:);
    
    ind = (X - repmat(mask(1).x,length(X),1)).^2 + (Y - repmat(mask(1).y,length(Y),1)).^2 <= mask(1).s^2;
    X = X(ind);
    Y = Y(ind);
    
    ind = (X - mask(2).x).^2 + (Y - mask(2).y).^2 <= mask(2).s^2;
    percentOverlap = sum(ind)/length(ind);
end