function y = getSigmoid(beta,x)
    % beta = [bias maxVal midPt slope];
    c=beta(1);
    s=beta(2);
    d=beta(3);
    m=beta(4);

    y = c + s./(1+exp(-(x-d)*m)); 
end