function [staFilt,staThresh] = filterAndThresholdSta(sta,doFilt,doThresh)
    if doFilt
        staFilt = filterSta(sta);
        staFilt = max(sta(:)) * staFilt / max(staFilt(:));
    else
        staFilt = sta;
    end
    
    if doThresh
        staThresh = thresholdSta(staFilt);
    else
        staThresh = staFilt;
    end
end

function sta = thresholdSta(sta)
    minSta = min(sta(:));
    maxSta = max(sta(:));
    midSta = 2*(maxSta - minSta)/3;
    slopeSta = 20; % determined by eye
    
    % x = linspace(minSta,maxSta,50);
    % plot(x,getSigmoid([minSta maxSta midSta slopeSta],x))
    
    sta = getSigmoid([minSta maxSta midSta slopeSta],sta);
end

function sta = filterSta(sta)   
    % coeffs(1) = center; centers(2) = neighbour;
    % coeffs = getGaussian([1 0 1],[0 1]);
    coeffs = [1,0.606530659712633];
    
    centralBins = coeffs(1) * sta;
    surroundBins = zeros(size(sta));
    deno = zeros(size(sta));
    
    loadedFileId = 0;
    for binId=1:numel(sta)
        if ~mod(binId,3840)
            fileId = binId/3840 - 1;
            fprintf('.');
        else
            fileId = binId/3840;
        end
        fileId = 1 + floor(fileId);
        
        if loadedFileId ~= fileId
            loadedFile = load(['dep/staNeigh/' num2str(fileId) '.mat']);
            staNeighMat = loadedFile.staNeighMat;
            loadedFileId = fileId;
        end

        binNumForNeigh = mod(binId,3840); binNumForNeigh(binNumForNeigh == 0) = 3840;
        surroundBins(binId) = (coeffs(2) * sum(sta(staNeighMat{binNumForNeigh})));
        
        nNeigh = length(staNeighMat{binNumForNeigh});
        deno(binId) = coeffs(1) + coeffs(2)*nNeigh;
        
    end
    fprintf('\n');
    sta = (centralBins + surroundBins)./deno;
end

function y = getSigmoid(beta,x)
    % beta = [bias maxVal midPt slope];
    c=beta(1);
    s=beta(2);
    d=beta(3);
    m=beta(4);

    y = c + s./(1+exp(-(x-d)*m)); 
end