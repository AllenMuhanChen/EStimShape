function y = getWrappedGauss(beta,x)
% beta = [mu sigma]
    x = x*pi/180;
    beta = beta*pi/180;
    jac = jacobiThetaEta(x-beta(1)/(2*pi),1i*beta(2)^2/(2*pi));
    y = jac/(2*pi);
end