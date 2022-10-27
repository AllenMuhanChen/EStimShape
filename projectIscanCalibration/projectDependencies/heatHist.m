function n = heatHist(data,edges)
    if exist('edges','var')
        hist3(data,'edges',edges); hold on;
        n = hist3(data,'edges',edges);
    else
        hist3(data); hold on;
        n = hist3(data,[30,30]); % default is to 10x10 bins
    end
       
% %     colormap below
%     n1 = n';
%     n1(size(n,1) + 1, size(n,2) + 1) = 0;
% 
%     xb = linspace(min(data(:,1)),max(data(:,1)),size(n,1)+1);
%     yb = linspace(min(data(:,2)),max(data(:,2)),size(n,1)+1);
% 
%     h = pcolor(xb,yb,n1);
%     set(h, 'zdata', ones(size(n1)) * -max(max(n)))
%     colormap(hot) % heat map
%     grid on
%     view(3);
    
% %     linear fit to hist3
%     a = repmat((1:30)',30,1); 
%     b = reshape(repmat(1:30,30,1),900,1);
%     
%     sf = fit([a,b],n(:),'poly23');
%     plot(sf,[a,b],n(:))
end