function fitnessVector = selectParents_getFitness(resp)
    resp(resp < 0) = 0;

    % get r
    r       = sqrt(nansum(resp.^2,2)) / sqrt(size(resp,2)); % / sqrt(sum(max(resp).^2));

    % get a
    d       = getProximityAngDist(resp);
    a       = getPromotions(d);
    a       = a/max(a);

    % get k
    k       = (sum(resp,2).^2) ./ sum(resp.^2,2);
    k       = k .* (max(resp,[],2)/max(resp(:)));
    k       = k/max(k);
    
    % for stimuli that weren't shown at all
    k(isnan(k)) = 0;

    fitnessVector.r   = r;
    fitnessVector.a   = a;
    fitnessVector.k   = k;
end

function a = getProximityAngDist(resp)
    nStim = size(resp,1);
    a     = zeros(nStim);

    for ii=1:nStim
        v1 = resp(ii,:);
        di = zeros(nStim,1);
        for jj=ii+1:nStim
            v2      = resp(jj,:);
            di(jj)  = 2 * real(acos(dot(v1,v2)/(norm(v1) * norm(v2))) / pi);
        end
        a(ii,:)   = di;
    end

    a   = a   + triu(a)';
    a(isnan(a)) = 0;
end

function promotions = getPromotions(diversityMat)
    promotions = (mean(diversityMat,2));
%     promotions = promotions/max(promotions);
    promotions(isnan(promotions)) = 0;
end
