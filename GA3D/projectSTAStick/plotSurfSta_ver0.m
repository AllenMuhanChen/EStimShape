function plotSurfSta_ver0(runId,binSpec,sta,sta_shuff,surfFitParams,resp,data,is3d)
    [selectResp,~,~,~,thumb] = getTopStim(resp,data,is3d);
    
    if length(sta) == 2
        staMult = sta(1).surf .* sta(2).surf;
    else
        staMult = sta.surf;
    end
    
    %%
    hf = figure('pos',[1392,897,1169,291],'color','w');
    clf; ha = tight_subplot(2,6,[0.1 0.05],0.05,0.05); ha = reshape(ha,6,2)';
    
    plotSubplot(staMult,binSpec,ha,1,[],0);
    plotStimImages(thumb,selectResp,ha,2);
    
    savefig(['plots/icosta_surf/icosta_surf_' runId '_all_linMult.fig']);
    close(hf)
end

function plotSubplot(sta,binSpec,ha,rowNum,scale,doMean)
    binCenters = binSpec.surf.binCenters;
    binCenters(cellfun(@isempty,binCenters)) = [];
    padding = binSpec.surf.padding;
    padding(padding == 'i') = '';
    
    nCols = length(size(sta));
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
    binId = sub2ind(size(sta),b1(1),b2(1),b3(1),b4(1),b5(1),b6(1));
    for ii=1:nCols
        h = ha(rowNum,ii); staForMean = sta;
        str = '(';
        for jj=1:nCols
            if ii==jj
                str = [str ':,'];
            else
                str = [str 'b' num2str(jj) '(1),'];
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
        elseif padding(ii) == 's' || padding(ii) == 'h' || padding(ii) == 'r'
            plotSingleIcosphereView(h,ss,[0 scale],padding(ii))
        else
            plot(h,binCenters{ii},ss,'k','linewidth',2); 
            hold(h,'on');

            box(h,'off');
            set(h,'ylim',[0 scale],'linewidth',2);
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

    hPlot = plotAxes(hAx);
    set(hAx,'clim',clim);
    
    hp = patch('Vertices',verts,'faces',faces,'parent',hAx);
    hp.EdgeColor = 'w'; hp.LineWidth = 2;
    hp.FaceAlpha = 1; hp.FaceColor = 'flat'; hp.FaceVertexCData = intensity/max(intensity);
    axis(hAx,'off','equal');
    
    hpl = patch([-1.3 -1.3 1.3 1.3],[0 0 0 0],[1.3 -1.3 -1.3 1.3],'r','parent',hAx);
    hpl.EdgeColor = 'none'; hpl.FaceAlpha = 0.2;
    
    hPlot = [hPlot hp hpl];
    
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

function plotStimImages(thumb,selectResp,ha,rowNum)
    for ii=1:length(thumb)
        imshow(thumb{ii},'parent',ha(rowNum,ii)); hold(ha(rowNum,ii),'on');
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

