function plotStaProjection(runId,binSpec,sta,stimStruct,resp,data,is3d,predCompResp)
    selectIdx = getTopStim(resp,is3d,predCompResp);
    
    if length(sta) == 2
        staMult.s  = sta(1).s .* sta(2).s;
        staMult.r  = sta(1).r .* sta(2).r;
        staMult.t  = sta(1).t .* sta(2).t;
        staMult.sr = sta(1).sr .* sta(2).sr;
        staMult.st = sta(1).st .* sta(2).st;
        sta = staMult;
    end
    
    %type = pickBestSta(sta);
   
    figure('color','w','pos',[365,475,1895,773])
    for ii=1:length(selectIdx)
        h = subplot(2,length(selectIdx)/2,ii);
        vert = plotStimVert(h,data(selectIdx(ii)).vert,data(selectIdx(ii)).s);
        face = data(selectIdx(ii)).face;
        % switch type
            projectSTA(h,{stimStruct(selectIdx(ii)).s},predCompResp.s{selectIdx(ii)},vert,face,[1 1 0]);
            projectSTA(h,{stimStruct(selectIdx(ii)).r},predCompResp.r{selectIdx(ii)},vert,face,[0 1 1]);
            projectSTA(h,{stimStruct(selectIdx(ii)).t},predCompResp.t{selectIdx(ii)},vert,face,[1 0 1]);
        % end
    end
    savefig(['plots/projection/projection_' runId '.fig']);
    close;
end

function type = pickBestSta(sta)
    [~,type] = max([max(sta.s(:)) max(sta.r(:)) max(sta.t(:)) max(sta.sr(:)) max(sta.st(:))]);
end

function selectIdx = getTopStim(resp,is3d,predCompResp)
    predCompResp.s = cellfun(@max,predCompResp.s);
    predCompResp.r = cellfun(@max,predCompResp.r);
    predCompResp.t = cellfun(@max,predCompResp.t);
    % 
    % idx_s(ismember(idx_s,find(~is3d))) = nan;
    % idx_r(ismember(idx_r,find(~is3d))) = nan;
    % idx_t(ismember(idx_t,find(~is3d))) = nan;
    % 
    % 
    % count = 1; stream = 1;
    % while count < 7 && stream < 30
    %     if ~isnan(idx_s(stream))
    %         if find(idx_r == idx_s(stream)) < 30 && find(idx_t == idx_s(stream)) < 30
    %             selectIdx(count) = idx_s(stream);
    %             count = count + 1;
    %         end
    %     end
    %     stream = stream + 1;
    % end
    
    resp = nanmean(resp,2); resp = resp/max(resp);
    resp(~is3d) = nan;
    [sortedResp,idx] = sort(resp,'descend');
    idx(isnan(sortedResp)) = [];
    sortedResp(isnan(sortedResp)) = [];
    % selectResp = [sortedResp(1:7); sortedResp(end-6:end)]; 
    % selectIdx = [selectIdx'; idx(end-length(selectIdx)-1:end)];
    topIdx = idx(1:20); topResp = sortedResp(1:20);
    [bestS,bestSIdx] = sort(abs(predCompResp.s(topIdx) - topResp));
    [bestR,bestRIdx] = sort(abs(predCompResp.r(topIdx) - topResp));
    [bestT,bestTIdx] = sort(abs(predCompResp.t(topIdx) - topResp));
    preselected = sortrows([bestS bestSIdx ones(20,1); bestR bestRIdx 2*ones(20,1); bestT bestTIdx 3*ones(20,1)]);
    
    count = 1; stream = 1; selectIdx = zeros(7,1);
    while count < 8 && stream < 60
        if ~sum(selectIdx == topIdx(preselected(stream,2)))
            selectIdx(count) = topIdx(preselected(stream,2));
            count = count + 1;
        end
        stream = stream + 1;
    end
    
    selectIdx = [selectIdx; idx(end-6:end)];
end

function vert = plotStimVert(h,vert,s)
    vert = vert .* s;
    centerOfMass = (max(vert) + min(vert)) / 2;
    vert = vert - repmat(centerOfMass,size(vert,1),1);
    maxRadDist = max(sqrt(sum(vert.^2,2)));
    vert = vert./maxRadDist;
	plot3(h,vert(:,1),vert(:,2),vert(:,3),'.','color',[0.8 0.8 0.8]);
    axis(h,'equal','off'); hold(h,'on');
    view(h,0,90);
end

function projectSTA(h,stim,predResp,vert,face,baseCol)
    stim = stim{1};
    
    for ii=1:size(stim,2)
        col = baseCol .* predResp(ii);
        s = stim(:,ii);
        [x,y,z] = sph2cart(s(1),s(2),s(3));
        plot3(h,x,y,z,'.','MarkerSize',30,'color',col);
        [tx,ty,tz] = sph2cart(s(4),s(5),0.3);
        line([x x+tx],[y y+ty],[z z+tz],'linewidth',2,'color',col,'parent',h);
        r = s(6);
        vert2plot = sqrt(sum((vert - repmat([x y z],size(vert,1),1)).^2,2)) < 1.2*r;
        face2plot = sum(ismember(face,find(vert2plot)),2) == 3;
        patch('vertices',vert,'faces',face(face2plot,:),'edgecolor','none',...
            'facecolor',col,'facealpha',1);
        % scatter3(vert(vert2plot,1),vert(vert2plot,2),vert(vert2plot,3),...
        %     'cdata',[predResp(ii) 0 0],'marker','.','sizedata',40);
    end
end

function y = getPerComponentResp(sta,stim,padding,binCenters,ico)
    n = length(padding);
    y = zeros(size(stim,2),1);
    binCount = 0;
    % s: full sphere, r: rotated hemi, z: normal, h: hemi, i: ignore, c: circular
    for cc=1:size(stim,2)
        comp = stim(:,cc)';
        idx = zeros(ndims(sta),1);
        str = '(';
        for ii=1:n
            if padding(ii) ~= 'i'
                binCount = binCount + 1; v1 = [];
                if padding(ii) == 'c'
                    dist = abs(circ_dist(comp(ii),binCenters{ii}));
                elseif padding(ii) == 'z'
                    dist = abs(binCenters{ii}-comp(ii));
                elseif padding(ii) == 's'
                    v2 = ico.s;
                    [v1(1),v1(2),v1(3)] = sph2cart(comp(ii-1),comp(ii),1);
                    v1 = repmat(v1,size(v2,1),1);
                    dist = acos(dot(v1',v2'));
                elseif padding(ii) == 'r'
                    v2 = ico.r;
                    [v1(1),v1(2),v1(3)] = sph2cart(comp(ii-1),comp(ii),1);
                    v1 = repmat(v1,size(v2,1),1);
                    dist = acos(dot(v1',v2'));
                elseif padding(ii) == 'h'
                    v2 = ico.h;
                    [v1(1),v1(2),v1(3)] = sph2cart(comp(ii-1),comp(ii),1);
                    v1 = repmat(v1,size(v2,1),1);
                    dist = acos(dot(v1',v2'));
                end
                [~,idx(binCount)] = min(dist);
                str = [str num2str(idx(binCount)) ','];
            end    
        end
        str = [str(1:end-1) ');'];
        eval(['y(cc) = sta' str]);
    end
end