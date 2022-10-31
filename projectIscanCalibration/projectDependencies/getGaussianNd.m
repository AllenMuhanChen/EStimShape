function y = getGaussianNd(beta,x0)
    % beta = [a s1 s2 s3 s4 s5 ... m1 m2 m3 m4 m5 ...]
    % x0 = [x1 x2 x3 x4 x5 ...]
    
    n = size(x0,2);
    
    a = beta(1);
    s = beta(2:1+n);
    m = beta(2+n:end);

    c = zeros(size(x0,1),n);
    for ii=1:n
        c(:,ii) = ((x0(:,ii)-m(ii)).^2)/(2*s(ii)^2);
    end
    
    b = 1/(2*pi*prod(s));
    
    y = a * b .* exp(-(sum(c,2)));
end