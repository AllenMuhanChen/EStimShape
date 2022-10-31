function movedPts = movePts(pts,x,y,s,o,rotateAboutXY)    
    [th,r] = cart2pol(pts(:,1) - rotateAboutXY(1),pts(:,2) - rotateAboutXY(2));
    th = th+deg2rad(o);
    [x1,y1] = pol2cart(th,r);
    
    movedPts = [x1 y1] * s;
        
    movedPts = movedPts + repmat(rotateAboutXY,size(pts,1),1);
    
    movedPts(:,1) = movedPts(:,1) + x;
    movedPts(:,2) = movedPts(:,2) + y;
end
