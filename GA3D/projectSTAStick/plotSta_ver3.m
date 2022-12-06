function plotSta_ver3(runId,binSpec,sta,sta_shuff,stimStruct,resp,data,is3d)
    % [selectResp,selectIdx,selectStim,~,thumb] = getTopStim(resp,data,is3d);
    
    if length(sta) == 2
%         sta(1).s = sta(1).s/max(sta(1).s(:)); sta(2).s = sta(2).s/max(sta(2).s(:));
%         sta(1).r = sta(1).r/max(sta(1).r(:)); sta(2).r = sta(2).r/max(sta(2).r(:));
%         sta(1).t = sta(1).t/max(sta(1).t(:)); sta(2).t = sta(2).t/max(sta(2).t(:));
        
        staMult.s  = sta(1).s .* sta(2).s;
        staMult.r  = sta(1).r .* sta(2).r;
        staMult.t  = sta(1).t .* sta(2).t;
%         staMult.sr = sta(1).sr .* sta(2).sr;
%         staMult.st = sta(1).st .* sta(2).st;
        sta = staMult;
    end
    
    cols = colormap('lines'); cols = cols(1:6,:);
    colormap('parula'); close;
    
    
    % figure('pos',[2587,919,1030,269],'color','w');
    % clf; ha = tight_subplot(2,6); ha = reshape(ha,6,2)';
    % 
    % type = pickBestSta(sta);
    % 
    % switch type
    %     case 1; plotSubplot(sta.s,binSpec.s,ha,1,[],{stimStruct(selectIdx).s},cols);
    %     case 2; plotSubplot(sta.r,binSpec.r,ha,1,[],{stimStruct(selectIdx).r},cols);
    %     case 3; plotSubplot(sta.t,binSpec.t,ha,1,[],{stimStruct(selectIdx).t},cols);
    %     case 4; plotSubplot(sta.sr,binSpec.sr,ha,1,[],{stimStruct(selectIdx).sr},cols);
    %     case 5; plotSubplot(sta.st,binSpec.st,ha,1,[],{stimStruct(selectIdx).st},cols);
    % end
    % plotStimImages(thumb,selectResp,cols,ha,2);
    % 
    % savefig(['plots/icosta/icosta_' runId '_best' num2str(type) '_linMult.fig']);
    % % screen2png(['plots/icosta/icosta_' runId '_linMult.png']);
    
    
    hf = figure('pos',[2562,335,1030,853],'color','w');
    ha = tight_subplot(3,6); ha = reshape(ha,6,3)';
    
    binSpec.r.padding(7) = 'V';
    binSpec.r.padding(8) = 'V';
    
    selectIdx = 1:3;
%     plotStimImages(thumb,selectResp,cols,ha,6);
    
    plotSubplot(sta.s,binSpec.s,ha,1,[],{stimStruct(selectIdx).s},cols,0);
    plotSubplot(sta.r,binSpec.r,ha,2,[],{stimStruct(selectIdx).r},cols,0);
    plotSubplot(sta.t,binSpec.t,ha,3,[],{stimStruct(selectIdx).t},cols,0);

    
%     [~,staThresh] = filterAndThresholdSta(sta.t,0,1);
%     plotSubplot(staThresh,binSpec.t,ha,4,[],{stimStruct(selectIdx).t},cols,0);
    
%     [~,staThresh] = filterAndThresholdSta(sta.s,0,1);
%     plotSubplot(staThresh,binSpec.s,ha,5,[],{stimStruct(selectIdx).s},cols,0);
    % plotSubplot(sta.sr,binSpec.sr,ha,4,[],{stimStruct(selectIdx).sr},cols,0);
    % plotSubplot(sta.st,binSpec.st,ha,5,[],{stimStruct(selectIdx).st},cols,0);
    
    % savefig(['plots/icosta/icosta_' runId '_all_linMult.fig']);
    savefig(['~/Desktop/summaries/sta_' runId '.fig']);
    close(hf)
    
    if false
        for ii=1:3
            figure('color','k');
            plotSingleStim(gca,runId,selectStim(ii).genNum,selectStim(ii).linNum,selectStim(ii).stimNum)
        end
    end
    
    
    % figure('pos',[2562,335,1030,853],'color','w');
    % ha = tight_subplot(6,6); ha = reshape(ha,6,6)';
    % 
    % scaleS = max(sta(1).s(:).*sta(2).s(:));
    % scaleR = max(sta(1).r(:).*sta(2).r(:));
    % scaleT = max(sta(1).t(:).*sta(2).t(:));
    % scaleSR = max(sta(1).sr(:).*sta(2).sr(:));
    % scaleST = max(sta(1).st(:).*sta(2).st(:));
    % 
    % plotSubplot(sta_shuff(1).s.*sta_shuff(2).s,binCentersS,ha,1,8,scaleS);
    % plotSubplot(sta_shuff(1).r.*sta_shuff(2).r,binCentersR,ha,2,8,scaleR);
    % plotSubplot(sta_shuff(1).t.*sta_shuff(2).t,binCentersT,ha,3,6,scaleT);
    % plotSubplot(sta_shuff(1).sr.*sta_shuff(2).sr,binCentersSR,ha,4,6,scaleSR);
    % plotSubplot(sta_shuff(1).st.*sta_shuff(2).st,binCentersST,ha,5,6,scaleST);
    % plotStimImages(thumb,selectResp,cols,ha,6);
    % 
    % screen2png(['plots/dumb/dumb_' runId '_shuff.png']);
    
end

function plotSubplot(sta,binSpec,ha,rowNum,scale,stim,cols,doMean)
    binCenters = binSpec.binCenters;
    binCenters(cellfun(@isempty,binCenters)) = [];
    padding = binSpec.padding;
    padding(padding == 'i') = '';
    
    nCols = length(size(sta));
    stim = stim(1:3);
    staMax = max(sta(:));
    if ~exist('scale','var') || isempty(scale)
        if doMean
            scale = getScaleForMean(sta);
        else
            scale = staMax;
        end
    end
    
    if sum(isnan(sta(:))) > 0
        return
    end
    
    str = '[';
    for jj=1:nCols
        str = [str 'b' num2str(jj) ','];
    end
    str = [str(1:end-1) ']'];
    
    eval([str ' = ind2sub(size(sta),find(sta(:)==staMax));']);
    stimValIdx = {[1 2] 3 [4 5] 6 7 8};
    for ii=1:nCols
        h = ha(rowNum,ii); staForMean = sta;
        figure('color','w','Position',[-1647,59,1152,998]); h = gca; 
        str = '(';
        for jj=1:nCols
            if ii==jj
                str = [str ':,'];
            else
                str = [str 'b' num2str(jj) ','];
                staForMean = mean(staForMean,jj);
            end
        end
        str = [str(1:end-1) ');'];
        staForMean = squeeze(staForMean);

        if doMean
            ss = staForMean;
        else
            eval(['ss = sta' str]); ss = squeeze(ss);
        end
        if ~isvector(ss)
            error('something went wrong; there should be no matrices here');
            % plotSingleSphereView(h,...
            %     binCenters{ii},binCenters{ii+1},ss,[0 scale],...
            %     cellfun(@(x) x(stimValIdx{ii},:),stim,'UniformOutput',false),cols);
        elseif padding(ii) == 's' || padding(ii) == 'h' || padding(ii) == 'r'
            allStim = cellfun(@(x) x(stimValIdx{ii},:),stim,'UniformOutput',false);
            plotSingleIcosphereView(h,ss,[0 scale],allStim,cols,padding(ii))
        else
            plot(h,binCenters{ii},ss,'k','linewidth',2); 
            hold(h,'on');
            % for jj=1:3
            %     plot(h,stim{jj}(stimValIdx{ii},:),0.2*ones(length(stim{jj}(stimValIdx{ii},:)),1),'.','color',cols(jj,:),'MarkerSize',10)
            % end

            box(h,'off');
            set(h,'ylim',[0 scale],'linewidth',2);
        end
        % if padding(ii) == 'V' && padding(ii-1) == 'V'
        %     ss = squeeze(sta(b1,b2,b3,b4,:,:));
        %     plotVsView(ss)
        % end  
    end
end

function plotSingleIcosphereView(hAx,intensity,clim,allStim,stimCols,icoType)
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
    hp.EdgeColor = 'w'; hp.LineWidth = 2;
    hp.FaceAlpha = 1; hp.FaceColor = 'flat'; hp.FaceVertexCData = intensity/max(intensity);
    axis(hAx,'off','equal');
    
    % stimuli
    % for ii=1:length(allStim)
    %     stim = allStim{ii};
    %     stim = [stim' 1.2*ones(size(stim,2),1)];
    %     [x,y,z] = sph2cart(stim(:,1),stim(:,2),stim(:,3));
    %     hStim = plot3(hAx,x,y,z,'.','color',stimCols(ii,:),'MarkerSize',30);
    % end
    
    hPlot = [hPlot hp ]; % hStim
    
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

function plotVsView(intensity)
    intensity = intensity(:)/max(intensity(:));
    hf = figure('color','w','pos',[2733,-179,420,421]);
    ha = tight_subplot(4,4,0,0,0);
    for ii=1:16
        im = imread(['Vs/' num2str(ii) '.png']);
        im = addborderimage(im,60,255*[intensity(ii) 0 0],'out');
        imshow(im,'parent',ha(ii));
    end
    screen2png('plots/tempVsPlot.png');
end

function [selectResp,selectIdx,selectStim,cols,thumb] = getTopStim(resp,data,is3d)
    resp(~is3d,:) = nan;
    [sortedResp,idx] = sort(nanmean(resp,2),'descend');
    idx(isnan(sortedResp)) = [];
    sortedResp(isnan(sortedResp)) = [];
    selectResp = [sortedResp(1:3); sortedResp(end-2:end)]; selectIdx = [idx(1:3); idx(end-2:end)];
    cols = selectResp/selectResp(1);
    
    selectStim = data(selectIdx);
    
    imPath = {data.imgPath};
    imPath = imPath(selectIdx);
    thumb = cell(1,6);
    for stimNum=1:6
        im = imread(imPath{stimNum});
        im = imcrop(im,[150 150 300 300]);
        im = addborderimage(im,30,255*[cols(stimNum) 0 0],'out');
        thumb{stimNum} = im; 
    end
end

function plotStimImages(thumb,selectResp,cols,ha,rowNum)
    for ii=1:length(thumb)
        imshow(thumb{ii},'parent',ha(rowNum,ii)); hold(ha(rowNum,ii),'on');
        drawCircle(ha(rowNum,ii),70,290,20,cols(ii,:),1,0);
        text('position',[50 70],'fontsize',17,...
            'string',num2str(round(selectResp(ii),2)),'color','c','parent',ha(rowNum,ii));
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
    
    % text labels
    % hPlot = [hPlot text(1.4,0,0,'RGHT', 'FontSize', 12,'parent',hAx,'color','r')];
    % hPlot = [hPlot text(-1.6,0,0,'LFT', 'FontSize', 12,'parent',hAx,'color','r')];
    % 
    % hPlot = [hPlot text(-0.12,1.4,0,'TOP', 'FontSize', 12,'parent',hAx,'color','g')];
    % hPlot = [hPlot text(-0.12,-1.4,0,'BTM', 'FontSize', 12,'parent',hAx,'color','g')];
    % 
    % hPlot = [hPlot text(-0.17,0,1.4,'FRNT', 'FontSize', 12,'parent',hAx,'color','b')];
    % hPlot = [hPlot text(-0.17,0,-1.4,'BCK', 'FontSize', 12,'parent',hAx,'color','b')];

    
    
    % hEye = drawEye(2.5,2.8);
    % hPlot = [hPlot hEye];
end

function hEye = drawEye(p1,p2)
    r = p2-p1;
    c1 = [0 r p2];
    c2 = [0 -r p2];
    
    th = linspace(pi,3*pi/2,20);
    [z1,y1] = pol2cart(th,r);
    z1 = z1 + p2;
    y1 = y1 + r;
    
    th = linspace(pi/2,pi,20);
    [z2,y2] = pol2cart(th,r);
    z2 = z2 + p2;
    y2 = y2 - r;
    
    h1 = plot3(zeros(1,length(z1)),y1,z1,'b','LineWidth',3);
    h2 = plot3(zeros(1,length(z2)),y2,z2,'b','LineWidth',3);
    
    rp = r*sqrt(2);
    th = linspace(3*pi/4,5*pi/4,20);
    [z3,y3] = pol2cart(th,rp);
    z3 = z3 + p2;
    h3 = plot3(zeros(1,length(z3)),y3,z3,'b','LineWidth',3);
    
    x = pi/4; t = -0.1*rp/4;
    th = linspace(pi - x,pi + x,20);
    [z3,y3] = pol2cart(th,rp/2.5);
    z3 = z3 + p2 - 2.8*rp/4 - t;
    pp = [zeros(length(z3),1) y3' z3'];
    
    th = linspace(-x,x,20);
    [z3,y3] = pol2cart(th,rp/2.5);
    z3 = z3 + p2 - 5.1*rp/4 - t;
    pp = [pp;zeros(length(z3),1) y3' z3'];
    % h4 = patch(pp(:,1),pp(:,2),pp(:,3),'edgecolor','none','facecolor','k');
    h4 = plot3(pp(:,1),pp(:,2),pp(:,3),'b','LineWidth',3);
    
    axis equal
    hEye = [h1 h2 h3 h4];
end

function type = pickBestSta(sta)
    [~,type] = max([max(sta.s(:)) max(sta.r(:)) max(sta.t(:)) max(sta.sr(:)) max(sta.st(:))]);
end

function scale = getScaleForMean(sta)
    nCols = ndims(sta);
    scale = nan(1,nCols);
    for ii=1:nCols
        staForMean = sta;
        for jj=1:nCols
            if ii~=jj
                staForMean = mean(staForMean,jj);
            end
        end
        staForMean = squeeze(staForMean);
        scale(ii) = max(staForMean(:));
    end
    scale = max(scale);
end

% function plotSingleSphereView(hAx,th_centers,ph_centers,intensity,clim,allStim,stimCols)
%     if size(ph_centers,2) == 2
%         intensity = [intensity zeros(length(th_centers),length(ph_centers))];
%         ph_centers = [ph_centers -ph_centers];
%     end
% 
%     th = repmat(th_centers',length(ph_centers),1); th = th(:);
%     ph = repmat(ph_centers,length(th_centers),1); ph = ph(:);
%     intensity = intensity(:);
%     
%     hPlot = PlotSphereIntensity(hAx, th, ph, ones(size(th)), intensity); 
%     view(hAx,0,90); set(hAx,'clim',clim); hold(hAx,'on');
%     hp = patch([-1.3 -1.3 1.3 1.3],[0 0 0 0],[1.3 -1.3 -1.3 1.3],'r','parent',hAx);
%     hp.EdgeColor = 'none'; hp.FaceAlpha = 0.2;
%     axis(hAx,'off');
%     
%     for ii=1:length(allStim)
%         stim = allStim{ii};
%         stim = [stim' ones(size(stim,2),1)];
%         [x,y,z] = sph2cart(stim(:,1),stim(:,2),stim(:,3));
%         hStim = plot3(hAx,x,y,z,'.','color',stimCols(ii,:),'MarkerSize',30);
%     end
%     
%     hPlot = [hPlot hp hStim];
%     
%     t = hgtransform('Parent',hAx); 
%     for ii=1:length(hPlot)
%         set(hPlot(ii),'Parent',t);
%     end
%     
%     done = false;
%     while ~done
%         Txy = makehgtform('xrotate',0,'yrotate',0,'yrotate',0); 
%         set(t,'Matrix',Txy)
%         xx = input('x: '); yy = input('y: '); zz = input('z: ');
%         Txy = makehgtform('xrotate',xx*pi/16,'yrotate',yy*pi/16,'zrotate',zz*pi/16); 
%         set(t,'Matrix',Txy)
%         done = validatedInput('happy?: ',[0 1]);
%     end
%     
% end