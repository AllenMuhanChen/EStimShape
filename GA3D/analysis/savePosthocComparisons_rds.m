% function savePosthocComparisons_rds
    %% save or load data
    close all; clear; clc
    if ~exist('plots/population/rds_auc.mat','file')
        [auc,resp,respFull,cell] = doAllCells();
        stats = getAnova(respFull);
        save('plots/population/rds_auc.mat','auc','resp','respFull','cell','stats');
    else
        load('plots/population/rds_auc.mat','auc','resp','respFull','cell','stats');
    end
    
    % for plotting ga scores for these cells
    load('plots/population/ids.mat','population');
    load('/Users/ramanujan/Documents/hopkins/papers/1b_phys_2p/ep/fig 2/population/shuffScore_percell.mat','sig2d','sig3d','score')
    population = population([population.nGen] > 1);
    cCells = ismember([population.runNum],[cell.runNum]);
    sig2d_ga = sig2d(cCells,1);
    sig3d_ga = sig3d(cCells,1);
    population = population(cCells);
    
    %% plots
    % doPlots_1(cell,resp,auc);
    % doPlots_2(cell,resp,auc);
    % doPlots_3(cell,resp,auc);
    % doPlots_4(cell,resp,auc);
    
    % screen2png('plots/population/rds_auc.png')
    
    %% example stim
    % plotCells = [3 5 7 8];
    % stimPerCell = [6 1 4 3];
    % actualStimNums = [2 1; 1 1; 1 25; 1 17];
    % rr = resp(plotCells);
    % rrf = respFull(plotCells);
    % ss = stats(plotCells);
    % cc = cell(plotCells);
    % 
    % vol = []; pla = []; 
    % for ii=1:length(plotCells)
    %     datV = []; datP = []; grp = [];
    %     for depthId=1:3
    %         vol{depthId} = rrf(ii).vol{stimPerCell(ii),depthId} ./ max(rr(ii).max);
    %         pla{depthId} = rrf(ii).pla{stimPerCell(ii),depthId} ./ max(rr(ii).max);
    % 
    %         datV = [datV; vol{depthId}'];
    %         datP = [datP; pla{depthId}'];
    % 
    %         grp = [grp; depthId*ones(length(vol{depthId}),1)];
    %     end
    % 
    %     cla; set(gcf,'color','w');
    %     errorbar(1:3,grpstats(datV,grp,'mean'),grpstats(datV,grp,'sem'),'LineWidth',2,'color',[0 0.65 1]); hold on;
    %     errorbar(1:3,grpstats(datP,grp,'mean'),grpstats(datP,grp,'sem'),'LineWidth',2,'color',[1 0.65 0])
    %     plot(1:3,grpstats(datV,grp,'mean'),'.','MarkerSize',30,'color',[0 0.65 1]);
    %     plot(1:3,grpstats(datP,grp,'mean'),'.','MarkerSize',30,'color',[1 0.65 0]);
    %     fixPlot(gca,'Depth','Norm. Response')
    %     fileName = [num2str(cc(ii).prefix) '_r-' num2str(cc(ii).runNum)];
    %     axis([0.5 3.5 0 1.5]); axis square; set(gca,'xtick',1:3,'YTick',0:0.5:1)
    % %         screen2png(['plots/population/rdsCell_' fileName '.png'])
    % end
    
    %% regen stim?
    % for ii=1:4
    %     fileName = [num2str(cc(ii).prefix) '_r-' num2str(cc(ii).runNum)];
    %     rdsGenNum = cc(ii).nGen-cc(ii).nPostHoc+find(cc(ii).postHocIds == 4,1,'last');
    %     load(['/Users/ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectMaskedGA3D/stim/dobby/' fileName '_g-' num2str(rdsGenNum) '/stimParams.mat']);
    % 
    %     fid = fopen(['/Users/ramanujan/Dropbox/Documents/Hopkins/Thesis/Papers/Cell2019/fig/rds/manual/spec/' num2str(ii) '_spec.xml'],'w');
    %     fwrite(fid,stimuli{actualStimNums(ii,1),actualStimNums(ii,2)}.shape.mstickspec);
    %     fclose(fid);
    % end
    
    %% randomization test
    sig3d = []; sig2d = [];
    for ii=1:length(resp)
        ii
        bDepth = maxind([mean(resp(ii).vol) mean(resp(ii).pla)]);
        bDepth(bDepth>size(resp(ii).vol,2)) = bDepth - size(resp(ii).vol,2);
        bDepth = 1:size(resp(ii).vol,2);
        
        bStim = maxind([mean(resp(ii).vol,2);mean(resp(ii).pla,2)]);
        bStim(bStim>size(resp(ii).vol,1)) = bStim - size(resp(ii).vol,1);
        % bStim = 1:size(respFull(ii).vol,1);
        
        vol = cell2mat(respFull(ii).vol(bStim,bDepth));
        pla = cell2mat(respFull(ii).pla(bStim,bDepth));
        for ss=1:length(bStim)
            sc_v(ss) = mean(vol(ss,:)); % across reps
            sc_p(ss) = mean(pla(ss,:)); % across reps
            
            temp = [vol(ss,:) pla(ss,:)];
            
            for rr=1:10000
                temp = temp(randperm(length(temp)));
                sc_sh_v(ss,rr) = mean(temp(1:length(temp)/2));
                sc_sh_p(ss,rr) = mean(temp(1+length(temp)/2 : end));
            end
        end
        sc(ii) = (mean(sc_v)-mean(sc_p))./max(mean(sc_v),mean(sc_p));
        if length(bStim) == 1
            sc_sh = (sc_sh_v-sc_sh_p)./max([sc_sh_v;sc_sh_p]);
        else
            sc_sh = (mean(sc_sh_v)-mean(sc_sh_p))./max([mean(sc_sh_v);mean(sc_sh_p)]);
        end
        upperC = prctile(sc_sh,100-2.5);
        lowerC = prctile(sc_sh,2.5);
        sig3d(ii) = sc(ii)>upperC;
        sig2d(ii) = sc(ii)<lowerC;
    end
    
    %% histogram
    clf;
    set(gcf,'color','w','pos',[118,446,1025,361]);    
    
    nBin = 11;
    lim = 1;
    ylim = 8;
    subplot(131);
    h = histogram(sc,linspace(-lim,lim,nBin)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [0.5 0.5 0.5]; h.FaceAlpha = 1; hold on;
    h = histogram(sc(sig3d & sc > 0),linspace(-lim,lim,nBin)); h.EdgeColor = 'none'; h.FaceColor = [1 0.6 0.1]; h.FaceAlpha = 1; 
    h = histogram(sc(sig2d & sc < 0),linspace(-lim,lim,nBin)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.6 1]; h.FaceAlpha = 1; 
    legStr = {'all 21' ['3d ' num2str(sum(sig3d & sc > 0)) '/' num2str(sum(sc > 0))] ['2d ' num2str(sum(sig2d & sc < 0)) '/' num2str(sum(sc < 0))]};
    fixPlot(gca,[-lim lim],[0 ylim],'solid index','count',-lim:0.5:lim,0:2:ylim,'rds',legStr)
    axis square; grid on;

    subplot(132);
    sc_ga = [cell.score_3d];
    h = histogram(sc_ga,linspace(-1,1,nBin)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [0.5 0.5 0.5]; h.FaceAlpha = 1; hold on;
    h = histogram(sc_ga(sc_ga>sig3d_ga' & sc_ga > 0),linspace(-1,1,nBin)); h.EdgeColor = 'none'; h.FaceColor = [1 0.6 0.1]; h.FaceAlpha = 1; 
    h = histogram(sc_ga(sc_ga<sig2d_ga' & sc_ga < 0),linspace(-1,1,nBin)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.6 1]; h.FaceAlpha = 1; 
    legStr = {'all 21' ['3d ' num2str(sum(sc_ga>sig3d_ga' & sc_ga > 0)) '/' num2str(sum(sc_ga > 0))] ['2d ' num2str(sum(sc_ga<sig2d_ga' & sc_ga < 0)) '/' num2str(sum(sc_ga < 0))]};
    fixPlot(gca,[-1 1],[0 8],'solid index','count',-1:0.5:1,0:2:8,'ga',legStr)

    sigGA = (sc_ga>sig3d_ga' & sc_ga > 0) | (sc_ga<sig2d_ga' & sc_ga < 0);
    sigRd = (sig3d & sc > 0) | (sig2d & sc < 0);
    sig = sum([sigGA(:)*2 sigRd(:)],2)+1;
    cols = [0.5 0.5 0.5; 0.8 0.4 0.2; 0.2 0.3 0.8; 0.7 0.3 0.7];
    cols = cols(sig,:);
    
    subplot(133);
    h = scatter(sc_ga,sc,800,cols,'marker','.'); hold on; % [0.6 0.6 0.6]
    fixPlot(gca,[-1 1],[-1 1],'solid index (ga)','solid index (rds)',-1:0.5:1,-1:0.5:1,'rds vs ga')
    ht = text(-0.8,-0.6,'rds','color',[0.8 0.4 0.2],'FontName','lato','FontSize',12);
    ht = text(-0.8,-0.72,'ga','color',[0.2 0.3 0.8],'FontName','lato','FontSize',12);
    ht = text(-0.8,-0.86,'both','color',[0.8 0.3 0.8],'FontName','lato','FontSize',12);
    
    
    
%     screen2png('plots/population/rds_cdf_hist_randTest_bStim.png');
%     screen2png('~/Desktop/rds_cdf_hist_randTest_bStim.png');
    
% end

function doPlots_1(cell,resp,auc)
    figure('color','w'); % ,'pos',[310,887,2202,440])
    
    % for 3d pref score colors
    cols = parula(256);
    colspace = linspace(-1,1,256);
    
    %% plot all stimuli and color code by 3d score from GA
    subplot(221);
    line([0 3],[0 3],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        plot(auc(ii).vol,auc(ii).pla,'.','MarkerSize',20,'color',cols(col_idx,:))
    end
    legend('Location','northeastoutside'); 
    fixPlot(gca,'3D AUC','2D AUC','AUC (depth) for 3D vs 2D RDS'); % {'Real cells' 'Best corresponding DCN cells'})    
    axis square
    
    %% plot mean across all stimuli
    subplot(222);
    line([0 3],[0 3],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        avgAuc_3d = mean(auc(ii).vol); semAuc_3d = std(auc(ii).vol)/sqrt(length(auc(ii).vol));
        avgAuc_2d = mean(auc(ii).pla); semAuc_2d = std(auc(ii).pla)/sqrt(length(auc(ii).pla));
        
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        
        linWid = [avgAuc_3d - semAuc_3d avgAuc_3d + semAuc_3d];
        line([linWid(1) linWid(2)],[avgAuc_2d avgAuc_2d],'linewidth',2,'color',cols(col_idx,:))
        linWid = [avgAuc_2d - semAuc_2d avgAuc_2d + semAuc_2d];
        line([avgAuc_3d avgAuc_3d],[linWid(1) linWid(2)],'linewidth',2,'color',cols(col_idx,:))
        
        plot(avgAuc_3d,avgAuc_2d,'.','MarkerSize',20,'color',cols(col_idx,:))
    end
    fixPlot(gca,'3D AUC','2D AUC','Mean AUC across stimuli for each cell'); % {'Real cells' 'Best corresponding DCN cells'})    
    axis square
    
    %% plot only max AUC-difference stimuli per cell
    subplot(223);
    line([0 3],[0 3],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        [~,idx] = max(abs(auc(ii).vol - auc(ii).pla));
        plot(auc(ii).vol(idx),auc(ii).pla(idx),'.','MarkerSize',20,'color',cols(col_idx,:))
    end
    fixPlot(gca,'3D AUC','2D AUC','AUCs for the highest difference AUC-stimulus'); % {'Real cells' 'Best corresponding DCN cells'})    
    axis square
    
    %% plot response weighted means and color code as per 3d score from GA
    subplot(224);
    line([0 3],[0 3],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        wts = resp(ii).max/max(resp(ii).max);
        plot(auc(ii).vol.*wts,auc(ii).pla.*wts,'.','MarkerSize',10,'color',[0.7 0.7 0.7])
    end
    for ii=1:length(auc)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        wts = resp(ii).max/max(resp(ii).max);
        avgAuc_3d = mean(auc(ii).vol.*wts); semAuc_3d = std(auc(ii).vol.*wts)/sqrt(length(auc(ii).vol));
        avgAuc_2d = mean(auc(ii).pla.*wts); semAuc_2d = std(auc(ii).pla.*wts)/sqrt(length(auc(ii).pla));
        
        linWid = [avgAuc_3d - semAuc_3d avgAuc_3d + semAuc_3d];
        line([linWid(1) linWid(2)],[avgAuc_2d avgAuc_2d],'linewidth',2,'color',cols(col_idx,:))
        linWid = [avgAuc_2d - semAuc_2d avgAuc_2d + semAuc_2d];
        line([avgAuc_3d avgAuc_3d],[linWid(1) linWid(2)],'linewidth',2,'color',cols(col_idx,:))
        
        plot(avgAuc_3d,avgAuc_2d,'.','MarkerSize',30,'color',cols(col_idx,:))
    end
    fixPlot(gca,'3D AUC','2D AUC','Response-weighted mean AUC across stimuli'); % {'Real cells' 'Best corresponding DCN cells'})    
    axis square
end

function doPlots_2(cell,resp,auc)
    figure('color','w');
    
    % for 3d pref score colors
    cols = parula(256);
    colspace = linspace(-1,1,256);
    
    %% plot only AUC for max response stimuli per cell
    subplot(221);
    line([0 3],[0 3],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        [~,idx] = max(max([resp(ii).vol;resp(ii).pla],[],2));
        stimIds = repmat(1:length(auc(ii).vol),1,2);
        idx = stimIds(idx);
        
        plot(auc(ii).vol(idx),auc(ii).pla(idx),'.','MarkerSize',20,'color',cols(col_idx,:))
    end
    fixPlot(gca,'3D AUC','2D AUC','AUCs for the max response stim'); % {'Real cells' 'Best corresponding DCN cells'})    
    axis square
    
    %% plot the average 3d response and average 2d response
    subplot(222);
    line([0 15],[0 15],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        plot(mean(resp(ii).vol(:)),mean(resp(ii).pla(:)),'.','MarkerSize',20,'color',cols(col_idx,:))
    end
    fixPlot(gca,'Mean 3D Resp','Mean 3D Resp','Mean 3d and 2d responses across // all stimuli and conditions'); % {'Real cells' 'Best corresponding DCN cells'})    
    axis square
    
    %% 
    subplot(223);
    line([0 3],[0 3],'linewidth',2,'color','k'); hold on;
    for ii=1:length(auc)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        [~,idx] = max(max(resp(ii).vol,[],2));
        plot(auc(ii).vol(idx),auc(ii).pla(idx),'.','MarkerSize',20,'color',cols(col_idx,:))
    end
    fixPlot(gca,'3D AUC','2D AUC','AUCs for the highest response 3D stim');
    axis square
    
    %%
    subplot(224);
    for ii=1:length(auc)
        [~,idx] = max(max(resp(ii).vol,[],2));
        toPlot(ii) = auc(ii).vol(idx) - auc(ii).pla(idx);
    end
    h = histogram(toPlot,10,'Normalization','probability'); h.LineWidth = 2;
    fixPlot(gca,'AUC Difference','Probability','AUC difference for the highest response 3D stim');
    axis square
end

function doPlots_3(cell,resp,auc)
    figure('color','w');
    
    %% plot a histogram of the max depth and stim
    subplot(221);
    for ii=1:length(auc)
        [~,stim_idx] = max(max([resp(ii).vol;resp(ii).pla],[],2));
        if stim_idx <= length(auc(ii).vol)
            [~,depth_idx] = max(resp(ii).vol(stim_idx,:));
        else
            stimIds = repmat(1:length(auc(ii).vol),1,2);
            stim_idx = stimIds(stim_idx);
            [~,depth_idx] = max(resp(ii).pla(stim_idx,:));
        end
        
        max_resp = max(resp(ii).max);
        
        toPlot(ii) = (resp(ii).vol(stim_idx,depth_idx) - resp(ii).pla(stim_idx,depth_idx))/max_resp;
    end
    h = histogram(toPlot,10); h.LineWidth = 2;
    fixPlot(gca,'Norm diff resp (3d-2d/max)','Cell count','For best stim, best disparity');
    
    %% plot a histogram of the middle depth and stim
    subplot(222);
    for ii=1:length(auc)
        [~,stim_idx] = max(max([resp(ii).vol;resp(ii).pla],[],2));
        stimIds = repmat(1:length(auc(ii).vol),1,2);
        stim_idx = stimIds(stim_idx);
        depth_idx = (size(resp(ii).vol,2) + 1)/2;
        if ~isinteger(depth_idx); depth_idx = 2; end
        max_resp = max(resp(ii).max);
        
        toPlot(ii) = (resp(ii).vol(stim_idx,depth_idx) - resp(ii).pla(stim_idx,depth_idx))/max_resp;
    end
    h = histogram(toPlot,20,'BinEdges',linspace(-1,1,17)); h.LineWidth = 2;
    centers = (h.BinEdges(1:end-1) + h.BinEdges(2:end))/2;
    vals = getGaussian([5 mean(toPlot) std(toPlot)],linspace(-1,1,201));
    hold on; plot(linspace(-1,1,201),vals,'LineWidth',3,'color','r');
    set(gca,'XLim',[-1 1]);
    fixPlot(gca,'Norm diff resp (3d-2d/max)','Cell count','For best stim, middle disparity');
    
    %% plot a histogram of the max depth but eliminate high disparity cells
    subplot(223);
    count = 0;
    toPlot = [];
    for ii=1:length(auc)
        [~,stim_idx] = max(max([resp(ii).vol;resp(ii).pla],[],2));
        stimIds = repmat(1:length(auc(ii).vol),1,2);
        stim_idx = stimIds(stim_idx);
        % max_resp = max(resp(ii).max);
        
        % ~kstest(resp(ii).vol(stim_idx,:)) || ~kstest(resp(ii).pla(stim_idx,:))
        
        sortResp_vol = sort(resp(ii).vol(stim_idx,:),'desc');
        sortResp_pla = sort(resp(ii).pla(stim_idx,:),'desc');
        
        if (sortResp_vol(2) > 0.6*sortResp_vol(1)) && (sortResp_pla(2) > 0.6*sortResp_pla(1))
            count = count + 1;
            toPlot(count) = auc(ii).vol(stim_idx) - auc(ii).pla(stim_idx);
            if toPlot(count) > 0
                figure
                plot(resp(ii).vol(stim_idx,:)); hold on;
                plot(resp(ii).pla(stim_idx,:));
                cell(ii).runNum
            end
        end
    end
    h = histogram(toPlot,20,'BinEdges',linspace(-1,1,17)); h.LineWidth = 2;
%     centers = (h.BinEdges(1:end-1) + h.BinEdges(2:end))/2;
%     vals = getGaussian([5 mean(toPlot) std(toPlot)],linspace(-1,1,201));
%     hold on; plot(linspace(-1,1,201),vals,'LineWidth',3,'color','r');
    set(gca,'XLim',[-1 1]);
    fixPlot(gca,'AUC 3D - AUC 2D','Cell count','For best stim, only non-disparity cells');
    
end

function doPlots_4(cell,resp,auc)
    figure('color','w');
    
    % for 3d pref score colors
    cols = parula(256);
    colspace = linspace(-1,1,256);
    
    %% plot highest resp for 3d against 
    subplot(221);
    line([0 35],[0 35],'linewidth',2,'color','k'); hold on;
    for ii=1:length(cell)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        
        plot(max(resp(ii).vol(:)),max(resp(ii).pla(:)),...
            '.','MarkerSize',20,'color',cols(col_idx,:)); hold on;
        
        if max(resp(ii).vol(:)) > max(resp(ii).pla(:))
            sc(ii) = (max(resp(ii).vol(:)) - max(resp(ii).pla(:))) / max(resp(ii).vol(:));
        else
            sc(ii) = (max(resp(ii).vol(:)) - max(resp(ii).pla(:))) / max(resp(ii).pla(:));
        end
        
        sc2(ii) = resp(ii).score;
        
        % if mean(resp(ii).vol(:)) > mean(resp(ii).pla(:))
        %     sc2(ii) = (mean(resp(ii).vol(:)) - mean(resp(ii).pla(:))) / mean(resp(ii).vol(:));
        % else
        %     sc2(ii) = (mean(resp(ii).vol(:)) - mean(resp(ii).pla(:))) / mean(resp(ii).pla(:));
        % end
    end
%     fixPlot(gca,'Max 3D Resp','Max 3D Resp','Max 3d and 2d responses across // all stimuli and conditions');
    axis equal; axis square; 
    
    subplot(222);
    h = cdfplot(sc); h.LineWidth = 2;
%     fixPlot(gca,'3D Pref Score','Cell count','3d pref score based on max resp to 3d and 2d stim');
    set(gca,'XLim',[-0.5 0.5]);
    axis square; 
    
    subplot(223);
    h = cdfplot(sc2); h.LineWidth = 2;
%     fixPlot(gca,'3D Pref Score','Cell count','3d pref score based on mean resp to all 3d and 2d stim');
    set(gca,'XLim',[-0.5 0.5]);
    axis square; 
end

function tabl = getAnova(respFull)
    for ii=1:length(respFull)
        resp_3d = respFull(ii).vol;
        resp_2d = respFull(ii).pla;
        
        nStim = size(resp_3d,1);
        nDepths = size(resp_3d,2);
        nReps = size(resp_3d,3);
        
        groups = []; data = [];
        for ss=1:nStim
            for dd=1:nDepths
                nReps = length(resp_3d{ss,dd});
                
                c1 = ss*ones(2*nReps,1);
                c2 = [ones(nReps,1); 2*ones(nReps,1)];
                c3 = dd*ones(2*nReps,1);

                dat = [resp_3d{ss,dd}' ; resp_2d{ss,dd}'];
                
                groups = [groups; c1 c2 c3];
                data = [data; dat];
            end
        end
        [~,tabl{ii}] = anovan(data,groups,'display','off');
    end
end

function [auc,resp,respFull,cell] = doAllCells()
    load('plots/population/ids.mat','population');
    count = 1;
    for cc=1:length(population)
        if sum(population(cc).postHocIds == 4) > 0
            filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
            disp([num2str(count) ': ' num2str(cc) ': ' filePrefix]);
            [auc_t,resp_t,respFull_t] = doSingleCell(num2str(population(cc).prefix),population(cc).runNum,population(cc).nGen,population(cc).nPostHoc,population(cc).postHocIds,40,population(cc).monkeyId,cc<100); % allDCNCells(cc).bestCellResp);
            auc(count) = auc_t;
            resp(count) = resp_t;
            respFull(count) = respFull_t;
            cell(count) = population(cc);
            count = count + 1;
        end
    end
end

function [auc,resp,respFull] = doSingleCell(prefix,runNum,nGen,nPosthocs,postHocIds,nStim,monkeyId,meanFirstTwo)
    getPaths;
    
    postHocGens = nGen-nPosthocs+1 : nGen;
    postHocGens = postHocGens(postHocIds == 4);
    
    folderName = [prefix '_r-' num2str(runNum)];

    genResp = cell(1,length(postHocGens));
    for genNum=1:length(postHocGens)
        genId = postHocGens(genNum);
        fullFolderName = [folderName '_g-' num2str(genId)];

        rData = load([respPath '/' fullFolderName '/resp.mat']);
        sData = load([stimPath '/' fullFolderName '/stimParams.mat']);
        
        im1 = [analysisPath '/plots/' folderName '/' fullFolderName '/' fullFolderName '_l-1_allStim.png'];
        im2 = [analysisPath '/plots/' folderName '/' fullFolderName '/' fullFolderName '_l-2_allStim.png'];
        
        im = {im1;im2};
        
        genResp{genNum} = squeeze(rData.resp);
    end
    genResp = cell2mat(genResp);
    linResp(:,:,1) = genResp(1:nStim,:);
    linResp(:,:,2) = genResp(nStim+1:2*nStim,:);

    [auc,resp,respFull] = getPostHocResp(sData,linResp,meanFirstTwo);
    resp.im = im;
end

function [auc,respS,respFull] = getPostHocResp(sData,linResp,meanFirstTwo)    
    stim = [sData.stimuli{1,:}];
    ids = [stim.id];
    shapes = [stim.shape];
    type = {shapes.texture};
    exclude = repmat(cellfun(@(x) ~strcmp(x,'RDS'),type),1,2);
    [~,~,parents] = unique({ids.parentId});
    nConds = min(sum((parents == 1:max(parents))));
    nStim = 2*length(shapes)/nConds;
    
    parents = repmat(1:nStim,nConds,1);
    parents = parents(:);
    
    perStimCond = [ones(1,nConds/2) zeros(1,nConds/2)];
    perStimCond = repmat(perStimCond,1,nStim);
    
    resp = squeeze(linResp(:,:,1));
    resp = [resp; squeeze(linResp(:,:,2))];

    parents(exclude == 1) = 0;
    
    nCondsToExclude = sum(exclude)/nStim;
    resp_3d = nan(max(parents),(nConds-nCondsToExclude-2*meanFirstTwo)/2);
    resp_2d = nan(max(parents),(nConds-nCondsToExclude-2*meanFirstTwo)/2);
    resp_3d_full = cell(max(parents),(nConds-nCondsToExclude-2*meanFirstTwo)/2);
    resp_2d_full = cell(max(parents),(nConds-nCondsToExclude-2*meanFirstTwo)/2);
    max_resp = nan(max(parents),1);
    for ii=1:max(parents)
        idx_3d = (parents == ii) & perStimCond';
        idx_2d = (parents == ii) & ~perStimCond';
        
        temp3 = resp(idx_3d==1,:);
        temp2 = resp(idx_2d==1,:);
        if meanFirstTwo
            % 3d
            temp = temp3(1:2,:); resp_3d(ii,1) = nanmean(temp(:)); % resp for first two stim
            resp_3d_full{ii,1} = temp(:)';
            temp = mean(temp3,2); resp_3d(ii,2:end) = temp(3:end); % resp for the rest
            resp_3d_full{ii,2} = temp3(3,:);
            resp_3d_full{ii,3} = temp3(4,:);
            
            % 2d
            temp = temp2(1:2,:); resp_2d(ii,1) = nanmean(temp(:)); % resp for first two stim
            resp_2d_full{ii,1} = temp(:)';
            temp = mean(temp2,2); resp_2d(ii,2:end) = temp(3:end); % resp for the rest
            resp_2d_full{ii,2} = temp2(3,:);
            resp_2d_full{ii,3} = temp2(4,:);
        else
            resp_3d(ii,:) = nanmean(temp3,2);
            resp_2d(ii,:) = nanmean(temp2,2);
            
            for jj=1:size(temp3,1)
                resp_3d_full{ii,jj} = temp3(jj,:);
                resp_2d_full{ii,jj} = temp2(jj,:);
            end
        end

        max_resp(ii) = max([resp_3d(ii,:) resp_2d(ii,:)]);
    end
    
    auc_3d = nan(max(parents),1);
    auc_2d = nan(max(parents),1);
    for ii=1:max(parents)
        auc_3d(ii) = trapz(resp_3d(ii,:)/max(max_resp));
        auc_2d(ii) = trapz(resp_2d(ii,:)/max(max_resp));
    end
    
    auc.vol = auc_3d;
    auc.pla = auc_2d;
    
    respS.vol = resp_3d;
    respS.pla = resp_2d;
    respS.max = max_resp;
    
    respFull.vol = resp_3d_full;
    respFull.pla = resp_2d_full;
    
    if mean(respS.vol(:)) > mean(respS.pla(:))
        respS.score = (mean(respS.vol(:)) - mean(respS.pla(:))) / mean(respS.vol(:));
    else
        respS.score = (mean(respS.vol(:)) - mean(respS.pla(:))) / mean(respS.pla(:));
    end
    
%     score_perStim = (auc_3d - auc_2d) ./ max_resp;
end

% function fixPlot(h,xL,yL,titleStr,legendStr)
%     h.LineWidth = 2; h.Color = 'w';
%     h.XColor = 'k'; h.YColor = 'k';
%     h.Box = 'off'; grid(h,'on');
%     h.TickDir = 'out'; h.LineWidth = 2;
%     
%     h.FontSize = 10; h.FontName = 'Lato';
%     
%     h.XLabel.String = xL;
%     h.XLabel.FontSize = 12; h.XLabel.FontName = 'Lato';
%     h.YLabel.String = yL;
%     h.YLabel.FontSize = 12; h.YLabel.FontName = 'Lato';
%     
%     if exist('legendStr','var')
%         hl = legend(h,legendStr);
%         hl.FontSize = 13; hl.TextColor = 'k'; hl.Color = 'w'; hl.Box = 'off';
%         hl.Location = 'SouthEast';
%     end
%     
%     if exist('titleStr','var')
%         ht = title(h,titleStr);
%         ht.Interpreter = 'none';
%         ht.Color = 'k'; ht.FontSize = 16; ht.FontName = 'Lato';
%     end
% end