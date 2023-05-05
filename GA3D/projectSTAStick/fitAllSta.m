function [linSta,linSta_shuff,fullSetSta,binSpec] = fitAllSta(stimStruct,resp,lineage,is3d)
    resp = nanmean(resp,2);
    resp = resp ./ max(resp);
%     resp(~is3d) = nan;
    
    % s: full sphere, r: rotated hemi, z: normal, h: hemi, i: ignore, c: circular
    binSpec.s = getBinSpec_gauss([stimStruct.s]',[1 80 5 1 40 5 5 5],'iszihzzz'); 
    binSpec.r = getBinSpec_gauss([stimStruct.r]',[1 80 5 1 80 5 4 4],'isziszcc');
    binSpec.t = getBinSpec_gauss([stimStruct.t]',[1 80 5 1 80 5],'iszisz');
%     binSpec.sr = getBinSpec_gauss([stimStruct.sr]',[1 80 5 1 80 5],'iszisz');
%     binSpec.st = getBinSpec_gauss([stimStruct.st]',[1 80 5 1 40 5],'iszihz');
    
    [~,~,binSpec.ico.s] = getIcosphereDeets(1,0,0);
    [~,~,binSpec.ico.h] = getIcosphereDeets(0,0,0);
    [~,~,binSpec.ico.r] = getIcosphereDeets(0,1,0);
    
    for ll=1:2
        disp(['... lineage ' num2str(ll)]);
        stim_l = stimStruct(lineage == ll);
        resp_l = resp(lineage == ll);
        
        disp('....... real');
        linSta(ll) = doSta(stim_l,resp_l,binSpec);
        disp('....... shuffle');
        linSta_shuff(ll) = 0; % doSta(stim_l,resp_l(randperm(length(resp_l))),binSpec);
    end
    disp('... full set');
    fullSetSta = []; % doSta(stimStruct,resp,binSpec);
end

function spec = getBinSpec(stim,nBin,padding)
    
    for ii=1:length(nBin)
        % bin edges. one more than total number of bins
        binEdges{ii} = linspace(min(stim(:,ii)),max(stim(:,ii)),nBin(ii)+1);

        % widths of bins and half standard deviations
        binWidth(ii) = (max(stim(:,ii))-min(stim(:,ii))) / nBin(ii);
        sigma(ii) = binWidth(ii) .* 1;
        nSigmasToConsider(ii) = 2;
    end

    % gaussian kernel. size of kernel is 2n+1 where n is sigma*numSigmasToConsider
    kernel = makeKernel(binWidth,sigma,nSigmasToConsider);
    
    spec.nBin = nBin;
    spec.binEdges = binEdges;
    spec.binWidth = binWidth;
    spec.sigma = sigma;
    spec.nSigmasToConsider = nSigmasToConsider;
    spec.kernel = kernel;
    spec.padding = padding;
end

function spec = getBinSpec_gauss(stim,nBin,padding)  
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
            if min(stim(:,ii)) > 0 % circular variable is 0-pi, most likely
                binEdges = linspace(0,pi,nBin(ii)+1);    
            else % circular variable is -pi/2-pi/2, most likely
                binEdges = linspace(-pi/2,pi/2,nBin(ii)+1);
            end
            binCenters{ii} = conv(binEdges,[0.5 0.5],'valid');
            std_bin(ii) = pi/4;
        else
            binEdges = linspace(min(stim(:,ii)),max(stim(:,ii)),nBin(ii)+1);
            binCenters{ii} = conv(binEdges,[0.5 0.5],'valid');
            std_bin(ii) = min(diff(binEdges));
        end
    end

    spec.nBin = nBin;
    spec.binCenters = binCenters;
    spec.std_bin = std_bin;
    spec.padding = padding;
end

function sta = doSta(stim,resp,binSpec)
    respThreshold = 0;
    eval(['s_sta = squeeze(zeros('  strrep(strrep(num2str(binSpec.s.nBin),'   ',','),'  ',',') '));']);
    eval(['s_staN = squeeze(zeros('  strrep(strrep(num2str(binSpec.s.nBin),'   ',','),'  ',',') '));']);
    eval(['r_sta = squeeze(zeros('  strrep(strrep(num2str(binSpec.r.nBin),'   ',','),'  ',',') '));']);
    eval(['r_staN = squeeze(zeros('  strrep(strrep(num2str(binSpec.r.nBin),'   ',','),'  ',',') '));']);
    eval(['t_sta = squeeze(zeros('  strrep(strrep(num2str(binSpec.t.nBin),'   ',','),'  ',',') '));']);
    eval(['t_staN = squeeze(zeros('  strrep(strrep(num2str(binSpec.t.nBin),'   ',','),'  ',',') '));']);
%     eval(['sr_sta = squeeze(zeros('  strrep(strrep(num2str(binSpec.sr.nBin),'   ',','),'  ',',') '));']);
%     eval(['sr_staN = squeeze(zeros('  strrep(strrep(num2str(binSpec.sr.nBin),'   ',','),'  ',',') '));']);
%     eval(['st_sta = squeeze(zeros('  strrep(strrep(num2str(binSpec.st.nBin),'   ',','),'  ',',') '));']);
%     eval(['st_staN = squeeze(zeros('  strrep(strrep(num2str(binSpec.st.nBin),'   ',','),'  ',',') '));']);
    
    for s=1:length(stim)
        fprintf('.');
        if ~isnan(resp(s))
            if resp(s) >= respThreshold
                [s_sta_temp,s_staN_temp] = doGaussianSta_perStim(stim(s).s',resp(s),binSpec.s,binSpec.ico);
                s_sta = s_sta + s_sta_temp;
                s_staN = s_staN + s_staN_temp;

                [r_sta_temp,r_staN_temp] = doGaussianSta_perStim(stim(s).r',resp(s),binSpec.r,binSpec.ico);
                r_sta = r_sta + r_sta_temp;
                r_staN = r_staN + r_staN_temp;

                [t_sta_temp,t_staN_temp] = doGaussianSta_perStim(stim(s).t',resp(s),binSpec.t,binSpec.ico);
                t_sta = t_sta + t_sta_temp;
                t_staN = t_staN + t_staN_temp;

%                 [sr_sta_temp,sr_staN_temp] = doGaussianSta_perStim(stim(s).sr',resp(s),binSpec.sr,binSpec.ico);
%                 sr_sta = sr_sta + sr_sta_temp;
%                 sr_staN = sr_staN + sr_staN_temp;
% 
%                 [st_sta_temp,st_staN_temp] = doGaussianSta_perStim(stim(s).st',resp(s),binSpec.st,binSpec.ico);
%                 st_sta = st_sta + st_sta_temp;
%                 st_staN = st_staN + st_staN_temp;
            end
        end
    end
    fprintf('\n')
    % disp('........... smoothing s');
    sta.s = s_sta ./ s_staN; sta.s(isnan(sta.s)) = 0; %  sta.s = padAndSmooth(sta.s,binSpec.s.kernel,binSpec.s.padding);
    % disp('........... smoothing r');
    sta.r = r_sta ./ r_staN; sta.r(isnan(sta.r)) = 0; % sta.r = padAndSmooth(sta.r,binSpec.r.kernel,binSpec.r.padding);
    % disp('........... smoothing t');
    sta.t = t_sta ./ t_staN; sta.t(isnan(sta.t)) = 0; % sta.t = padAndSmooth(sta.t,binSpec.t.kernel,binSpec.t.padding);
%     % disp('........... smoothing sr');
%     sta.sr = sr_sta ./ sr_staN; sta.sr(isnan(sta.sr)) = 0; % sta.sr = padAndSmooth(sta.sr,binSpec.sr.kernel,binSpec.sr.padding);
%     % disp('........... smoothing st');
%     sta.st = st_sta ./ st_staN; sta.st(isnan(sta.st)) = 0; % sta.st = padAndSmooth(sta.st,binSpec.st.kernel,binSpec.st.padding);
end

function [tempRwa,tempRwaN] = doSta_perStim(stim,resp,nBin,binEdges)
    tempRwa = zeros(nBin);
    tempRwaN = zeros(nBin);
    
    if isnan(stim(1))
        return
    end
    
    % for each component, bin the values
    for ii=1:length(nBin)
        % nX contains total elements in all 20 bins; for debug
        % last bin is for elements >= last bin edge.
        % binX contains bin for nth element
        [nX,binX] = histc(stim(:,ii),binEdges{ii});

        % since last bin contains all elements >= last bin edge, assign
        % those elements to the last bin instead. Ideally that bin
        % should be empty anyway.
        binX(binX>nBin(ii)) = nBin(ii);

        bin(ii,:) = binX;
    end

    % assign resp of stimulus to that bin. Don't
    % assign more than once.
    bin = unique(bin','rows','stable')';
    for b=1:size(bin,2)
        eval(['tempRwa(' replace(num2str(bin(:,b)'),'  ',',') ') = resp;'])
        eval(['tempRwaN(' replace(num2str(bin(:,b)'),'  ',',') ') = 1;'])
    end
end

function [tempRwa,tempRwaN] = doGaussianSta_perStim(stim,resp,binSpec,ico)
    nBin = binSpec.nBin;
    binCenters = binSpec.binCenters; 
    std_bin = binSpec.std_bin;
    
    tempRwa = squeeze(zeros(nBin));
    tempRwaN = squeeze(zeros(nBin));
    
    if isnan(stim(1))
        return
    end
    
    str1 = '['; str2 = '('; str3 = '[';
    binCount = 0;
    for jj=1:length(nBin)
        if binSpec.padding(jj) ~= 'i'
            binCount = binCount + 1;
            str1 = [str1 'b' num2str(binCount) ','];
            str2 = [str2 'binCenters{' num2str(jj) '},'];
            str3 = [str3 'b' num2str(binCount) '(:),'];
        end
    end
    str1 = [str1(1:end-1) ']'];
    str2 = [str2(1:end-1) ');'];
    str3 = [str3(1:end-1) '];'];
    
    eval([str1 ' = ndgrid' str2]);
    eval(['x = ' str3]);
    
    for ss=1:size(stim,1)
        betaRwa = [resp std_bin stim(ss,:)];
        betaRwaN = [1 std_bin stim(ss,:)];
        tempRwa = tempRwa + reshape(getGaussianNd(betaRwa,x,binSpec.padding,ico),size(tempRwaN));
        tempRwaN = tempRwaN + reshape(getGaussianNd(betaRwaN,x,binSpec.padding,ico),size(tempRwa));
    end
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
                cc = abs(x0(:,binCount)-m(ii));
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