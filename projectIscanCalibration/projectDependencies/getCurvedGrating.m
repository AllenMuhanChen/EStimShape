% Example:
% x = [-6*pi 6*pi];
% y = [-20 20];
% evalFunc.x = 'x.^2/20';
% evalFunc.y = 'y.^2/20';
% evalFunc.offset = pi;
% f = getCurvedGrating(x,y,200,evalFunc);
% imagesc(f)
% colormap gray; axis off; grid off;

function f = getCurvedGrating(x,y,nDots,evalFunc)
    % x and y are limits of your gratings; eg x = [-6*pi 6*pi]
    % nDots is the resolution of the grating
    X = linspace(x(1),x(2),nDots);
    Y = linspace(y(1),y(2),nDots);
    [x,y] = meshgrid(X,Y); %#ok<ASGLU>
    
    evalFuncStr = ['fx = ' evalFunc.x '; fy = ' evalFunc.y ';'];
    eval(evalFuncStr);
    
    f = sin(fx + fy + evalFunc.offset);
end