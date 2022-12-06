function pred = makeStaPrediction(runId,binSpec,fullSetSta,sta,sta_shuff,stimStruct,resp,data,is3d,lineage,doPlot)
    %%
    % [~,selectIdx,~,~,~] = getTopStim(resp,data,is3d);
    % selectIdx = selectIdx(1:3);
    selectIdx = [];
    
    resp = nanmean(resp,2);
    resp = resp/max(resp(:));
    resp(~is3d) = [];
    stimStruct(~is3d) = [];
    
    %%
%     hf = figure('pos',[181,302,1160,951],'color','w');
    
    % row 1: predict full set from full set
    % row 2: predict lin 2 from lin 1
    % row 3: predict lin 1 from lin 2
    % row 4: predict full set from linMult
    % row ?: predict full set from shuffle full set
    
    for ii=1:3
        switch ii
            case 1; % plotPrediction(subplot(4,5,1),fullSetSta.s,binSpec.s,{stimStruct.s},resp,binSpec.s.binCenters,binSpec.ico,'s',selectIdx);
                    % plotPrediction(subplot(4,5,6),sta(1).s,binSpec.s,{stimStruct(lineage==2).s},resp(lineage==2,:),binSpec.s.binCenters,binSpec.ico,'s',[]);
                    % plotPrediction(subplot(4,5,11),sta(2).s,binSpec.s,{stimStruct(lineage==1).s},resp(lineage==1,:),binSpec.s.binCenters,binSpec.ico,'s',[]);
                    pred.s = plotPrediction([],sta(1).s.*sta(2).s,binSpec.s,{stimStruct.s},resp,binSpec.s.binCenters,binSpec.ico,'s',selectIdx);
                    pred.s_1 = plotPrediction([],sta(1).s,binSpec.s,{stimStruct.s},resp,binSpec.s.binCenters,binSpec.ico,'s',selectIdx);
                    pred.s_2 = plotPrediction([],sta(2).s,binSpec.s,{stimStruct.s},resp,binSpec.s.binCenters,binSpec.ico,'s',selectIdx);
                    % plotPrediction(subplot(256),sta_shuff.s,binSpec.s,{stimStruct.s},resp,binSpec.s.binCenters,binSpec.ico,'s',selectIdx);
            case 2; % plotPrediction(subplot(4,5,2),fullSetSta.r,binSpec.r,{stimStruct.r},resp,binSpec.r.binCenters,binSpec.ico,'r',selectIdx);
                    % plotPrediction(subplot(4,5,7),sta(1).r,binSpec.r,{stimStruct(lineage==2).r},resp(lineage==2,:),binSpec.r.binCenters,binSpec.ico,'r',[]);
                    % plotPrediction(subplot(4,5,12),sta(2).r,binSpec.r,{stimStruct(lineage==1).r},resp(lineage==1,:),binSpec.r.binCenters,binSpec.ico,'r',[]);
                    pred.r = plotPrediction([],sta(1).r.*sta(2).r,binSpec.r,{stimStruct.r},resp,binSpec.r.binCenters,binSpec.ico,'r',selectIdx);
                    pred.r_1 = plotPrediction([],sta(1).r,binSpec.r,{stimStruct.r},resp,binSpec.r.binCenters,binSpec.ico,'r',selectIdx);
                    pred.r_2 = plotPrediction([],sta(2).r,binSpec.r,{stimStruct.r},resp,binSpec.r.binCenters,binSpec.ico,'r',selectIdx);
%                     plotPrediction(subplot(257),sta_shuff.r,binSpec.r,{stimStruct.r},resp,binSpec.r.binCenters,binSpec.ico,'r',selectIdx);
            case 3; % pred.t = plotPrediction(subplot(4,5,3),fullSetSta.t,binSpec.t,{stimStruct.t},resp,binSpec.t.binCenters,binSpec.ico,'t',selectIdx);
                    % plotPrediction(subplot(4,5,8),sta(1).t,binSpec.t,{stimStruct(lineage==2).t},resp(lineage==2,:),binSpec.t.binCenters,binSpec.ico,'t',[]);
                    % plotPrediction(subplot(4,5,13),sta(2).t,binSpec.t,{stimStruct(lineage==1).t},resp(lineage==1,:),binSpec.t.binCenters,binSpec.ico,'t',[]);
                    pred.t = plotPrediction([],sta(1).t.*sta(2).t,binSpec.t,{stimStruct.t},resp,binSpec.t.binCenters,binSpec.ico,'t',selectIdx);
                    pred.t_1 = plotPrediction([],sta(1).t,binSpec.t,{stimStruct.t},resp,binSpec.t.binCenters,binSpec.ico,'t',selectIdx);
                    pred.t_2 = plotPrediction([],sta(2).t,binSpec.t,{stimStruct.t},resp,binSpec.t.binCenters,binSpec.ico,'t',selectIdx);
%                     plotPrediction(subplot(258),sta_shuff.t,binSpec.t,{stimStruct.t},resp,binSpec.t.binCenters,binSpec.ico,'t',selectIdx);
%             case 4; plotPrediction(subplot(4,5,4),fullSetSta.sr,binSpec.sr,{stimStruct.sr},resp,binSpec.sr.binCenters,binSpec.ico,'sr',selectIdx);
%                     plotPrediction(subplot(4,5,9),sta(1).sr,binSpec.sr,{stimStruct(lineage==2).sr},resp(lineage==2,:),binSpec.sr.binCenters,binSpec.ico,'sr',[]);
%                     plotPrediction(subplot(4,5,14),sta(2).sr,binSpec.sr,{stimStruct(lineage==1).sr},resp(lineage==1,:),binSpec.sr.binCenters,binSpec.ico,'sr',[]);
%                     pred.sr = plotPrediction(subplot(4,5,19),sta(1).sr.*sta(2).sr,binSpec.sr,{stimStruct.sr},resp,binSpec.sr.binCenters,binSpec.ico,'sr',selectIdx);
% %                     plotPrediction(subplot(259),sta_shuff.sr,binSpec.sr,{stimStruct.sr},resp,binSpec.sr.binCenters,binSpec.ico,'sr',selectIdx);
%             case 5; plotPrediction(subplot(4,5,5),fullSetSta.st,binSpec.st,{stimStruct.st},resp,binSpec.st.binCenters,binSpec.ico,'st',selectIdx);
%                     plotPrediction(subplot(4,5,10),sta(1).st,binSpec.st,{stimStruct(lineage==2).st},resp(lineage==2,:),binSpec.st.binCenters,binSpec.ico,'st',[]);
%                     plotPrediction(subplot(4,5,15),sta(2).st,binSpec.st,{stimStruct(lineage==1).st},resp(lineage==1,:),binSpec.st.binCenters,binSpec.ico,'st',[]);
%                     pred.st = plotPrediction(subplot(4,5,20),sta(1).st.*sta(2).st,binSpec.st,{stimStruct.st},resp,binSpec.st.binCenters,binSpec.ico,'st',selectIdx);
% %                     plotPrediction(subplot(4,5,10),sta_shuff.st,binSpec.st,{stimStruct.st},resp,binSpec.st.binCenters,binSpec.ico,'st',selectIdx);
        end
    end
    
%     screen2png(['plots/prediction/icostaPred2_' runId '_fullSta.png']);
%     close(hf)
end

function compResp = plotPrediction(h,sta,binSpec,stim,resp,binCenters,ico,titleStr,selectIdx)
    predResp = nan(size(resp));
    compResp = cell(size(resp));
    for ii=1:length(stim)
        compResp{ii} = getPerComponentResp(sta,stim{ii},binSpec.padding,binCenters,ico);
        predResp(ii) = max(compResp{ii});
    end
    compResp = cellfun(@(x) x./max(predResp(:)),compResp,'UniformOutput',false);
    predResp = predResp/max(predResp(:));
%     plot(h,resp,predResp,'r.'); hold(h,'on');
%     if ~isempty(selectIdx)
%         plot(h,resp(selectIdx),predResp(selectIdx),'g.');
%     end
%     lm = fitlm(resp,predResp);
%     plot(0:0.1:1,lm.predict((0:0.1:1)'),'b','LineWidth',2);
%     fixPlot(h,[titleStr ': ' num2str(round(lm.Rsquared.Adjusted,3))])
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