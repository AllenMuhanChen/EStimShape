function y = getVonMises(beta,x)
% beta = [mu kappa]; mu in degrees
    x = x*pi/180;
    beta(1) = beta(1)*pi/180;
    y = exp(beta(2) * cos(x-beta(1))) / (2*pi*besseli(0,beta(2)));
end