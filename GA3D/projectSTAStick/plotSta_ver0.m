function plotSta_ver0(runId,sta,sta_shuff,binSpec)
%     clear; close all; clc;
%     dataPath = '/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectSTAStick/data';
%     cell = '170508_r-45';
%     load([dataPath '/' cell '_sta.mat']);
%     load([dataPath '/' cell '_fit.mat']);
%     resp = nanmean(resp,2); resp = resp/max(resp);
        
%     linNum = 1;
%     
%     plotStaProjectionsPerComponent(binSpec,sta,linNum,resp,'s')
%     plotStaProjectionsPerComponent(binSpec,sta,linNum,resp,'r')
%     plotStaProjectionsPerComponent(binSpec,sta,linNum,resp,'t')
%     plotStaProjectionsPerComponent(binSpec,sta,linNum,resp,'sr')
%     plotStaProjectionsPerComponent(binSpec,sta,linNum,resp,'st')
    
     %% sta prediction/cross-validation
    % oppLin = 3-linNum;
    % figure('name','shaft')
    % sta(linNum).s(:) = sta(linNum).s(:)/max(sta(linNum).s(:));
    % subplot(221); validateSta(sta(linNum).s,{stimStruct(lineage == linNum).s},resp(lineage == linNum),binSpec.s); title('lin1 sta pred lin 1');
    % subplot(222); validateSta(sta(linNum).s,{stimStruct(lineage == oppLin).s},resp(lineage == oppLin),binSpec.s); title('lin1 sta pred lin 2');
    % subplot(223); validateSta(sta(oppLin).s,{stimStruct(lineage == linNum).s},resp(lineage == linNum),binSpec.s); title('lin2 sta pred lin 1');
    % subplot(224); validateSta(sta(oppLin).s,{stimStruct(lineage == oppLin).s},resp(lineage == oppLin),binSpec.s); title('lin2 sta pred lin 2');
    % 
    % figure('name','term')
    % sta(linNum).t(:) = sta(linNum).t(:)/max(sta(linNum).t(:));
    % subplot(221); validateSta(sta(linNum).t,{stimStruct(lineage == linNum).t},resp(lineage == linNum),binSpec.t); title('lin1 sta pred lin 1');
    % subplot(222); validateSta(sta(linNum).t,{stimStruct(lineage == oppLin).t},resp(lineage == oppLin),binSpec.t); title('lin1 sta pred lin 2');
    % subplot(223); validateSta(sta(oppLin).t,{stimStruct(lineage == linNum).t},resp(lineage == linNum),binSpec.t); title('lin2 sta pred lin 1');
    % subplot(224); validateSta(sta(oppLin).t,{stimStruct(lineage == oppLin).t},resp(lineage == oppLin),binSpec.t); title('lin2 sta pred lin 2');
    % 
    % figure('name','root')
    % sta(linNum).r(:) = sta(linNum).r(:)/max(sta(linNum).r(:));
    % subplot(221); validateSta(sta(linNum).r,{stimStruct(lineage == linNum).r},resp(lineage == linNum),binSpec.r); title('lin1 sta pred lin 1');
    % subplot(222); validateSta(sta(linNum).r,{stimStruct(lineage == oppLin).r},resp(lineage == oppLin),binSpec.r); title('lin1 sta pred lin 2');
    % subplot(223); validateSta(sta(oppLin).r,{stimStruct(lineage == linNum).r},resp(lineage == linNum),binSpec.r); title('lin2 sta pred lin 1');
    % subplot(224); validateSta(sta(oppLin).r,{stimStruct(lineage == oppLin).r},resp(lineage == oppLin),binSpec.r); title('lin2 sta pred lin 2');
    
    %% gauss test
    % binCenters = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.s.binEdges,'uniformoutput',false);
    % 
    % y = sta(linNum).s(:);
    % y = y/max(y);
    % [a1,a2,a3,a4,a5,a6,a7,a8] = ndgrid(binCenters{1},binCenters{2},binCenters{3},binCenters{4},binCenters{5},binCenters{6},binCenters{7},binCenters{8}); %#ok<ASGLU>
    % [b1,b2,b3,b4,b5,b6,b7,b8] = ind2sub(size(sta(linNum).s),find(y==1)); %#ok<ASGLU>
    % x = nan(length(y),8);
    % beta = nan(1,8);
    % for ii=1:8
    %     eval(['a' num2str(ii) ' = a' num2str(ii) '(:);']);
    %     eval(['x(:,ii) = a' num2str(ii) ';']);
    %     eval(['beta(ii) = binCenters{ii}(b' num2str(ii) ');'])
    %     eval(['clearvars a' num2str(ii) ' b' num2str(ii)]);
    % end
    % beta = [ones(1,8) beta];
    % options.Display = 'iter';
    % options.MaxIter = 80;
    % beta = nlinfit(x,y,@getGaussianNd,beta,options);
    % s = beta(1:8);
    % m = beta(9:16);
end
% 
% function y = getGaussianNd(beta,x0)
%     % beta = [s1 s2 s3 s4 s5 ... m1 m2 m3 m4 m5 ...]
%     % x0 = [x1 x2 x3 x4 x5 ...]
%     
%     n = size(x0,2);
%     
%     s = beta(1:1+n);
%     m = beta(1+n:end);
% 
%     c = zeros(size(x0,1),n);
%     for ii=1:n
%         c(:,ii) = ((x0(:,ii)-m(ii)).^2)/(2*s(ii)^2);
%     end
%     
%     b = 1/(2*pi*prod(s));
%     
%     y = b .* exp(-(sum(c,2)));
% end


function validateSta(sta,stim,resp,binSpec)
    predResp = nan(size(resp));
    for ss=1:length(stim)
        for cc=1:size(stim{ss},2)
            comp = stim{ss}(:,cc);
            str = '';
            for dd=1:length(binSpec.nBin)
                [~,binX] = histc(comp(dd),binSpec.binEdges{dd});
                binX(binX>binSpec.nBin(dd)) = binSpec.nBin(dd);
                bin(dd,:) = binX;
                str = [str num2str(binX) ','];
            end
            eval(['compResp(cc) = sta(' str(1:end-1) ');']);
        end
        predResp(ss) = max(compResp);
    end
    scatter(resp,predResp); hold on
    lm = fitlm(resp,predResp);
    int = lm.Coefficients.Estimate(1);
    slope = lm.Coefficients.Estimate(2);
    x = linspace(0,1,20);
    y = int + slope*x;
    line(x,y,'linewidth',2,'color','r')
    
end