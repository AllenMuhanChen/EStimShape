function img = getGabor(beta,x)
    % res: resolution: odd only
    % beta:
    % grating params
        % 1: ori in deg
        % 2: freq in cyl/pix
        % 3: phase
    % gaussian params
        % 4: amp
        % 5: std in pix
       
    img = getGabor_fn(beta,x);
    img = img(:);

    % heuristic way: bad way    
    % resmax = 3*res;
    % xx = linspace(0,2*pi*(resmax*beta(2)),resmax);
    % yy = sin(beta(3)+xx);
    % grat = repmat(yy,resmax,1); 
    % grat = imrotate(grat,beta(1)); 
    % grat = grat((res+1):2*res, (res+1):2*res);
    % grat = (grat + 1)./2; % grating
    % 
    % mid = (res+1)/2;
    % 
    % aa = 2*pi*beta(4)*beta(5)*beta(5);
    % [xx,yy] = meshgrid(1:res,1:res);
    % gaus = getGaussian2d([aa,mid,beta(5),mid,beta(5)],xx,yy); % gaussian
    % 
    % img = grat.*gaus;
end

function gb = getGabor_fn(beta,x)
    theta = beta(1);
    lambda = beta(2);
    psi = beta(3);
    sigma = beta(4);
    alpha = beta(5);

    gamma = 1;
    sigma_x = sigma;
    sigma_y = sigma/gamma;

    siz = sqrt(size(x,1));
    xx = reshape(x(:,1),siz,siz);
    yy = reshape(x(:,2),siz,siz);

    % Rotation 
    x_theta=xx*cos(theta)+yy*sin(theta);
    y_theta=-xx*sin(theta)+yy*cos(theta);

    gb= alpha.*exp(-.5*(x_theta.^2/sigma_x^2+y_theta.^2/sigma_y^2)).*cos(2*pi/lambda*x_theta+psi);
end