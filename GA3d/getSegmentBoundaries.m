function [boundaryCoordinates,boundaryPtIndices,segmentGroupIndices,...
        maskCandidateIndices,maskCandidateCenters,maskCandidateSizes] ...
    = getSegmentBoundaries(dPts)

    x    = dPts(:,1);           y   = dPts(:,2);
    dx   = gradient(x);         dy  = gradient(y);
    ddx  = gradient(dx);        ddy = gradient(dy);

    k = (dx.*ddy - ddx.*dy)./(sqrt((dx.^2 + dy.^2).^3));
    squashK = (2./(1+exp(-0.125*k))) - 1;

    [ymax,imax,ymin,imin] = extrema(squashK);
    yextrm = [ymax;ymin]; xextrm = [imax;imin];

   
    absThreshold = [];
    for i = 1:17
        if sum(abs(yextrm) >= 0.05*(20-i)) > 6
            absThreshold = 0.05*(20-i); break;
        end
    end
    
    if ~isempty(absThreshold)
        boundaryPtIndices = xextrm(abs(yextrm) > absThreshold);
    else
        [~,ind] = sort(abs(yextrm),'descend');
        boundaryPtIndices = xextrm(ind(1:6));
    end
    boundaryPtIndices = sort(boundaryPtIndices);
    boundaryCoordinates = [dPts(boundaryPtIndices,1),dPts(boundaryPtIndices,2)];
    
    segmentGroupIndices = cell(1,length(boundaryPtIndices));
    boundaryPtIndicesEnd = circshift(boundaryPtIndices,-1);
    
    for i=1:length(boundaryPtIndices)
        if boundaryPtIndices(i) < boundaryPtIndicesEnd(i)
            segmentGroupIndices{i} = boundaryPtIndices(i)+1:boundaryPtIndicesEnd(i);
        else
            segmentGroupIndices{i} = [boundaryPtIndices(i)+1:size(dPts,1) 1:boundaryPtIndicesEnd(i)];
        end
    end
    
    count = 1;
    while count <= length(boundaryPtIndices)
        currSeg = [];
        segmentsGrouped = 1;
        tempCenters = [];
        while length(currSeg) < 5 || segmentsGrouped <= 2
            if count+segmentsGrouped-1 <= length(boundaryPtIndices)
                currSeg = [currSeg segmentGroupIndices{count+segmentsGrouped-1}]; %#ok<AGROW>
                tempCenters = [tempCenters currSeg(end)];
            else
                currSeg = [currSeg segmentGroupIndices{1}]; %#ok<AGROW>
            end
            
            segmentsGrouped = segmentsGrouped + 1; 
        end
        if length(currSeg) < 20
            count = count + 1; continue;
        end
        maskCandidateIndices{count} = currSeg; %#ok<AGROW>
        tempMaskCandidateCenters(count) = tempCenters(1);
        count = count + 1;
    end
%     maskCandidateCenters = circshift(boundaryPtIndices,-1);
%     maskCandidateSizes = zeros(1,length(maskCandidateIndices));
    
    count = 0;
    for i=1:length(maskCandidateIndices)
        if isempty(maskCandidateIndices{i})
            continue;
        end
        [xx,yy] = boundingBox(dPts(maskCandidateIndices{i},:));
        currCenter = [dPts(tempMaskCandidateCenters(i),1) dPts(tempMaskCandidateCenters(i),2)];
%         tempDist = [sqrt((currCenter(1) - xx(1))^2 + (currCenter(2) - yy(1))^2)...
%                     sqrt((currCenter(1) - xx(1))^2 + (currCenter(2) - yy(2))^2)...
%                     sqrt((currCenter(1) - xx(2))^2 + (currCenter(2) - yy(1))^2)...
%                     sqrt((currCenter(1) - xx(2))^2 + (currCenter(2) - yy(2))^2)];
%         maskCandidateSizes(i) = min(tempDist);
        r = sqrt(diff(xx)^2 + diff(yy)^2)/3;
        ind = find(sqrt((currCenter(1) - dPts(:,1)).^2 + (currCenter(2) - dPts(:,2)).^2) < r);
        if ~ismember(ind,maskCandidateIndices{i})
            r = sqrt(diff(xx)^2 + diff(yy)^2)/4;
        end
        count = count + 1;
        maskCandidateCenters(count,:) = dPts(tempMaskCandidateCenters(i),:); %#ok<AGROW>
        maskCandidateSizes(count) = r;
    end
end

function [xx,yy] = boundingBox(xy)
    xx = [min(xy(:,1)) max(xy(:,1))];
    yy = [min(xy(:,2)) max(xy(:,2))];
end