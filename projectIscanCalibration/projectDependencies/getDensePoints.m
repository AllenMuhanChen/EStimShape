function densePts = getDensePoints(cPts,idx,sampling,closeCurve)
    if ~exist('sampling','var'); sampling = 100; end
    if ~exist('closeCurve','var'); closeCurve = 1; end
    

    deg = 3; order = deg + 1;
    n = size(cPts,1); 
    if closeCurve
        overlapCPts = [cPts; cPts(1:deg,:)];
    else
        overlapCPts = cPts;
        n = n-deg;
    end
    knotVec = linspace(0,1,n+deg+order);
    sp = spmak(knotVec,overlapCPts');
    
    % if the index is specified, then only calculate the spline for that
    % index. But if it is not, or it is empty, then calculate it for the
    % whole shape
    if ~exist('idx','var')
        x = linspace(knotVec(order),knotVec(n+order),sampling);
    elseif isempty(idx)
        x = linspace(knotVec(order),knotVec(n+order),sampling);
    elseif idx == 1
        x = knotVec(n + deg);
    else
        x = knotVec(idx + deg - 1);
    end
    densePts = fnval(sp,x)';
end