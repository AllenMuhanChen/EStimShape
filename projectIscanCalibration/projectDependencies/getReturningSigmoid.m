function y = getReturningSigmoid(beta,x)
    % beta = [bias maxVal midPt1 midPt2 slope];
    c=beta(1);
    s=beta(2);
    d1=beta(3);
    d2=beta(4);
    m1=beta(5);
    m2=beta(5);

    y = c + s./(1+exp(-(x-d1)*m1)) + s./(1+exp((x-d2)*m2)); 
end