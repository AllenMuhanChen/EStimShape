function plotSta_ver2(runId,binSpec,sta,sta_shuff,stimStruct,resp,data,is3d)
    [selectResp,selectIdx,selectStim,~,thumb] = getTopStim(resp,data,is3d);
    
    figure('pos',[2561,93,1030,789],'color','w');
    clf; ha = tight_subplot(6,6); ha = reshape(ha,6,6)';
    
    cols = colormap('lines'); cols = cols(1:6,:);
    colormap('parula');
%     plotSubplot(sta(1).s.*sta(2).s,binSpec.s,ha,1,[],{stimStruct(selectIdx).s},cols);
%     plotSubplot(sta(1).r.*sta(2).r,binSpec.r,ha,2,[],{stimStruct(selectIdx).r},cols);
%     plotSubplot(sta(1).t.*sta(2).t,binSpec.t,ha,3,[],{stimStruct(selectIdx).t},cols);
%     plotSubplot(sta(1).sr.*sta(2).sr,binSpec.sr,ha,4,[],{stimStruct(selectIdx).sr},cols);
%     plotSubplot(sta(1).st.*sta(2).st,binSpec.st,ha,5,[],{stimStruct(selectIdx).st},cols);
    
    plotSubplot(sta.s,binSpec.s,ha,1,[],{stimStruct(selectIdx).s},cols);
    plotSubplot(sta.r,binSpec.r,ha,2,[],{stimStruct(selectIdx).r},cols);
    plotSubplot(sta.t,binSpec.t,ha,3,[],{stimStruct(selectIdx).t},cols);
    plotSubplot(sta.sr,binSpec.sr,ha,4,[],{stimStruct(selectIdx).sr},cols);
    plotSubplot(sta.st,binSpec.st,ha,5,[],{stimStruct(selectIdx).st},cols);
    plotStimImages(thumb,selectResp,cols,ha,6);
    
    savefig(['plots/icosta/icosta_' runId '_linMult.fig']);
    % screen2png(['plots/icosta/icosta_' runId '_linMult.png']);
    
    if false
        for ii=1:3
            figure('color','k');
            plotSingleStim(gca,runId,selectStim(ii).genNum,selectStim(ii).linNum,selectStim(ii).stimNum)
        end
    end
    
    % clf; ha = tight_subplot(6,6); ha = reshape(ha,6,6)';
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

function plotSubplot(sta,binSpec,ha,rowNum,scale,stim,cols)
    binCenters = binSpec.binCenters;
    binCenters(cellfun(@isempty,binCenters)) = [];
    padding = binSpec.padding;
    padding(padding == 'i') = '';
    
    nCols = length(size(sta));
    stim = stim(1:3);
    staMax = max(sta(:));
    if ~exist('scale','var') || isempty(scale)
        scale = staMax;
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
            plotSingleSphereView(h,...
                binCenters{ii},binCenters{ii+1},ss,[0 scale],...
                cellfun(@(x) x(stimValIdx{ii},:),stim,'UniformOutput',false),cols);

        elseif padding(ii) == 's' || padding(ii) == 'h' || padding(ii) == 'r'
            allStim = cellfun(@(x) x(stimValIdx{ii},:),stim,'UniformOutput',false);
            plotSingleIcosphereView(h,ss,[0 scale],allStim,cols,padding(ii))
        else
            plot(h,binCenters{ii},ss,'k','linewidth',2); 
            hold(h,'on');
            for jj=1:3
                plot(h,stim{jj}(stimValIdx{ii},:),0.2*ones(length(stim{jj}(stimValIdx{ii},:)),1),'.','color',cols(jj,:),'MarkerSize',10)
            end

            box(h,'off');
            set(h,'ylim',[0 scale],'linewidth',2);
        end
    end
end

function plotSingleSphereView(hAx,th_centers,ph_centers,intensity,clim,allStim,stimCols)
    if size(ph_centers,2) == 2
        intensity = [intensity zeros(length(th_centers),length(ph_centers))];
        ph_centers = [ph_centers -ph_centers];
    end

    th = repmat(th_centers',length(ph_centers),1); th = th(:);
    ph = repmat(ph_centers,length(th_centers),1); ph = ph(:);
    intensity = intensity(:);
    
    hPlot = PlotSphereIntensity(hAx, th, ph, ones(size(th)), intensity); 
    view(hAx,0,90); set(hAx,'clim',clim); hold(hAx,'on');
    hp = patch([-1.3 -1.3 1.3 1.3],[0 0 0 0],[1.3 -1.3 -1.3 1.3],'r','parent',hAx);
    hp.EdgeColor = 'none'; hp.FaceAlpha = 0.2;
    axis(hAx,'off');
    
    for ii=1:length(allStim)
        stim = allStim{ii};
        stim = [stim' ones(size(stim,2),1)];
        [x,y,z] = sph2cart(stim(:,1),stim(:,2),stim(:,3));
        hStim = plot3(hAx,x,y,z,'.','color',stimCols(ii,:),'MarkerSize',30);
    end
    
    hPlot = [hPlot hp hStim];
    
    t = hgtransform('Parent',hAx); 
    for ii=1:length(hPlot)
        set(hPlot(ii),'Parent',t);
    end
    
    done = true;
    while ~done
        Txy = makehgtform('xrotate',0,'yrotate',0,'yrotate',0); 
        set(t,'Matrix',Txy)
        xx = input('x: '); yy = input('y: '); zz = input('z: ');
        Txy = makehgtform('xrotate',xx*pi/16,'yrotate',yy*pi/16,'zrotate',zz*pi/16); 
        set(t,'Matrix',Txy)
        done = validatedInput('happy?: ',[0 1]);
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

    hPlot = plotAxes(hAx);
    set(hAx,'clim',clim);
    
    hp = patch('Vertices',verts,'faces',faces,'parent',hAx);
    hp.EdgeColor = 'w'; hp.LineWidth = 2;
    hp.FaceAlpha = 1; hp.FaceColor = 'flat'; hp.FaceVertexCData = intensity/max(intensity);
    axis(hAx,'off','equal');
    
    hpl = patch([-1.3 -1.3 1.3 1.3],[0 0 0 0],[1.3 -1.3 -1.3 1.3],'r','parent',hAx);
    hpl.EdgeColor = 'none'; hpl.FaceAlpha = 0.2;
    
    for ii=1:length(allStim)
        stim = allStim{ii};
        stim = [stim' 1.2*ones(size(stim,2),1)];
        [x,y,z] = sph2cart(stim(:,1),stim(:,2),stim(:,3));
        hStim = plot3(hAx,x,y,z,'.','color',stimCols(ii,:),'MarkerSize',30);
    end
    
    hPlot = [hPlot hp hpl hStim];
    
    t = hgtransform('Parent',hAx); 
    for ii=1:length(hPlot)
        set(hPlot(ii),'Parent',t);
    end
    
    done = true;
    while ~done
        Txy = makehgtform('xrotate',0,'yrotate',0,'yrotate',0); 
        set(t,'Matrix',Txy)
        xx = input('x: '); yy = input('y: '); zz = input('z: ');
        Txy = makehgtform('xrotate',xx*pi/16,'yrotate',yy*pi/16,'zrotate',zz*pi/16); 
        set(t,'Matrix',Txy)
        done = validatedInput('happy?: ',[0 1]);
    end
    
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
    
    xAxis = [-1.3 0 0; 1.3 0 0];
    yAxis = [0 -1.3 0; 0 1.3 0];
    zAxis = [0 0 -1.3; 0 0 1.3];
    hPlot(1) = plot3(hAx,xAxis(:,1), xAxis(:,2), xAxis(:,3), 'r', 'LineWidth', 2);
    hPlot(2) = plot3(hAx,yAxis(:,1), yAxis(:,2), yAxis(:,3), 'g', 'LineWidth', 2);
    hPlot(3) = plot3(hAx,zAxis(:,1), zAxis(:,2), zAxis(:,3), 'b', 'LineWidth', 2);

    hPlot(4) = text(1.4,0,0.04,'R', 'FontSize', 12,'parent',hAx,'color','r');
    hPlot(5) = text(0,1.4,0.04,'T', 'FontSize', 12,'parent',hAx,'color','g');
    hPlot(6) = text(0.04,0.04,1.4,'F', 'FontSize', 12,'parent',hAx,'color','b');
    hPlot(7) = text(-1.4,0,-0.04,'L', 'FontSize', 12,'parent',hAx,'color','r');
    hPlot(8) = text(-0.04,-0.04,-1.4,'B', 'FontSize', 12,'parent',hAx,'color','b');
end