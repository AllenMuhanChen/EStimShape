function [beta,LM,pred] = multiPrediction(predStick,predSurf,resp,is3d)
    % beta = s,r,t,surf
    pred_s = cellfun(@max,predStick.s);
    pred_r = cellfun(@max,predStick.r);
    pred_t = cellfun(@max,predStick.t);
    pred_surf = cellfun(@max,predSurf.mult);
    
    pred = [pred_s pred_r pred_t];
    
    resp = nanmean(resp,2);
    resp = resp ./ max(resp);
    resp(~is3d) = [];
    
    beta = regress(resp,pred);
    LM = fitlm(resp,getLinComb(beta',pred));
    
    pred = [pred pred_surf];
end

function y = getLinComb(beta,x)
    y = sum(repmat(beta,size(x,1),1) .* x,2);
end