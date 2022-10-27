function [beta,stats] = fitAny(x,y,h,estBeta) 
    options = statset('MaxIter',2000);
    
    warning('off','all')
    [beta,res] = nlinfit(x,y,h,estBeta,options);
    warning('on','all')
    
    nObs = length(y); 

    stats.resid = res'; 
    stats.aic = 2*2 + nObs*(log((sum(stats.resid.^2))/nObs));
end