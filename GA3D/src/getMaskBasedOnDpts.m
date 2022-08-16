function mask = getMaskBasedOnDpts(dPts,isActive)
    mask(1).isActive = isActive(1);
    mask(2).isActive = isActive(2);

    mask(1).z = 0;
    mask(2).z = 0;

    [~,~,~,~,maskCandidateCenters,maskCandidateSizes] = getSegmentBoundaries(dPts);
    
    nMasks = length(maskCandidateCenters);
    areaOfShape = polygeom(dPts(:,1),dPts(:,2));
    areaOfShape = areaOfShape(1);
    
    tryNum = 1;
    validMaskPair = false;
    while ~validMaskPair > 0 && tryNum < 50
        
        maskIdx(1) = randi(nMasks);
        masksRem = 1:nMasks; masksRem(masksRem == maskIdx(1)) = [];
        maskIdx(2) = datasample(masksRem,1);
        
        mask(1).x = maskCandidateCenters(maskIdx(1),1);
        mask(1).y = maskCandidateCenters(maskIdx(1),2);
        mask(1).s = maskCandidateSizes(maskIdx(1));
        
        mask(2).x = maskCandidateCenters(maskIdx(2),1);
        mask(2).y = maskCandidateCenters(maskIdx(2),2);
        mask(2).s = maskCandidateSizes(maskIdx(2));
        
        percentOverlap = getMaskOverlapPercent(mask);
        
        factor = 1;
        while percentOverlap > 0 && factor > 0.5
            factor = factor - 0.1;
            mask(1).s = mask(1).s * factor;
            mask(2).s = mask(2).s * factor;
            percentOverlap = getMaskOverlapPercent(mask);
        end
        
        areaOfMask(1) = pi * mask(1).s^2;
        areaOfMask(2) = pi * mask(2).s^2;
        validMaskPair = (areaOfMask(1)/areaOfShape > 0.3 && ...
            areaOfMask(2)/areaOfShape > 0.3);
        
        tryNum = tryNum + 1;
    end
    
    if ~validMaskPair
        distFromAllPts = sqrt(sum((dPts - repmat([mask(1).x mask(1).y],size(dPts,1),1)).^2,2));
        [~,farPointIdx] = max(distFromAllPts);
        mask(2).x = dPts(farPointIdx,1);
        mask(2).y = dPts(farPointIdx,2);
        mask(2).s = maskCandidateSizes(maskIdx(1));
        mask(1).s = maskCandidateSizes(maskIdx(1));
        
        percentOverlap = getMaskOverlapPercent(mask);
        
        factor = 1;
        while percentOverlap > 0 && factor > 0.5
            factor = factor - 0.1;
            mask(1).s = mask(1).s * factor;
            mask(2).s = mask(2).s * factor;
            percentOverlap = getMaskOverlapPercent(mask);
        end
    end
    
    if percentOverlap > 0
        mask = [];
    end
end