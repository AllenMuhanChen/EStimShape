function y = getLinComb(beta,x)
    y = sum(repmat(beta,size(x,1),1) .* x,2);
end