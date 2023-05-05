function isValid = checkPolygon(cPts)
    if sum(isnan(cPts(:))) > 0
        isValid = 0;
        return;
    end

    cPts = round((cPts.*10000))/10000;
    inters = polygonSelfIntersections(cPts);
    isValid = isempty(inters);
    
    % contingency for sharpness morphs
    if ~isValid
        found = 0;
        inters = round((inters.*10000))/10000;
        for i=1:size(inters,1)
            [x,~]=find(cPts == inters(i,1));
            [y,~]=find(cPts == inters(i,2));
            
            if length(x) < 2 || isempty(x) || isempty(y) || ~isequal(x,y)
                found = 1;
                break;
            end
        end
        isValid = ~found;
    end
    
end