clc; close all; clear;
load('data/ids.mat');
load('data/corrScores_dcn.mat','corrScores')

staPop_3d = []; count_3d = 0;
staPop_2d = []; count_2d = 0;

for ii=1:169
    ii
    if ~isempty(corrScores(ii).neu_s)
        runId = [num2str(population(ii).prefix) '_r-' num2str(population(ii).runNum)];
        staFile = ['data/neural/' runId '_sta.mat'];
        load(staFile);
        % fitFile = ['data/' runId '_fit.mat'];
        % load(fitFile);
        if length(sta) == 2
            staMult.s  = sta(1).s .* sta(2).s;
            staMult.r  = sta(1).r .* sta(2).r;
            staMult.t  = sta(1).t .* sta(2).t;
            sta = staMult;
        end
        
        sta.s = sta.s./max(sta.s(:));
        sta.r = sta.r./max(sta.r(:));
        sta.t = sta.t./max(sta.t(:));
        
        % [~,~,b3,~,~,~] = ind2sub(size(sta.s),find(sta.s(:)==scale));
        
        if population(ii).score_3d > 0
            if isempty(staPop_3d)
                staPop_3d = sta;
            else
                staPop_3d.s = staPop_3d.s + sta.s;
                staPop_3d.r = staPop_3d.r + sta.r;
                staPop_3d.t = staPop_3d.t + sta.t;
            end
            count_3d = count_3d + 1;
        else
            if isempty(staPop_2d)
                staPop_2d = sta;
            else
                staPop_2d.s = staPop_2d.s + sta.s;
                staPop_2d.r = staPop_2d.r + sta.r;
                staPop_2d.t = staPop_2d.t + sta.t;
            end
            count_2d = count_2d + 1;
        end
    end
end

staPop_3d.s = staPop_3d.s./count_3d;
staPop_3d.r = staPop_3d.r./count_3d;
staPop_3d.t = staPop_3d.t./count_3d;

staPop_2d.s = staPop_2d.s./count_2d;
staPop_2d.r = staPop_2d.r./count_2d;
staPop_2d.t = staPop_2d.t./count_2d;

%%
figure('pos',[-1545,396,1232,624],'color','w','name','3d units');
clf; ha = tight_subplot(3,6,[0.05 0.03],0.01,0.01); ha = reshape(ha,6,3)';
plotSubplot(staPop_3d.s,binSpec.s,ha,1);
plotSubplot(staPop_3d.r,binSpec.r,ha,2);
plotSubplot(staPop_3d.t,binSpec.t,ha,3);

figure('pos',[-1545,396,1232,624],'color','w','name','2d units');
clf; ha = tight_subplot(3,6,[0.05 0.03],0.01,0.01); ha = reshape(ha,6,3)';
plotSubplot(staPop_2d.s,binSpec.s,ha,1);
plotSubplot(staPop_2d.r,binSpec.r,ha,2);
plotSubplot(staPop_2d.t,binSpec.t,ha,3);

%%
function plotSubplot(sta,binSpec,ha,rowNum)
    binCenters = binSpec.binCenters;
    binCenters(cellfun(@isempty,binCenters)) = [];
    padding = binSpec.padding;
    padding(padding == 'i') = '';
    
    nCols = length(size(sta));
    scale = max(sta(:));
    
    if sum(isnan(sta(:))) > 0
        return
    end
    
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
                % sta = mean(sta,jj);
            end
        end
        str = [str(1:end-1) ');'];
        eval(['ss = sta' str]); ss = squeeze(ss);
        
        if ~isvector(ss)
            error('something went wrong; there should be no matrices here');
        elseif padding(ii) == 's' || padding(ii) == 'h' || padding(ii) == 'r'
            ss = (ss-min(ss))./(max(ss)-min(ss));
            plotSingleIcosphereView(h,ss,[min(ss) max(ss)],padding(ii))
        else
            plot(h,binCenters{ii},ss,'k','linewidth',2); 
            hold(h,'on');
            box(h,'off');
            set(h,'ylim',[min(ss) max(ss)],'linewidth',2);
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

    axis(hAx,'off','equal');
    set(hAx,'clim',clim);
    
    % axes
    hPlot = plotAxes(hAx);
    
    % isosphere
    hp = patch('Vertices',verts,'faces',faces,'parent',hAx);
    hp.EdgeColor = 'w';
    hp.LineWidth = 2;
    hp.FaceAlpha = 1; 
    hp.FaceColor = 'flat'; 
    hp.FaceVertexCData = intensity/max(intensity);
    axis(hAx,'off','equal');

    hPlot = [hPlot hp];
    
    t = hgtransform('Parent',hAx); 
    for ii=1:length(hPlot)
        set(hPlot(ii),'Parent',t);
    end
    
    done = true;
    while ~done
        Txy = makehgtform('xrotate',0,'yrotate',0,'zrotate',0); 
        set(t,'Matrix',Txy)
        xx = input('x: '); yy = input('y: '); zz = input('z: ');
        Txy = makehgtform('xrotate',xx*pi/16,'yrotate',yy*pi/16,'zrotate',zz*pi/16); 
        set(t,'Matrix',Txy)
        done = validatedInput('happy?: ',[0 1]);
    end
end

function hPlot = plotAxes(hAx)
    view(hAx,0,90);  hold(hAx,'on');
    
    xAxis = [-2.1 0 0; 2.1 0 0];
    yAxis = [0 -1.3 0; 0 1.3 0];
    zAxis = [0 0 -2.1; 0 0 2.1];
    
    % axis lines
    hPlot(1) = plot3(hAx,xAxis(:,1), xAxis(:,2), xAxis(:,3), 'r', 'LineWidth', 5);
    hPlot(2) = plot3(hAx,yAxis(:,1), yAxis(:,2), yAxis(:,3), 'g', 'LineWidth', 5);
    hPlot(3) = plot3(hAx,zAxis(:,1), zAxis(:,2), zAxis(:,3), 'b', 'LineWidth', 5);

    % top arrow
    hPlot(4) = plot3(hAx,[0 0.0684],[1.3 1.3-0.1879],[0 0], 'g', 'LineWidth', 5);
    hPlot(5) = plot3(hAx,[0 -0.0684],[1.3 1.3-0.1879],[0 0], 'g', 'LineWidth', 5);
    
    % front arrow
    hPlot(6) = plot3(hAx,[0 0],[0 0.0684],[2.1 2.1-0.1879], 'b', 'LineWidth', 5);
    hPlot(7) = plot3(hAx,[0 0],[0 -0.0684],[2.1 2.1-0.1879], 'b', 'LineWidth', 5);
    
    % bottom fletching
    fletchingOffsets = [0.05 0.15 0.25];
    for ii=1:length(fletchingOffsets)
        hPlot = [hPlot plot3(hAx,[0 0.0684],fletchingOffsets(ii)+[-1.3 -1.3-0.1879],[0 0], 'g', 'LineWidth', 5)];
        hPlot = [hPlot plot3(hAx,[0 -0.0684],fletchingOffsets(ii)+[-1.3 -1.3-0.1879],[0 0], 'g', 'LineWidth', 5)];
    end
    
    % back fletching
    for ii=1:length(fletchingOffsets)
        hPlot = [hPlot plot3(hAx,[0 0],[0 0.0684],fletchingOffsets(ii)+[-2.1 -2.1-0.1879], 'b', 'LineWidth', 5)];
        hPlot = [hPlot plot3(hAx,[0 0],[0 -0.0684],fletchingOffsets(ii)+[-2.1 -2.1-0.1879], 'b', 'LineWidth', 5)];
    end
    
    % plane
    hpl = patch(1.5*[-1.3 -1.3 1.3 1.3],[0 0 0 0],1.5*[1.3 -1.3 -1.3 1.3],'k',...
        'parent',hAx);
    hpl.EdgeColor = 'none'; hpl.FaceAlpha = 0.5;
    hPlot = [hPlot hpl];
end
