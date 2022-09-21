function [gb,al] = getGabor(param,x,y)
    theta = param.ori;
    lambda = param.sw;
    psi = param.phase;
    sigma = param.siz;
    alpha = param.cont;
    gamma = param.aRatio;
    
    sigma_x = sigma;
    sigma_y = sigma/gamma;

    x_theta=x*cos(theta)+y*sin(theta);
    y_theta=-x*sin(theta)+y*cos(theta);

    gb1 = (1+cos(2*pi/lambda*x_theta+psi))/2;
    gb2 = (1+cos(2*pi/lambda*x_theta+psi+pi))/2;
    
    al = alpha.*exp(-.5*(x_theta.^2/sigma_x^2+y_theta.^2/sigma_y^2));
    
    gb1 = padarray(gb1,size(gb1)/2);
    gb2 = padarray(gb2,size(gb2)/2);
    al = padarray(al,size(al)/2);
    
    shift = round(fliplr(param.pos)./[-abs(x(1,1)-x(1,2)) abs(y(1,1)-y(2,1))]);
    gb1 = circshift(gb1,shift);
    gb2 = circshift(gb2,shift);
    al = circshift(al,shift);
    
    a = size(x,1)/2 + 1;
    b = 3*size(x,1)/2;
    c = size(x,2)/2 + 1;
    d = 3*size(x,2)/2;
    al = al(a:b,c:d);
    gb1 = gb1(a:b,c:d);
    gb2 = gb2(a:b,c:d);
    
    % win1 = centerCropWindow2d(size(al),size(x));
    % gb1 = imcrop(gb1,win1);
    % gb2 = imcrop(gb2,win1);
    % al = imcrop(al,win1);
    
    gb1 = repmat(gb1,1,1,3);
    gb2 = repmat(gb2,1,1,3);
    
    c1 = repmat(reshape(param.col(1,:),[1,1,3]),size(gb1,1),size(gb1,2),1);
    c2 = repmat(reshape(param.col(2,:),[1,1,3]),size(gb1,1),size(gb1,2),1);
    
    gb = gb1 .* c1 + gb2 .* c2;
end