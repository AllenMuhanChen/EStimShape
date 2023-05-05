function corrScores = doSingleCell(jobId)
    tic; close all;
    corrScores = [];
    addpath(genpath('dep'));
    loadedFile = load('data/ids.mat');
    population = loadedFile.population;
    cells = 1:length(population); % [3,8,12,32,40,54,60,64,112,113]; 
    
    cellId = cells(jobId + 1);
    runId = [num2str(population(cellId).prefix) '_r-' num2str(population(cellId).runNum)];
    
    disp(['Processing ' runId]);
    nGen = population(cellId).nGen - population(cellId).nPostHoc;
    disp(['... nGen = ' num2str(nGen)]);
    
    if nGen > 2
        %% Parse data
        dataFile = ['data/' runId '_data.mat'];
        if ~exist(dataFile,'file')
            disp(['Processing and saving ' dataFile '...']);
            data = getRunData(population(cellId).prefix,population(cellId).runNum,nGen,population(cellId).monkeyId);    
            save(dataFile,'data');
        else % if ~exist('data','var')
            loadedFile = load(dataFile);
            data = loadedFile.data;
            disp(['Loaded ' dataFile '.']);
        end
        is3d = cellfun(@(x) ~strcmp(x,'TWOD'),{data.texture});
    
        %% Get fit file for stick STA
        fitFile = ['data/' runId '_fit.mat'];
        if ~exist(fitFile,'file')
            disp(['Processing and saving ' fitFile '...']);
            [~,resp,lineage,stimStruct,data] = formatDataForFitting(data);
            save(['data/' runId '_fit.mat'],'resp','lineage','stimStruct'); 
            save(dataFile,'data');
        else % if ~exist('stimStruct','var')
            loadedFile = load(fitFile);
            stimStruct = loadedFile.stimStruct;
            resp = loadedFile.resp;
            lineage = loadedFile.lineage;
            disp(['Loaded ' fitFile '.']);
        end
        
        %% replace resp with dcn data
        % dcnFile = ['data/dcnData/' runId '_data_alexnet.mat'];
        % if ~exist(dcnFile,'file')
        %     disp([dcnFile ' does not exist.']);
        % else % if ~exist('stimStruct','var')
        %     loadedFile = load(dcnFile);
        %     nresp = resp;
        %     resp = redoBestDCNUnit(loadedFile.adata(3).resp,nresp);
        %     resp = repmat(resp,1,2);
        %     disp(['Loaded ' dcnFile '.']);
        % end
        
        %% Stick STA and prediction
        staFile = ['data/' runId '_sta.mat'];
        if ~exist(staFile,'file')
            disp('Calculating stick STA...');
            [sta,sta_shuff,fullSetSta,binSpec] = fitAllSta(stimStruct,resp,lineage,is3d);
            save(staFile,'sta','sta_shuff','fullSetSta','binSpec');
            disp('Getting stick STA predictions...');
            predCompResp = makeStaPrediction(runId,binSpec,fullSetSta,sta,sta_shuff,stimStruct,resp,data,is3d,lineage);
            save(staFile,'predCompResp','-append');
        else % if ~exist('sta','var')
            loadedFile = load(staFile);
            binSpec = loadedFile.binSpec;
            sta = loadedFile.sta;
            sta_shuff = loadedFile.sta_shuff;
            fullSetSta = loadedFile.fullSetSta;
            predCompResp = loadedFile.predCompResp;
            disp(['Loaded ' staFile '.']);        
        end

        %% Get Surface data and fit parameters for surface STA
        % surfdataFile = ['data/' runId '_surfdata.mat'];
        % if ~exist(surfdataFile,'file')
        %     disp(['Processing and saving ' surfdataFile '...']);
        %     surfFitParams = getSurfData(data,0);
        %     disp('Subsampling surface points...');
        %     selectedIds = []; % subsampleVerts(surfFitParams,data);
        %     % [~,selectedIds] = getRoots(data);
        %     save(surfdataFile,'surfFitParams','selectedIds');
        % else % if ~exist('surfFitParams','var')
        %     loadedFile = load(surfdataFile);
        %     surfFitParams = loadedFile.surfFitParams;
        %     selectedIds = loadedFile.selectedIds;
        %     selectedIds = {};
        %     disp(['Loaded ' surfdataFile '.']);
        % end
        
        %% Surface STA
        % surfstaFile = ['data/' runId '_surfsta.mat'];
        % if ~exist(surfstaFile,'file')
        %     disp('Calculating surface STA...');
        %     [sta_surf,sta_shuff_surf,fullSetSta_surf,binSpec_surf] = fitAllSta_surf_v0(surfFitParams,selectedIds,resp,lineage,is3d);
        %     predCompResp_surf = makeSurfStaPrediction(runId,binSpec_surf,fullSetSta_surf,sta_surf,sta_shuff_surf,surfFitParams,resp,selectedIds,data,is3d,lineage);
        %     save(surfstaFile,'sta_surf','sta_shuff_surf','fullSetSta_surf','binSpec_surf','predCompResp_surf');
        % else % if ~exist('sta_surf','var')
        %     loadedFile = load(surfstaFile);
        %     binSpec_surf = loadedFile.binSpec_surf;
        %     sta_surf = loadedFile.sta_surf;
        %     sta_shuff_surf = loadedFile.sta_shuff_surf;
        %     fullSetSta_surf = loadedFile.fullSetSta_surf;
        %     predCompResp_surf = loadedFile.predCompResp_surf;
        %     disp(['Loaded ' surfstaFile '.']);
        % end

        %% Redo predictions?
        % predCompResp = makeStaPrediction(runId,binSpec,fullSetSta,sta,sta_shuff,stimStruct,resp,data,is3d,lineage);
        % save(staFile,'predCompResp','-append');
        % predCompResp_surf = makeSurfStaPrediction(runId,binSpec_surf,fullSetSta_surf,sta_surf,sta_shuff_surf,surfFitParams,resp,selectedIds,data,is3d,lineage);
        % save(surfstaFile,'predCompResp_surf','-append');
        
        %% Use all STAs to get final prediction and the contribution of each STA
        finalPredFile = ['data/' runId '_pred.mat'];
        if ~exist(finalPredFile,'file')
            disp('Calculating final prediction...');
            [staContributions,finalPredictionModel,allPred] = multiPrediction(predCompResp, predCompResp_surf,resp,is3d);
            save(finalPredFile,'staContributions','finalPredictionModel','allPred');
        else
            loadedFile = load(finalPredFile);
            staContributions = loadedFile.staContributions;
            finalPredictionModel = loadedFile.finalPredictionModel;
            allPred = loadedFile.allPred;
            disp(['Loaded ' finalPredFile '.']);
        end

        %% plot STAs
        plotSta_ver3(runId,binSpec,sta,sta_shuff,stimStruct,resp,data,is3d);
        % set(gcf,'Name','DCN')
        % plotSurfSta_ver0(runId,binSpec_surf,sta_surf,sta_shuff_surf,surfFitParams,resp,data,is3d); 
        
        
        %% plot predictions 
        % cs_d = plotPredResp(runId,predCompResp,predCompResp_surf,resp,finalPredictionModel,is3d,1);
        % % corrScores = []; p = [];
        % corrScores.dcn_s = cs_d.s;
        % corrScores.dcn_r = cs_d.r;
        % corrScores.dcn_t = cs_d.t;
        % corrScores.dcn_comb = cs_d.comb;
        
        %% plot neural sta
        % staFile = ['data/latest/' runId '_sta.mat'];
        % if exist(staFile,'file')
        %     loadedFile = load(staFile);
        %     staN = loadedFile.sta;
        %     predCompRespN = loadedFile.predCompResp;
        %     disp(['Loaded ' staFile '.']);        
        % end
        % figure
        % plotSta_ver3(runId,binSpec,staN,[],stimStruct,[],[],[]);
        % set(gcf,'Name','Neural')
        
        %% get neural pred file to compare and save
        % finalPredFile = ['data/latest/' runId '_pred.mat'];
        % if exist(finalPredFile,'file')
        %     loadedFile = load(finalPredFile);
        %     finalPredictionModel = loadedFile.finalPredictionModel;
        %     disp(['Loaded ' finalPredFile '.']);
        % end
        % cs_n = plotPredResp(runId,predCompRespN,predCompResp_surf,nresp,finalPredictionModel,is3d,0);
        % corrScores.neu_s = cs_n.s;
        % corrScores.neu_r = cs_n.r;
        % corrScores.neu_t = cs_n.t;
        % corrScores.neu_comb = cs_n.comb;
        
        %% calculate neural dcn resp corr and also sta corr
        % corrScores.dcn_cor = corr(nanmean(resp,2),nanmean(nresp,2));
        % a = staN(1).s.*staN(2).s; b = sta(1).s.*sta(2).s; corrScores.xSta_s = corr(a(:),b(:));
        % a = staN(1).r.*staN(2).r; b = sta(1).r.*sta(2).r; corrScores.xSta_r = corr(a(:),b(:));
        % a = staN(1).t.*staN(2).t; b = sta(1).t.*sta(2).t; corrScores.xSta_t = corr(a(:),b(:));
        % 
        % load('data/dcnData/population_dcn.mat');
        % corrScores.nScore = nScore(jobId + 1);
        % corrScores.dScore = aScore(jobId + 1,3);
        
        %% plot projections
        % plotStaProjection(runId,binSpec,sta,stimStruct,resp,data,is3d,predCompResp)
        % plotStaProjection_surf(runId,resp,data,is3d,predCompResp_surf);
    else
        disp(['... nGen = ' num2str(nGen) '; too few']);
    end
    toc;
end

%%
function [corrScore,p] = plotPredResp(runId,predCompResp,predCompResp_surf,resp,finalPredictionModel,is3d,doPlot)
    resp = nanmean(resp,2);
    resp = resp/max(resp(:));
    resp(~is3d) = [];
    % if doPlot
    %     hf = figure('pos',[488,342,1220,264],'color','w');
    %     ha = [subplot(151) subplot(152) subplot(153) subplot(154) subplot(155)];
    % else
    %     ha = 1:5; % hack to not generate a figure if doPlot is off
    % end
    % 
    % for ii=1:5
    %     switch ii
    %         case 1; [corrScore.s,p.s] = plotPrediction(ha(1),predCompResp.s,resp,'s',doPlot);
    %         case 2; [corrScore.r,p.r] = plotPrediction(ha(2),predCompResp.r,resp,'r',doPlot);
    %         case 3; [corrScore.t,p.t] = plotPrediction(ha(3),predCompResp.t,resp,'t',doPlot);
    %         case 4; % [corrScore.surf,p.surf] = plotPrediction(ha(4),predCompResp_surf.mult,resp,'surf',doPlot);
    %         case 5; [corrScore.comb,p.comb] = plotPrediction(ha(5),mat2cell( finalPredictionModel.Variables{:,2},ones(1,length(resp)),1),resp,'linComb',doPlot);
    %     end
    % end
    
    if doPlot
        % screen2png(['plots/prediction/icostaPred3_' runId '_multSta.png']);
        % close(hf)
        
        hf = figure('pos',[751,258,585,550],'color','w');
        plotPrediction(gca,mat2cell(finalPredictionModel.Variables{:,2},ones(1,length(resp)),1),resp,'linComb',1);
        box off;
        plot2svg(['~/Desktop/summaries/pred_' runId '.svg']);
        close(hf)
    end
end

function [corrScore,p] = plotPrediction(h,predResp,resp,titleStr,doPlot)
    predResp = cellfun(@max,predResp);
    predResp = predResp/max(predResp);
    lm = fitlm(resp,predResp);
    corrScore = corr(resp,predResp);
    p = lm.coefTest;
    
    if doPlot
        plot(h,resp,predResp,'k.','markersize',20); hold(h,'on');
        plot(h,0:0.1:1,lm.predict((0:0.1:1)'),'r','LineWidth',3);
        fixPlot(h,[titleStr ': ' num2str(round(corrScore,2))])
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

function [resp,corrV,idx] = redoBestDCNUnit(dresp,nresp)
    nresp = nanmean(nresp,2);
    nresp = nresp / max(nresp);
    
    dresp(isnan(nresp),:) = nan;
    dresp(dresp < 0) = 0;
    dresp = dresp./repmat(nanmax(dresp),[size(dresp,1),1]);
    
    corrV = corr(nresp,dresp);
    
    [~,idx] = max(corrV);
    resp = dresp(:,idx);
end