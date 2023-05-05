function plotSta(sta,binSpec)
    for ii=1:length(sta)
        if ii == 1
            staMult = sta(ii);
        else
            staMult.s = staMult.s .* sta(ii).s;
            staMult.r = staMult.r .* sta(ii).r;
            staMult.t = staMult.t .* sta(ii).t;
        end
    end
        
    figure('pos',[1330,615,1030,442],'color','w');
    ha = tight_subplot(3,6,[0.06 0.02]); ha = reshape(ha,6,3)';
    plotSubplot(staMult.s,binSpec.s,ha,1);
    plotSubplot(staMult.r,binSpec.r,ha,2);
    plotSubplot(staMult.t,binSpec.t,ha,3);
end

function plotSubplot(sta,binSpec,ha,rowNum)
    binCenters = binSpec.binCenters;
    binCenters(cellfun(@isempty,binCenters)) = [];
    padding = binSpec.padding;
    padding(padding == 'i') = '';
    
    nCols = length(size(sta));
    scale = max(sta(:)); 
    
    str = '[';
    for jj=1:nCols
        str = [str 'b' num2str(jj) ','];
    end
    str = [str(1:end-1) ']'];
    eval([str ' = ind2sub(size(sta),find(sta(:)==scale));']);
    for ii=1:nCols
        h = ha(rowNum,ii); 
        str = '(';
        for jj=1:nCols
            if ii==jj
                str = [str ':,'];
            else
                str = [str 'b' num2str(jj) ','];
            end
        end
        str = [str(1:end-1) ');'];
        eval(['ss = sta' str]); ss = squeeze(ss);
        
        if ~isvector(ss)
            error('something went wrong; there should be no matrices here');
        elseif padding(ii) == 's' || padding(ii) == 'h' || padding(ii) == 'r'
            plotSingleIcosphereView(h,ss,[0 scale],padding(ii))
        else
            plot(h,binCenters{ii},ss,'k','linewidth',1); 
            hold(h,'on');
            
            box(h,'off');
            set(h,'ylim',[0 scale],'linewidth',1);
        end
    end
end

function plotSingleIcosphereView(hAx,intensity,clim,icoType)
    if icoType == 's'
        [verts,faces] = getIcosphereDeets(1,0,0);
    elseif icoType == 'r'
        [verts,faces] = getIcosphereDeets(0,1,0);
    else
        [verts,faces] = getIcosphereDeets(0,0,0);
    end

    hold(hAx,'on');
    axis(hAx,'off','equal');
    set(hAx,'clim',clim);
    
    % axes
    plotAxes(hAx);
    
    % isosphere
    hp = patch('Vertices',verts,'faces',faces,'parent',hAx);
    hp.EdgeColor = 'w'; hp.LineWidth = 1;
    hp.FaceAlpha = 1; hp.FaceColor = 'flat'; hp.FaceVertexCData = intensity/max(intensity);
    axis(hAx,'off','equal');
end

function hPlot = plotAxes(hAx)
    view(hAx,0,90);  hold(hAx,'on');
    
    xAxis = [-2.1 0 0; 2.1 0 0];
    yAxis = [0 -1.3 0; 0 1.3 0];
    zAxis = [0 0 -2.1; 0 0 2.1];
    
    % axis lines
    hPlot(1) = plot3(hAx,xAxis(:,1), xAxis(:,2), xAxis(:,3), 'r', 'LineWidth', 2);
    hPlot(2) = plot3(hAx,yAxis(:,1), yAxis(:,2), yAxis(:,3), 'g', 'LineWidth', 2);
    hPlot(3) = plot3(hAx,zAxis(:,1), zAxis(:,2), zAxis(:,3), 'b', 'LineWidth', 2);

    % top arrow
    hPlot(4) = plot3(hAx,[0 0.0684],[1.3 1.3-0.1879],[0 0], 'g', 'LineWidth', 2);
    hPlot(5) = plot3(hAx,[0 -0.0684],[1.3 1.3-0.1879],[0 0], 'g', 'LineWidth', 2);
    
    % front arrow
    hPlot(6) = plot3(hAx,[0 0],[0 0.0684],[2.1 2.1-0.1879], 'b', 'LineWidth', 2);
    hPlot(7) = plot3(hAx,[0 0],[0 -0.0684],[2.1 2.1-0.1879], 'b', 'LineWidth', 2);
    
    % bottom fletching
    fletchingOffsets = [0.05 0.15 0.25];
    for ii=1:length(fletchingOffsets)
        hPlot = [hPlot plot3(hAx,[0 0.0684],fletchingOffsets(ii)+[-1.3 -1.3-0.1879],[0 0], 'g', 'LineWidth', 2)];
        hPlot = [hPlot plot3(hAx,[0 -0.0684],fletchingOffsets(ii)+[-1.3 -1.3-0.1879],[0 0], 'g', 'LineWidth', 2)];
    end
    
    % back fletching
    for ii=1:length(fletchingOffsets)
        hPlot = [hPlot plot3(hAx,[0 0],[0 0.0684],fletchingOffsets(ii)+[-2.1 -2.1-0.1879], 'b', 'LineWidth', 2)];
        hPlot = [hPlot plot3(hAx,[0 0],[0 -0.0684],fletchingOffsets(ii)+[-2.1 -2.1-0.1879], 'b', 'LineWidth', 2)];
    end
    
    % plane
    hpl = patch(1.5*[-1.3 -1.3 1.3 1.3],[0 0 0 0],1.5*[1.3 -1.3 -1.3 1.3],'k',...
        'parent',hAx);
    hpl.EdgeColor = 'none'; hpl.FaceAlpha = 0.5;
    hPlot = [hPlot hpl];
end