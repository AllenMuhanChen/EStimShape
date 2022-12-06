function [roots,selectedIds] = getRoots(data)
    roots = cell(length(data),1);
    selectedIds = cell(length(data),1);
    
    for ii=1:length(data)
        a = [data(ii).comp([data(ii).comp.compPart] == 'R').pos];
        a = reshape(a,3,length(a)/3)';
        roots{ii} = unique(a,'rows');
        
        selectedIds{ii} = false(size(data(ii).vert,1),1);
        for jj=1:size(roots{ii},1)
            dist = sqrt(sum((data(ii).vert - repmat(roots{ii}(jj,:),size(data(ii).vert,1),1)).^2,2));
            [~,idx] = sort(dist);
            selectedIds{ii}(idx(1:100)) = 1;
        end
    end
end

