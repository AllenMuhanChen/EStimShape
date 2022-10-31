function [densePts,hPatch] = drawSpline(cPts,varargin)
    % varargin = sampleDensity + h + drawCpts + fColor,bColor
    densePts = [];
    
    if length(varargin) == 1
        sampleDensity = varargin{1};
        plotSpline = 0;
    elseif length(varargin) == 2
        sampleDensity = varargin{1}; h = varargin{2};
        plotSpline = 1; fColor = [0.7 0.7 0.7]; bColor = [0.5 0.5 0.5]; drawCpts = 0; 
    elseif length(varargin) == 3
        sampleDensity = varargin{1}; h = varargin{2}; drawCpts = varargin{3};
        plotSpline = 1; fColor = [0.7 0.7 0.7]; bColor = [0.5 0.5 0.5];
    elseif length(varargin) == 5
        sampleDensity = varargin{1}; h = varargin{2}; drawCpts = varargin{3}; fColor = varargin{4}; bColor = varargin{5};
        plotSpline = 1; 
    elseif isempty(varargin)
        plotSpline = 0; sampleDensity = 200;
    else
       disp('Invalid number of arguments.'); 
       return;
    end
    
    deg = 3; order = deg + 1;
    n = size(cPts,1); 
    overlapCPts = [cPts; cPts(1:deg,:)];
    knotVec = linspace(0,1,n+deg+order);
    sp = spmak(knotVec,overlapCPts');
    x = linspace(knotVec(4),knotVec(n+deg+1),sampleDensity);
    densePts = fnval(sp,x)';
    
    if plotSpline
        axes(h); set(h,'color',bColor);
        hPatch = patch(densePts(:,1),densePts(:,2),fColor,'EdgeColor','None'); hold on;
%         axis(h,'image'); 
        set(h,'xtick',[],'ytick',[]); box(h,'on');

        if drawCpts
            color = [0.3 0.3 0.3];
            patch(cPts(:,1),cPts(:,2),color,'facecolor','none','edgecolor',color,'markerfacecolor',color,'marker','o','linestyle','--');
        end
    end
end