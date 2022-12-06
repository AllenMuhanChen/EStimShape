function plotSta_ver1(runId,binSpec,sta,sta_shuff,fullSetSta)
    figure('pos',[276,460,2127,878]);
    
    ha = tight_subplot(5,8);
    ha = reshape(ha,8,5)';

    binCentersS  = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.s.binEdges,'uniformoutput',false);
    binCentersR  = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.r.binEdges,'uniformoutput',false);
    binCentersT  = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.t.binEdges,'uniformoutput',false);
    binCentersSR = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.sr.binEdges,'uniformoutput',false);
    binCentersST = cellfun(@(x) conv(x,[0.5 0.5],'valid'),binSpec.st.binEdges,'uniformoutput',false);
    
    linCols = {'r','b'};
    for linNum=1:2
        plotSubplot(sta(linNum).s,binCentersS,linCols{linNum},ha,1,8);
        plotSubplot(sta(linNum).r,binCentersR,linCols{linNum},ha,2,8);
        plotSubplot(sta(linNum).t,binCentersT,linCols{linNum},ha,3,6);
        plotSubplot(sta(linNum).sr,binCentersSR,linCols{linNum},ha,4,6);
        plotSubplot(sta(linNum).st,binCentersST,linCols{linNum},ha,5,6);
    end
    
    screen2png(['plots/dumb/dumb_' runId '.png']);
    
    clf; ha = tight_subplot(5,8); ha = reshape(ha,8,5)';
    
    plotSubplot(sta(1).s.*sta(2).s,binCentersS,'k',ha,1,8);
    plotSubplot(sta(1).r.*sta(2).r,binCentersR,'k',ha,2,8);
    plotSubplot(sta(1).t.*sta(2).t,binCentersT,'k',ha,3,6);
    plotSubplot(sta(1).sr.*sta(2).sr,binCentersSR,'k',ha,4,6);
    plotSubplot(sta(1).st.*sta(2).st,binCentersST,'k',ha,5,6);
    
    screen2png(['plots/dumb/dumb_' runId '_linMult.png']);
    
    clf; ha = tight_subplot(5,8); ha = reshape(ha,8,5)';
    
    plotSubplot(fullSetSta.s,binCentersS,'k',ha,1,8);
    plotSubplot(fullSetSta.r,binCentersR,'k',ha,2,8);
    plotSubplot(fullSetSta.t,binCentersT,'k',ha,3,6);
    plotSubplot(fullSetSta.sr,binCentersSR,'k',ha,4,6);
    plotSubplot(fullSetSta.st,binCentersST,'k',ha,5,6);
    
    screen2png(['plots/dumb/dumb_' runId '_fullSet.png']);
    
    clf; ha = tight_subplot(5,8); ha = reshape(ha,8,5)';
    
    scaleS = max(sta(1).s(:).*sta(2).s(:));
    scaleR = max(sta(1).r(:).*sta(2).r(:));
    scaleT = max(sta(1).t(:).*sta(2).t(:));
    scaleSR = max(sta(1).sr(:).*sta(2).sr(:));
    scaleST = max(sta(1).st(:).*sta(2).st(:));
    
    plotSubplot(sta_shuff(1).s.*sta_shuff(2).s,binCentersS,'k',ha,1,8,scaleS);
    plotSubplot(sta_shuff(1).r.*sta_shuff(2).r,binCentersR,'k',ha,2,8,scaleR);
    plotSubplot(sta_shuff(1).t.*sta_shuff(2).t,binCentersT,'k',ha,3,6,scaleT);
    plotSubplot(sta_shuff(1).sr.*sta_shuff(2).sr,binCentersSR,'k',ha,4,6,scaleSR);
    plotSubplot(sta_shuff(1).st.*sta_shuff(2).st,binCentersST,'k',ha,5,6,scaleST);
    
    screen2png(['plots/dumb/dumb_' runId '_shuff.png']);
    
end

function plotSubplot(sta,binCenters,linCol,ha,rowNum,nCols,scale)
    
    staMax = max(sta(:));
    if ~exist('scale','var')
        scale = staMax;
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
    for ii=1:nCols
        if ii~=2 && ii~=5
            str = '(';
            for jj=1:nCols
                if ii==jj || (ii==1 && jj==2) || (ii==4 && jj==5)
                    str = [str ':,'];
                else
                    str = [str 'b' num2str(jj) ','];
                end     
            end
            str = [str(1:end-1) ');'];

            eval(['ss = sta' str]); ss = squeeze(ss);
            if size(ss,2) > 1
                if linCol == 'r'
                    plotSphereAsImage(ha(rowNum,ii),binCenters{1},binCenters{2},ss);
                    set(ha(rowNum,ii),'CLim',[0 scale])
                else
                    plotSphereAsImage(ha(rowNum,ii+1),binCenters{1},binCenters{2},ss);
                    set(ha(rowNum,ii+1),'CLim',[0 scale])
                end
            else
                plot(ha(rowNum,ii),binCenters{ii},ss,linCol); hold(ha(rowNum,ii),'on')
                set(ha(rowNum,ii),'ylim',[0 scale]);
            end
        end
    end
end

function plotSphereAsImage(h,th_centers,ph_centers,intensity)
    [th,ph] = meshgrid(th_centers,ph_centers);
    [thq,phq] = meshgrid(linspace(-pi,pi,256),linspace(-pi/2,pi/2,128));
    ssq = interp2(th,ph,intensity',thq,phq,'spline');
    
    imagesc(ssq,'parent',h);
    set(h,'xtick',[1 64:64:256],'ytick',[1 64 128]);
    set(h,'XTickLabel',{'-\pi' '-\pi/2' '0' '\pi/2' '\pi'});
    set(h,'YTickLabel',{'-\pi/2' '0' '\pi/2'});
    
%     [~,maxInd] = max(ssq(:));
%     beta = fitAny([thq(:) phq(:)],ssq(:),@getGaussian2d,[thq(maxInd) phq(44) pi/4 pi/4]);
%     figure;
%     drawEllipse(beta(4),beta(2),0,beta(3),beta(1),'r',100,gca)
%     set(gca,'xlim',[-pi pi],'ylim',[-pi/2 pi/2]); axis equal;
end
