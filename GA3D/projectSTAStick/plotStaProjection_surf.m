function plotStaProjection_surf(runId,resp,data,is3d,predCompResp)
    selectIdx = getTopStim(resp,is3d,predCompResp);
       
    figure('color','w','pos',[365,475,1895,773])
    for ii=1:length(selectIdx)
        h = subplot(2,length(selectIdx)/2,ii);
        projectSTA(h,data(selectIdx(ii)).vert,data(selectIdx(ii)).s,predCompResp.mult{selectIdx(ii)});
            
    end
    % savefig(['plots/projection/projection_surf_' runId '.fig']);
    close;
end


function selectIdx = getTopStim(resp,is3d,predCompResp)
    predCompResp.mult = cellfun(@max,predCompResp.mult);
    
    resp = nanmean(resp,2); resp = resp/max(resp);
    resp(~is3d) = nan;
    [sortedResp,idx] = sort(resp,'descend');
    idx(isnan(sortedResp)) = [];
    sortedResp(isnan(sortedResp)) = [];
    
    topIdx = idx(1:20); topResp = sortedResp(1:20);
    [bestS,bestSIdx] = sort(abs(predCompResp.mult(topIdx) - topResp));
    preselected = sortrows([bestS bestSIdx ones(20,1)]);
    
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

function vert = projectSTA(h,vert,s,predResp)
    vert = vert .* s;
    centerOfMass = (max(vert) + min(vert)) / 2;
    vert = vert - repmat(centerOfMass,size(vert,1),1);
    maxRadDist = max(sqrt(sum(vert.^2,2)));
    vert = vert./maxRadDist;
    scatter3(h,vert(:,1),vert(:,2),vert(:,3),100,[predResp zeros(length(predResp),2)],'.');
    axis(h,'equal','off'); hold(h,'on');
    view(h,0,90);
end
