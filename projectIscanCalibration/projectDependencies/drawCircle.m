function h1 = drawCircle(h,x,y,r,col,solid,specks)
    if ~exist('solid','var'); solid = zeros(length(x),1); end;
    if ~exist('specks','var'); specks = zeros(length(x),1); end;
    if length(x) > size(col,1)
        col = repmat(col,length(x),1);
    end
    ang=0:0.01:2*pi; 
    for ii=1:length(x)
        xp=r(ii)*cos(ang);
        yp=r(ii)*sin(ang);
        if solid(ii)
            h1 = patch(xp+x(ii),yp+y(ii),col(ii,:),'edgecolor',col(ii,:),'parent',h);
        else
            h1 = plot(h,x(ii)+xp,y(ii)+yp,'color',col(ii,:),'linewidth',2);
        end
        if specks
            hatchfill(h1,'cross',45,5,[0.4 0.4 0.4]);
        end
    end
end