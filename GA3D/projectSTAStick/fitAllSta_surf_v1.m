function [linSta,linSta_shuff,fullSetSta,binSpec] = fitAllSta_surf_v1(surfFitParams,selectedIds,resp,lineage,is3d)
    resp = nanmean(resp,2);
    resp = resp ./ max(resp);
    resp(~is3d) = nan;
    
    % s: full sphere, r: rotated hemi, z: normal, h: hemi, i: ignore, c: circular
    binSpec.surf = getBinSpec(surfFitParams,[1 80 3 1 80 5 5 8],'isziszzc'); 
    [~,~,binSpec.ico.s] = getIcosphereDeets(1,0,0);

    for ll=1:2
        disp(['... lineage ' num2str(ll)]);
        stim_l = surfFitParams(lineage == ll);
        ids_l = selectedIds(lineage == ll);
        resp_l = resp(lineage == ll);
        
        disp('....... real');
        linSta(ll) = doSta(stim_l,ids_l,resp_l,binSpec);
        disp('....... shuffle');
        linSta_shuff(ll) = doSta(stim_l,ids_l,resp_l(randperm(length(resp_l))),binSpec);
    end
    disp('... full set');
    fullSetSta = doSta(surfFitParams,selectedIds,resp,binSpec);
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

function sta = doSta(stim,ids,resp,binSpec)
    respThreshold = 0;
    eval(['surf_sta = squeeze(zeros('  replace(num2str(binSpec.surf.nBin),'  ',',') '));']); % add before replace to keep stimuli in memory num2str(length(stim)) ',' 
    eval(['surf_staN = squeeze(zeros('  replace(num2str(binSpec.surf.nBin),'  ',',') '));']);
    
    x = getX(binSpec.surf.nBin,binSpec.surf.binCenters,binSpec.surf.padding);
    
    for s=1:length(stim)
        fprintf('.');
        if ~isnan(resp(s))
            if resp(s) >= respThreshold
                tic
                [s_sta_temp,s_staN_temp] = doSta_perStim(stim{s}(ids{s},:),resp(s),x,binSpec.surf,binSpec.ico);
                surf_sta = surf_sta + s_sta_temp;
                surf_staN = surf_staN + s_staN_temp;
                toc
            end
        end
    end
    fprintf('\n')
    disp('........... smoothing s');
    sta.surf = surf_sta ./ surf_staN; 
    sta.surf(isnan(sta.surf)) = 0; 
    
    % surf_sta = padAndSmooth(surf_sta,binSpec.s.kernel,binSpec.s.padding);
end

function [tempRwa,tempRwaN] = doSta_perStim(stim,resp,x,binSpec,ico)
    nBin = binSpec.nBin;
    std_bin = binSpec.std_bin;
    
    % tempRwa = squeeze(zeros(nBin));
    % tempRwaN = squeeze(zeros(nBin));
    
    totalBins = nBin; totalBins(totalBins == 1) = [];
    
    if isnan(stim(1))
        return
    end
    
    tRwa = cell(1,size(stim,1));
    tRwaN = cell(1,size(stim,1));
    parfor ss=1:size(stim,1)
        betaRwaN = [1 std_bin stim(ss,:)];
        % tempRwa = tempRwa + reshape(getGaussianNd(betaRwa,x,binSpec.padding,ico),size(tempRwaN));
        % tempRwaN = tempRwaN + reshape(getGaussianNd(betaRwaN,x,binSpec.padding,ico),size(tempRwa));
        tRwaN{ss} = reshape(getGaussianNd(betaRwaN,x,binSpec.padding,ico),totalBins);
        tRwa{ss} = resp * tRwaN{ss}; % reshape(getGaussianNd(betaRwa,x,binSpec.padding,ico),totalBins); %#ok<*PFBNS>
    end
    tempRwa = sum(cat(7,tRwa{:}),7);
    tempRwaN = sum(cat(7,tRwaN{:}),7);
end

function y = getGaussianNd(beta,x0,padding,ico)
    % beta = [a s1 s2 s3 s4 s5 ... m1 m2 m3 m4 m5 ...]
    % x0 = [x1 x2 x3 x4 x5 ...]
    
    n = length(padding);
    
    a = beta(1);
    s = beta(2:1+n);
    m = beta(2+n:end);

    c = zeros(size(x0));
    binCount = 0;
    % s: full sphere, r: rotated hemi, z: normal, h: hemi, i: ignore, c: circular
    for ii=1:n
        if padding(ii) ~= 'i'
            binCount = binCount + 1; v1 = [];
            if padding(ii) == 'c'
                cc = abs(circ_dist(x0(:,binCount),m(ii)));
            elseif padding(ii) == 'z'
                cc = x0(:,binCount)-m(ii);
            elseif padding(ii) == 's'
                norms = ico.s;
                [v1(1),v1(2),v1(3)] = sph2cart(m(ii-1),m(ii),1);
                v2 = norms(x0(:,binCount),:);
                v1 = repmat(v1,size(v2,1),1);
                cc = acos(dot(v1',v2'));
            elseif padding(ii) == 'r'
                norms = ico.r;
                [v1(1),v1(2),v1(3)] = sph2cart(m(ii-1),m(ii),1);
                v2 = norms(x0(:,binCount),:);
                v1 = repmat(v1,size(v2,1),1);
                cc = acos(dot(v1',v2'));
            elseif padding(ii) == 'h'
                norms = ico.h;
                [v1(1),v1(2),v1(3)] = sph2cart(m(ii-1),m(ii),1);
                v2 = norms(x0(:,binCount),:);
                v1 = repmat(v1,size(v2,1),1);
                cc = acos(dot(v1',v2'));
            end
            c(:,binCount) = (cc.^2)/(2*s(ii)^2);
        end
    end
    
    s(s==0) = [];
    b = 1/(2*pi*prod(s));
    
    y = a * b .* exp(-(sum(c,2)));
end

function x = getX(nBin,binCenters,padding) %#ok<STOUT,INUSL>
    str1 = '['; str2 = '('; str3 = '[';
    binCount = 0;
    for jj=1:length(nBin)
        if padding(jj) ~= 'i'
            binCount = binCount + 1;
            str1 = [str1 'b' num2str(binCount) ',']; %#ok<*AGROW>
            str2 = [str2 'binCenters{' num2str(jj) '},'];
            str3 = [str3 'b' num2str(binCount) '(:),'];
        end
    end
    str1 = [str1(1:end-1) ']'];
    str2 = [str2(1:end-1) ');'];
    str3 = [str3(1:end-1) '];'];
    
    eval([str1 ' = ndgrid' str2]);
    eval(['x = ' str3]);
end