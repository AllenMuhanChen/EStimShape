function y = getDoubleVonMises(beta,x)
% beta = [mu1 kappa1 mu2 kappa2]; mu in degrees
    x = x*pi/180;
    beta(1) = beta(1)*pi/180;
    beta(3) = beta(3)*pi/180;
    y = exp(beta(2) * cos(x-beta(1))) / (2*pi*besseli(0,beta(2))) + ...
        exp(beta(4) * cos(x-beta(3))) / (2*pi*besseli(0,beta(4)));
end