function h1 = drawSemicircle(h,xc,yc,r,ori_deg,col,solid,specks)
    if ~exist('solid','var'); solid = 0; end;
    if ~exist('specks','var'); specks = []; end;
    ang= deg2rad(ori_deg-270 : 1 : ori_deg-90); 
    xp=r*cos(ang);
    yp=r*sin(ang);
    
%     diam(1,:) = [xc-r*cos(ori) xc+r*cos(ori)];
%     diam(2,:) = [yc-r*sin(ori) yc+r*sin(ori)];
    
    if solid
        h1 = patch(xp+xc,yp+yc,col,'edgecolor',col);
    else
        h1 = plot(h,xc+xp,yc+yp,'color',col);
    end
    if ~isempty(specks)
        set(h1,'edgecolor','none')
        ang = specks.ang;
        spacing = specks.spacing;
        col = specks.col;
        hatchfill(h1,'cross',ang,spacing,col);
    end
end