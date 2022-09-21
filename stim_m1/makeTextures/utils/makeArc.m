function arccoord=makeArc(ang1,ang2,rad,dir)

%input: angle 1, angle 2: start, stop angle, both in radians
%dir: 0 convex, 1 concave



if dir==0
    %convex:
    %draw line along short angle
    if abs(ang1-ang2)<=pi
        thetavec=linspace(ang1,ang2,100);
    else
        if ang1<ang2
            thetavec=linspace(ang1+2*pi,ang2,100);
        else
            thetavec=linspace(ang1,ang2+2*pi,100);
        end
        
    end
else
    %concave:
    %draw line along long angle
    if abs(ang1-ang2)>pi
        thetavec=linspace(ang1,ang2,100);
    else
        if ang1<ang2
            thetavec=linspace(ang1+2*pi,ang2,100);
        else
            thetavec=linspace(ang1,ang2+2*pi,100);
        end
        
    end
    
end
    
[arccoord(1,:),arccoord(2,:)]=pol2cart(thetavec,rad);

