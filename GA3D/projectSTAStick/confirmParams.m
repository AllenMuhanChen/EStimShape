function confirmParams(stim,params)
    hold on; cla; axis([-1 1 -1 1 -1 1])
    for ii=1:size(params.s,2)
        s = params.s(:,ii);
        [x,y,z] = sph2cart(s(1),s(2),s(3));
        plot3(x,y,z,'r.','MarkerSize',30);
        [tx,ty,tz] = sph2cart(s(4),s(5),0.3);
        line([x x+tx],[y y+ty],[z z+tz],'linewidth',2,'color','r');
        r = s(6);
        draw3dcircle(gca,r,[tx ty tz],[x y z])
    end
    
    for ii=1:size(params.t,2)
        s = params.t(:,ii);
        [x,y,z] = sph2cart(s(1),s(2),s(3));
        plot3(x,y,z,'b.','MarkerSize',30);
        [tx,ty,tz] = sph2cart(s(4),s(5),0.3);
        line([x x+tx],[y y+ty],[z z+tz],'linewidth',2,'color','b');
        r = s(6);
        draw3dcircle(gca,r,[tx ty tz],[x y z])
    end
    
    for ii=1:size(params.r,2)
        s = params.r(:,ii);
        [x,y,z] = sph2cart(s(1),s(2),s(3));
        plot3(x,y,z,'g.','MarkerSize',30);
        [tx,ty,tz] = sph2cart(s(4),s(5),0.3);
        line([x x+tx],[y y+ty],[z z+tz],'linewidth',2,'color','g');
        r = s(6);
        draw3dcircle(gca,r,[tx ty tz],[x y z])
    end
    axis equal; view(0,90);
end

function draw3dcircle(h,rad,tang,center)
    % rotation vector magic for the circles
    ssc = @(v) [0 -v(3) v(2); v(3) 0 -v(1); -v(2) v(1) 0];
    RU = @(A,B) eye(3) + ssc(cross(A,B)) + ssc(cross(A,B))^2*(1-dot(A,B))/(norm(cross(A,B))^2);
    
    [xx,yy] = pol2cart(linspace(0,2*pi,100),rad*ones(1,100));
    zz = zeros(1,100);

    rotVec = RU([0 0 1],tang);
    a = rotVec * [xx; yy; zz];

    scatter3(h,a(1,:)+center(1),a(2,:)+center(2),a(3,:)+center(3),'c.');
end