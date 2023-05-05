function a = circleIntersectionArea(c1,r1,c2,r2)
    d = sqrt((c1(1) - c2(1))^2 + (c1(2) - c2(2))^2); % dist bet centers
    
%     h = cla; drawCircle(h,c1(1),c1(2),r1,'b'); plot(c1(1),c1(2),'r*'); hold on; drawCircle(h,c2(1),c2(2),r2,'b'); plot(c2(1),c2(2),'r*'); grid on;
    
    cosTh = (d^2 - r2^2 + r1^2) / (2*d*r1); % disp(rad2deg(acos(cosTh))); % cos of one sector angle
    cosPh = (d^2 + r2^2 - r1^2) / (2*d*r2); % disp(rad2deg(acos(cosPh))); % cos of the other sector angle
    
    a = real((r1^2)*acos(cosTh) + (r2^2)*acos(cosPh) - 0.5*sqrt((d+r1+r2)*(-d+r1+r2)*(d-r1+r2)*(d+r1-r2)));
    if isnan(a) % a is nan iff both circles are overlapping
        a = pi * r1^2;
    end
end