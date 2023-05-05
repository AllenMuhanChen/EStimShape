function plotTranslucentScatter(th,ph,r,col)
    [x,y,z] = sph2cart(th,ph,r);
    x = x(:);
    y = y(:);
    z = z(:);
    col = col(:);
    col = (col - min(col)) / (max(col) - min(col));
    
    pts = linspace(floor(min([x;y;z])),ceil(max([x;y;z])),200);
    [xq,yq,zq] = ndgrid(pts,pts,pts); xq = xq(:); yq = yq(:); zq = zq(:);
    sphEle = xq.^2 + yq.^2 + zq.^2 <= ceil(max([x;y;z]));
    xq = xq(sphEle); yq = yq(sphEle); zq = zq(sphEle);
    
    h = scatter3(x,y,z,1500,[col zeros(length(col),2)]);
    h.Marker = '.';
    h.MarkerEdgeAlpha = 0.5;
    axis equal; view(0,90);

end