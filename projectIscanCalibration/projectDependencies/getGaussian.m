function y = getGaussian(beta,x)
% beta = [a mu sig]
    y = beta(1) * exp(-((x-beta(2)).^2) / (2*beta(3)^2));
end