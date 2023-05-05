function y = getSaturatingGaussian(beta,x)
% beta = [a mu sig expt]
    y = beta(1) * exp(-((x-beta(2)).^2) / (2*beta(3)^2));
    y = y .* (1-exp(-beta(4)*x));
end