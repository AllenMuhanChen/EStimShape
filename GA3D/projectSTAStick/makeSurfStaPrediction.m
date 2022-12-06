function pred = makeSurfStaPrediction(runId,binSpec,fullSetSta,sta,sta_shuff,surfFitParams,resp,selectedIds,data,is3d,lineage)
    %%
    selectIdx = getTopStim(resp,is3d);
    selectIdx = selectIdx(1:3);

    resp = nanmean(resp,2);
    resp = resp/max(resp(:));
    resp(~is3d) = [];
    surfFitParams(~is3d) = [];
    %%
%     hf = figure('pos',[181,1070,1160,183],'color','w');
%     
%     % row 1: predict full set from full set
%     % row 2: predict lin 2 from lin 1
%     % row 3: predict lin 1 from lin 2
%     % row 4: predict full set from linMult
%     % row ?: predict full set from shuffle full set
%     
%     % pred.full = plotPrediction(subplot(1,5,1),fullSetSta.surf,...
%     %             binSpec,surfFitParams,selectedIds,resp,'full',selectIdx);
% 	pred.l1s2 = plotPrediction([],sta(1).surf,...
%                 binSpec,surfFitParams(lineage==2),resp(lineage==2,:),[],'lin 1 sta with lin 2 stim',[]);
% 	pred.l2s1 = plotPrediction([],sta(2).surf,...
%                 binSpec,surfFitParams(lineage==1),resp(lineage==1,:),[],'lin 2 sta with lin 1 stim',[]);
	pred.mult = plotPrediction([],sta(1).surf.*sta(2).surf,...
                binSpec,surfFitParams,resp,selectedIds,'mult',selectIdx);
% 	pred.shuf = plotPrediction(subplot(1,5,5),sta_shuff(1).surf.*sta_shuff(2).surf,...
%                 binSpec,surfFitParams,resp,'shuffle',selectIdx);
            
    staMult   = sta(1).thresh .* sta(2).thresh;
	pred.filtMult = []; % plotPrediction([],staMult,binSpec,surfFitParams,resp,selectedIds,'filt mult',selectIdx);
    
%     screen2png(['plots/prediction/icostaPred6_' runId '_surfSta.png']);
%     close(hf)
end

function compResp = plotPrediction(h,sta,binSpec,stim,resp,selectedIds,titleStr,selectIdx)
    predResp = nan(size(resp));
    compResp = cell(size(resp));
    for ii=1:length(stim)
        ss = stim{ii}; % (selectedIds{ii},:)
        compResp{ii} = getPerComponentResp(squeeze(sta),ss,...
            binSpec.surf.padding,binSpec.surf.binCenters,binSpec.ico.s);
        predResp(ii) = max(compResp{ii});
    end
    compResp = cellfun(@(x) x./max(predResp(:)),compResp,'UniformOutput',false);
%     predResp = predResp/max(predResp(:));
%     plot(h,resp,predResp,'r.'); hold(h,'on');
%     if ~isempty(selectIdx)
%         plot(h,resp(selectIdx),predResp(selectIdx),'g.');
%     end
%     lm = fitlm(resp,predResp);
%     plot(0:0.1:1,lm.predict((0:0.1:1)'),'b','LineWidth',2);
%     fixPlot(h,[titleStr ': ' num2str(round(lm.Rsquared.Adjusted,3))])
end

function y = getPerComponentResp(sta,stim,padding,binCenters,ico)
    nBin = length(padding);
    nPts = size(stim,1);
    % s: full sphere, r: rotated hemi, z: normal, h: hemi, i: ignore, c: circular

    bin = nan(nPts,nBin);
    for ii=1:nBin
        if padding(ii) ~= 'i'
            if padding(ii) == 'c'
                [~,bin(:,ii)] = min(abs(circ_dist(repmat(binCenters{ii},nPts,1),repmat(stim(:,ii),1,length(binCenters{ii})))),[],2);
            elseif padding(ii) == 'z'
                [~,bin(:,ii)] = min(abs(repmat(binCenters{ii},nPts,1) - repmat(stim(:,ii),1,length(binCenters{ii}))),[],2);
            elseif padding(ii) == 's'
                norms = ico;
                norms = transpose(reshape(repmat(transpose(norms),nPts,1),3,nPts*size(ico,1)));

                v1 = [];
                [v1(:,1),v1(:,2),v1(:,3)] = sph2cart(stim(:,ii-1),stim(:,ii),1);
                v1 = repmat(v1,size(ico,1),1);

                dist = reshape(abs(dot(v1',norms')),nPts,80);
                [~,bin(:,ii)] = max(dist,[],2);
            elseif padding(ii) == 'r'

            elseif padding(ii) == 'h'

            end
            
        end    
    end
	bin(:,padding == 'i') = [];
    bin = mat2cell(bin,ones(nPts,1),6);
    bin = cellfun(@(x) ['sta(' strrep(strrep(num2str(x),'   ',','),'  ',',') ')'],bin,'UniformOutput',false);
    y = cellfun(@eval,bin);
end

function fixPlot(h,titleStr)
    h.LineWidth = 2; h.Color = 'w';
    h.XColor = 'k'; h.YColor = 'k';
    h.Box = 'on';
    h.XLim = [0 1]; h.YLim = [0 1];
    h.XTick = 0:0.5:1; h.YTick = 0:0.5:1;
    h.TickDir = 'out'; h.LineWidth = 2;

    h.FontSize = 12; h.FontName = 'Lato';

    h.XLabel.String = 'Response';
    h.XLabel.FontSize = 18; h.XLabel.FontName = 'Lato';
    h.YLabel.String = 'Prediction';
    h.YLabel.FontSize = 18; h.YLabel.FontName = 'Lato';

    ht = title(h,titleStr);
    ht.Color = 'k'; ht.FontSize = 20; ht.FontName = 'Lato';

    axis(h,'square');
end

function selectIdx = getTopStim(resp,is3d)
    resp(~is3d,:) = nan;
    [sortedResp,idx] = sort(nanmean(resp,2),'descend');
    idx(isnan(sortedResp)) = [];
    selectIdx = [idx(1:3); idx(end-2:end)];    
end