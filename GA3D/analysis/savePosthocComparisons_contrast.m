% function savePosthocComparisons_contrast
    close all; clear; clc;
    % save or load data
    if ~exist('plots/population/contrast_data.mat','file')
        [resp,cell,respFull] = doAllCells();
        stats = getAnova(respFull);
        save('plots/population/contrast_data.mat','resp','cell','respFull','stats');
    else
        load('plots/population/contrast_data.mat','resp','cell','respFull','stats');
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
    % reject = checkForSpecular(cell,resp);
    % cell(reject) = []; resp(reject) = [];
    % 
    % % doPlots_0(cell,resp);
    % doPlots_1(cell,resp);
    
    % screen2png('plots/population/rds_auc.png')
    
    %% randomization test
    sig3d = []; sig2d = [];
    for ii=1:length(resp)
        ii
        for ss=1:size(respFull(ii).vol,1)
            vol = mat2vec(respFull(ii).vol(ss,:,:));
            pla = mat2vec(respFull(ii).pla(ss,:,:));
            sc_v(ss) = mean(vol); % across reps
            sc_p(ss) = mean(pla); % across reps
            
            a = [vol;pla];
            for rr=1:10000
                a = a(randperm(length(a)));
                sc_sh_v(ss,rr) = mean(a(1:length(a)/2));
                sc_sh_p(ss,rr) = mean(a(1+length(a)/2 : end));
            end
        end
        sc(ii) = (mean(sc_v)-mean(sc_p))./max(mean(sc_v),mean(sc_p));
        sc_sh = (mean(sc_sh_v)-mean(sc_sh_p))./max([mean(sc_sh_v);mean(sc_sh_p)]);
        upperC = prctile(sc_sh,100-2.5);
        lowerC = prctile(sc_sh,2.5);
        sig3d(ii) = sc(ii)>upperC;
        sig2d(ii) = sc(ii)<lowerC;
    end
    
    %% histogram
    clf;
    set(gcf,'color','w','pos',[118,446,1025,361]);
    
    nBin = 13;
    subplot(131);
    h = histogram(sc,linspace(-1,1,nBin)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [0.5 0.5 0.5]; h.FaceAlpha = 1; hold on;
    h = histogram(sc(sig3d & sc > 0),linspace(-1,1,nBin)); h.EdgeColor = 'none'; h.FaceColor = [1 0.6 0.1]; h.FaceAlpha = 1; 
    h = histogram(sc(sig2d & sc < 0),linspace(-1,1,nBin)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.6 1]; h.FaceAlpha = 1; 
    legStr = {'all 18' ['3d ' num2str(sum(sig3d & sc > 0)) '/' num2str(sum(sc > 0))] ['2d ' num2str(sum(sig2d & sc < 0)) '/' num2str(sum(sc < 0))]};
    fixPlot(gca,[-1 1],[0 8],'solid index','count',-1:0.5:1,0:2:6,'contrast',legStr)
    
    subplot(132);
    sc_ga = [cell.score_3d];
    h = histogram(sc_ga,linspace(-1,1,nBin)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [0.5 0.5 0.5]; h.FaceAlpha = 1; hold on;
    h = histogram(sc_ga(sc_ga>sig3d_ga' & sc_ga > 0),linspace(-1,1,nBin)); h.EdgeColor = 'none'; h.FaceColor = [1 0.6 0.1]; h.FaceAlpha = 1; 
    h = histogram(sc_ga(sc_ga<sig2d_ga' & sc_ga < 0),linspace(-1,1,nBin)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.6 1]; h.FaceAlpha = 1; 
    legStr = {'all 18' ['3d ' num2str(sum(sc_ga>sig3d_ga' & sc_ga > 0)) '/' num2str(sum(sc_ga > 0))] ['2d ' num2str(sum(sc_ga<sig2d_ga' & sc_ga < 0)) '/' num2str(sum(sc_ga < 0))]};
    fixPlot(gca,[-1 1],[0 8],'solid index','count',-1:0.5:1,0:2:6,'ga',legStr)

    
    sigGA = (sc_ga>sig3d_ga' & sc_ga > 0) | (sc_ga<sig2d_ga' & sc_ga < 0);
    sigCo = (sig3d & sc > 0) | (sig2d & sc < 0);
    sig = sum([sigGA(:)*2 sigCo(:)],2)+1;
    cols = [0.5 0.5 0.5; 0.8 0.4 0.2; 0.2 0.3 0.8; 0.7 0.3 0.7];
    cols = cols(sig,:);
    
    accept = checkForSpecular(cell,resp)==0;
    subplot(133);
    h = scatter(sc_ga,sc,800,cols,'marker','.'); hold on; % [0.6 0.6 0.6]
    h = plot(sc_ga(~accept),sc(~accept),'.','markersize',10,'color','w'); hold on; % [0.6 0.6 0.6]
    % plot(a(sig),b(sig),'k.','markersize',20); hold on;
    fixPlot(gca,[-1 1],[-1 1],'solid index (ga)','solid index (contrast)',-1:0.5:1,-1:0.5:1,'contrast vs ga')
    ht = text(-0.8,-0.6,'contrast','color',[0.8 0.4 0.2],'FontName','lato','FontSize',12);
    ht = text(-0.8,-0.72,'ga','color',[0.2 0.3 0.8],'FontName','lato','FontSize',12);
    ht = text(-0.8,-0.86,'both','color',[0.8 0.3 0.8],'FontName','lato','FontSize',12);
%     delete(ht)
    screen2png('plots/population/contrast_cdf_hist_randTest.png');
    screen2png('~/Desktop/contrast_cdf_hist_randTest.png');
% end

%%
function reject = checkForSpecular(cell,resp)
    getPaths;
    reject = false(length(cell),1);
    % save control data
    for cc=1:length(cell)
        % mainScript_AnalyzeGen_3d(num2str(cell(cc).prefix),cell(cc).runNum,...
        %     1,cell(cc).nGen-cell(cc).nPostHoc,2,40,20,0,0,cell(cc).monkeyId);
        
        filePrefix = [num2str(cell(cc).prefix) '_r-' num2str(cell(cc).runNum)];
        load([plotPath '/' filePrefix '/' filePrefix '_allControls.mat'])
        
        [~,idx] = max(mean(controlResp,2));
        if idx == 1
            a = squeeze(allControlResp(1,:,:)); a = a(:);
            b = squeeze(allControlResp(2,:,:)); b = b(:);
            c = squeeze(allControlResp(3,:,:)); c = c(:);
            d = squeeze(allControlResp(4,:,:)); d = d(:);
            reject(cc) = ttest(a,b,'alpha',0.05) && ttest(a,c,'alpha',0.05) && ttest(a,d,'alpha',0.05);
        end
    end
end

function doPlots_0(cell,resp)
    figure('color','w')
    
    % for 3d pref score colors
    cols = parula(256);
    colspace = linspace(-1,1,256);
    
    h1 = subplot(231); h2 = subplot(232);
    line(h1,[0 1],[0 1],'linewidth',2,'color','k'); hold(h1,'on');
    line(h2,[0 1],[0 1],'linewidth',2,'color','k'); hold(h2,'on');
    for ii=1:length(resp)
        [~,col_idx] = min(abs(colspace - cell(ii).score_3d));
        
        avgResp_3d = mean(resp(ii).vol(:)); semResp_3d = std(resp(ii).vol(:))/sqrt(length(resp(ii).vol(:)));
        avgResp_2d = mean(resp(ii).pla(:)); semResp_2d = std(resp(ii).pla(:))/sqrt(length(resp(ii).pla(:)));
        
        linWid = [avgResp_3d - semResp_3d avgResp_3d + semResp_3d];
        line(h1,[linWid(1) linWid(2)],[avgResp_2d avgResp_2d],'linewidth',2,'color',cols(col_idx,:))
        linWid = [avgResp_2d - semResp_2d avgResp_2d + semResp_2d];
        line(h1,[avgResp_3d avgResp_3d],[linWid(1) linWid(2)],'linewidth',2,'color',cols(col_idx,:))
        
        plot(h1,avgResp_3d,avgResp_2d,'.','MarkerSize',20,'color',cols(col_idx,:))
        
        if avgResp_3d > avgResp_2d
            sc(ii) = (avgResp_3d - avgResp_2d)/avgResp_3d;
        else
            sc(ii) = (avgResp_3d - avgResp_2d)/avgResp_2d;
        end
        
        [~,stim_idx] = max(max([resp(ii).vol;resp(ii).pla],[],2));
        stimIds = repmat(1:size(resp(ii).vol,1),1,2);
        stim_idx = stimIds(stim_idx);
        
        avgResp_3d = mean(resp(ii).vol(stim_idx,:)); semResp_3d = std(resp(ii).vol(stim_idx,:))/sqrt(length(resp(ii).vol(stim_idx,:)));
        avgResp_2d = mean(resp(ii).pla(stim_idx,:)); semResp_2d = std(resp(ii).vol(stim_idx,:))/sqrt(length(resp(ii).vol(stim_idx,:)));
        
        linWid = [avgResp_3d - semResp_3d avgResp_3d + semResp_3d];
        line(h2,[linWid(1) linWid(2)],[avgResp_2d avgResp_2d],'linewidth',2,'color',cols(col_idx,:))
        linWid = [avgResp_2d - semResp_2d avgResp_2d + semResp_2d];
        line(h2,[avgResp_3d avgResp_3d],[linWid(1) linWid(2)],'linewidth',2,'color',cols(col_idx,:))
        
        plot(h2,avgResp_3d,avgResp_2d,'.','MarkerSize',20,'color',cols(col_idx,:))
        
        
        if avgResp_3d > avgResp_2d
            sc3(ii) = (avgResp_3d - avgResp_2d)/avgResp_3d;
        else
            sc3(ii) = (avgResp_3d - avgResp_2d)/avgResp_2d;
        end
        
        sc2(ii) = cell(ii).score_3d;
    end
    fixPlot(h1,'3D mean resp','2D mean resp','Mean resp across stimuli for each cell');
    axis(h1,'square'); axis(h1,[0 1 0 1])
    fixPlot(h2,'3D max resp','2D max resp','Mean resp across contrast for each cell for best stim');
    axis(h2,'square'); axis(h2,[0 1 0 1])
    
    subplot(234);
    h = cdfplot(sc); h.LineWidth = 2;
    fixPlot(gca,'3D Pref Score','Cell count','3d pref score (mean resp)');
    set(gca,'XLim',[-1 1]);
    axis square; 
    
    subplot(235);
    h = cdfplot(sc3); h.LineWidth = 2;
    fixPlot(gca,'3D Pref Score','Cell count','3d pref score (max stim resp)');
    set(gca,'XLim',[-1 1]);
    axis square;  
    
    subplot(236);
    line([-0.5 1],[-0.5 1],'linewidth',2,'color','k'); hold on;
    plot(sc2,sc,'.','MarkerSize',20)
    fixPlot(gca,'3D Pref Score (GA)','3D Pref Score (contrast)');
    axis([-0.5 1 -0.5 1]); axis square
end

function doPlots_1(cell,resp)
    figure('color','w')
    
    for ii=1:length(resp)        
        avgResp_3d = mean(resp(ii).vol(:));
        avgResp_2d = mean(resp(ii).pla(:));
        
        if avgResp_3d > avgResp_2d
            sc(ii) = (avgResp_3d - avgResp_2d)/avgResp_3d;
        else
            sc(ii) = (avgResp_3d - avgResp_2d)/avgResp_2d;
        end
        
        sc2(ii) = cell(ii).score_3d;
    end

    
    subplot(121);
    h = cdfplot(sc); h.LineWidth = 2;
    fixPlot(gca,'3D Pref Score','Cell count','3d pref score (mean resp)');
    set(gca,'XLim',[-1 1]);
    axis square; 
   
    subplot(122);
    line([-1 1],[-1 1],'linewidth',2,'color','k'); hold on;
    plot(sc2,sc,'.','MarkerSize',20)
    fixPlot(gca,'3D Pref Score (GA)','3D Pref Score (contrast)');
    axis([-1 1 -1 1]); axis square
end

function tabl = getAnova(respFull)
    for ii=1:length(respFull)
        resp_3d = respFull(ii).vol;
        resp_2d = respFull(ii).pla;
        
        nStim = size(resp_3d,1);
        nCont = size(resp_3d,2);
        nReps = size(resp_3d,3);
        
        groups = []; data = [];
        for ss=1:nStim
            c1 = ss*ones(2*nCont*nReps,1);
            c2 = [ones(nCont*nReps,1); 2*ones(nCont*nReps,1)];
            c3 = repmat(1:nReps,5,1); c3 = [c3(:); c3(:)];
            
            dat = squeeze(resp_3d(ss,:,:))';
            s1 = dat(:);
            dat = squeeze(resp_2d(ss,:,:))';
            s1 = [s1; dat(:)];
            
            groups = [groups; c1 c2 c3];
            data = [data; s1];
        end
        [~,tabl{ii}] = anovan(data,groups,'display','off');
    end
end

function [resp,cell,respFull] = doAllCells()
    load('plots/population/ids.mat','population');
    count = 1;
    for cc=1:length(population)
        if sum(population(cc).postHocIds == 9) > 0
            filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
            disp([num2str(count) ': ' num2str(cc) ': ' filePrefix]);
            [resp_t,fullResp_t] = doSingleCell(num2str(population(cc).prefix),population(cc).runNum,population(cc).nGen,population(cc).nPostHoc,population(cc).postHocIds,40,population(cc).monkeyId); % allDCNCells(cc).bestCellResp);
            resp(count) = resp_t;
            respFull(count) = fullResp_t;
            cell(count) = population(cc);
            count = count + 1;
        end
    end
end

function [resp,resp_full] = doSingleCell(prefix,runNum,nGen,nPosthocs,postHocIds,nStim,monkeyId)
    getPaths;
    
    postHocGens = nGen-nPosthocs+1 : nGen;
    postHocGens = postHocGens(postHocIds == 9);
    
    folderName = [prefix '_r-' num2str(runNum)];

    genResp = cell(1,length(postHocGens));
    for genNum=1:length(postHocGens)
        genId = postHocGens(genNum);
        fullFolderName = [folderName '_g-' num2str(genId)];

        rData = load([respPath '/' fullFolderName '/resp.mat']);
        sData = load([stimPath '/' fullFolderName '/stimParams.mat']);
        
        im1 = [analysisPath '/plots/' folderName '/' fullFolderName '/' fullFolderName '_l-1_allStim.png'];
        im2 = [analysisPath '/plots/' folderName '/' fullFolderName '/' fullFolderName '_l-2_allStim.png'];
        
        resp.im = {im1;im2};

        genResp{genNum} = squeeze(rData.resp);
    end
    genResp = cell2mat(genResp);
    linResp(:,:,1) = genResp(1:nStim,:);
    linResp(:,:,2) = genResp(nStim+1:2*nStim,:);

    [resp_3d,resp_2d,resp_3d_full,resp_2d_full] = getPostHocResp(sData,linResp);
    
    resp.vol = resp_3d;
    resp.pla = resp_2d;
    
    resp_full.vol = resp_3d_full;
    resp_full.pla = resp_2d_full;
end

function [resp_3d,resp_2d,resp_3d_full,resp_2d_full] = getPostHocResp(sData,linResp)    
    stim = [sData.stimuli{1,:}];
    ids = [stim.id];
    
    [~,~,parents] = unique({ids.parentId});
    nConds = min(sum((parents == 1:max(parents))));
    nStim = 2*length(ids)/nConds;
    
    parents = repmat(1:nStim,nConds,1);
    parents = parents(:);
    
    perStimCond = [zeros(1,nConds/2) ones(1,nConds/2)];
    perStimCond = repmat(perStimCond,1,nStim);
    
    resp = squeeze(linResp(:,:,1));
    resp = [resp; squeeze(linResp(:,:,2))];
    fullResp = resp;
    resp = mean(resp,2);
    resp = resp/max(resp(:));
    
    resp_3d = nan(max(parents),nConds/2);
    resp_2d = nan(max(parents),nConds/2);
    resp_3d_full = nan(max(parents),nConds/2,size(fullResp,2));
    resp_2d_full = nan(max(parents),nConds/2,size(fullResp,2));
    for ii=1:max(parents)
        idx_3d = (parents == ii) & perStimCond';
        idx_2d = (parents == ii) & ~perStimCond';
        
        resp_3d(ii,:) = resp(idx_3d==1);
        resp_2d(ii,:) = resp(idx_2d==1);
        
        resp_3d_full(ii,:,:) = fullResp(idx_3d==1,:);
        resp_2d_full(ii,:,:) = fullResp(idx_2d==1,:);
    end
end

