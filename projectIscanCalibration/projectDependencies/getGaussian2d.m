function z = getGaussian2d(beta,x,y)
% beta = [a mu_x sig_x mu_y sig_y]
    a = beta(1);
    mu1 = beta(2);
    sig1 = beta(3);
    mu2 = beta(4);
    sig2 = beta(5);
    
    z = 1/(2*pi*sig1*sig2);
    
    c1 = ((x-mu1).^2)/(2*sig1^2);
    c2 = ((y-mu2).^2)/(2*sig2^2);
    
    z = a * z .* exp(-(c1 + c2));

end