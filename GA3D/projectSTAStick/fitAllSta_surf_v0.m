function [linSta,linSta_shuff,fullSetSta,binSpec] = fitAllSta_surf_v0(surfFitParams,selectedIds,resp,lineage,is3d)
    resp = nanmean(resp,2);
    resp = resp ./ max(resp);
    resp(~is3d) = nan;
    
    % s: full sphere, r: rotated hemi, z: normal, h: hemi, i: ignore, c: circular
    binSpec.surf = getBinSpec(surfFitParams,[1 80 3 1 80 5 5 8],'isziszzc'); 
    [~,~,binSpec.ico.s] = getIcosphereDeets(1,0,0);

    for ll=1:2
        disp(['... lineage ' num2str(ll)]);
        stim_l = surfFitParams(lineage == ll);
        resp_l = resp(lineage == ll);
        ids_l = []; % selectedIds(lineage == ll);
        
        disp('....... real');
        linSta(ll) = doSta(stim_l,resp_l,ids_l,binSpec);
        disp('....... shuffle');
        linSta_shuff(ll) = 0; % doSta(stim_l,resp_l(randperm(length(resp_l))),ids_l,binSpec);
    end
    disp('... full set');
    fullSetSta = []; % doSta(surfFitParams,resp,selectedIds,binSpec);
end

function spec = getBinSpec(stim,nBin,padding)  
    binCenters = cell(1,length(nBin));
    std_bin = nan(1,length(nBin));
    for ii=1:length(nBin)
        if padding(ii) == 's'
            binCenters{ii} = 1:80;
            std_bin(ii) = deg2rad(18);
        elseif padding(ii) == 'h' || padding(ii) == 'r'
            binCenters{ii} = 1:40;
            std_bin(ii) = deg2rad(18);
        elseif padding(ii) == 'i'
            binCenters{ii} = [];
            std_bin(ii) = 0;
        elseif padding(ii) == 'c' 
            maxC = max(cellfun(@(x) max(x(:,ii)),stim));
            minC = min(cellfun(@(x) min(x(:,ii)),stim));
            binEdges = linspace(minC,maxC,nBin(ii)+1);
            binCenters{ii} = conv(binEdges,[0.5 0.5],'valid');
            std_bin(ii) = pi/4;
        else
            high = max(cellfun(@(x) max(x(:,ii)),stim));
            low = min(cellfun(@(x) min(x(:,ii)),stim));
            
            binEdges = linspace(low,high,nBin(ii)+1);
            binCenters{ii} = conv(binEdges,[0.5 0.5],'valid');
            std_bin(ii) = min(diff(binEdges));
        end
    end

    spec.nBin = nBin;
    spec.binCenters = binCenters;
    spec.std_bin = std_bin;
    spec.padding = padding;
end

function sta = doSta(stim,resp,selectedIds,binSpec)
    respThreshold = 0;
    eval(['surf_sta = squeeze(zeros(' strrep(strrep(num2str(binSpec.surf.nBin),'   ',','),'  ',',') '));']);
    eval(['surf_staN = squeeze(zeros(' strrep(strrep(num2str(binSpec.surf.nBin),'   ',','),'  ',',') '));']);
    
%     tic
    for s=1:length(stim)
        fprintf('.');
        if ~isnan(resp(s))
            if resp(s) >= respThreshold
                % (selectedIds{s},:)
                [s_sta_temp,s_staN_temp] = doSta_perStim(stim{s},resp(s),binSpec.surf,binSpec.ico);
                surf_sta = surf_sta + s_sta_temp;
                surf_staN = surf_staN + s_staN_temp;
            end
        end
    end
%     toc
    fprintf('\n')
    
    surf_sta = squeeze(surf_sta);
    surf_staN = squeeze(surf_staN);
    
    surf_sta = surf_sta ./ surf_staN; 
    surf_sta(isnan(surf_sta)) = 0;     
    sta.surf = surf_sta;
    
    disp('........... smoothing surface sta');
    % [sta.filt,sta.thresh] = filterAndThresholdSta(surf_sta,1,1);
    sta.filt = [];
    sta.thresh = [];
end

function [tempRwa,tempRwaN] = doSta_perStim(stim,resp,binSpec,ico)
    nBin = binSpec.nBin;
    binCenters = binSpec.binCenters; 
    padding = binSpec.padding;
    
    tempRwa = squeeze(zeros(nBin));
    tempRwaN = squeeze(zeros(nBin));
    
    nPts = size(stim,1);
    bin = nan(nPts,length(nBin));
    for ss=1:length(nBin)
        if padding(ss) == 's'
            norms = ico.s;
            norms = transpose(reshape(repmat(transpose(norms),nPts,1),3,nPts*size(ico.s,1)));
            
            v1 = [];
            [v1(:,1),v1(:,2),v1(:,3)] = sph2cart(stim(:,ss-1),stim(:,ss),1);
            v1 = repmat(v1,size(ico.s,1),1);
            
            dist = reshape(abs(dot(v1',norms')),nPts,80);
            [~,bin(:,ss)] = max(dist,[],2);
        elseif padding(ss) == 'h' || padding(ss) == 'r'

        elseif padding(ss) == 'i'
            
        elseif padding(ss) == 'c' 
            [~,bin(:,ss)] = min(abs(circ_dist(repmat(binCenters{ss},nPts,1),repmat(stim(:,ss),1,length(binCenters{ss})))),[],2);
           
        elseif padding(ss) == 'z'
            [~,bin(:,ss)] = min(abs(repmat(binCenters{ss},nPts,1) - repmat(stim(:,ss),1,length(binCenters{ss}))),[],2);
        end
    end
    
    % assign resp of stimulus to that bin. Don't
    % assign more than once.
    bin(:,padding == 'i') = [];
    bin = unique(bin,'rows','stable');
    for ss=1:size(bin,1)
        eval(['tempRwa(' strrep(strrep(num2str(bin(ss,:)),'   ',','),'  ',',') ') = resp;']);
        eval(['tempRwaN(' strrep(strrep(num2str(bin(ss,:)),'   ',','),'  ',',') ') = 1;']);
    end
end
