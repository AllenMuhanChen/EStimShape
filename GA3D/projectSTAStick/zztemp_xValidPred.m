clc; close all; clear;
% loadedFile = load('data/ids.mat');
% population = loadedFile.population;
files = dir('data/neural'); files = {files(cellfun(@(x) contains(x,'pred'),{files.name})).name}';
% files = files([4, 45, 77, 78]); % figure 2 selected cells
%%
% load('~/Desktop/matlab_rHeld.mat')
for ii=1:length(files)
    files{ii}(strfind(files{ii},'_pred'):end) = '';
    runId = files{ii};
    disp([num2str(ii) ': ' runId]);

    load(['data/neural/' runId '_pred.mat'],'allPred')
    load(['data/' runId '_fit.mat'],'resp')
    load(['data/' runId '_data.mat'])
    
    is3d = cellfun(@(x) ~strcmp(x,'TWOD'),{data.texture});
    
    resp = nanmean(resp,2);
    resp = resp ./ max(resp);
    resp(~is3d) = [];
    
    pred = allPred(:,1:3);
    
    % do exactly what i did for the figure
    beta = regress(resp,pred);
    LM = fitlm(resp,getLinComb(beta',pred));
    % h = subplot(131);
    rNoVal(ii) = corr(resp,LM.Variables{:,2});
    % rAll(ii) = plotPrediction([],mat2cell(LM.Variables{:,2},ones(1,length(resp)),1),resp,0); %#ok<MMTC>

    % then do x valid
    [respVal{ii},~,rVal(ii)] = regress_cv(resp,pred,10); % ,subplot(132),subplot(133)
    
    rr{ii} = resp;
    
    % LM = fitlm(resp,respVal);
    % c = LM.Coefficients{1,1};
    % m = LM.Coefficients{2,1};
    % clf; plot(resp,respVal,'k.','markersize',30); hold on;
    % line([0 1],[c m+c],'color',[1 0.4 0.2]);
    % fixPlot(gca,'');
    % axis([0 1 0 1]); axis square;
    % plot2svg(['~/Desktop/' runId '_pred.svg'])
    
%     line(
    
    % fixPlot(subplot(132),num2str(round(max(rVal),2)))
    % fixPlot(subplot(133),num2str(round(rHeld,2)))
end

resp = rr;
save('~/Desktop/xValPred.mat','resp','respVal','rVal','rNoVal')

cdfplot(rVal); axis([0 1 0 1]); axis square
plot2svg('~/Desktop/xValid_comboPred.svg')

%%
% figure('pos',[560,600,1121,348],'color','w')
% subplot(131)
% h = cdfplot(rAll); h.LineWidth = 2; h.Color = 'k'; hold on;
% h = cdfplot(rHeld); h.LineWidth = 2; h.LineStyle = '--'; h.Color = 'k';
% fixPlot(gca,'r',{'all' 'held out'})
% axis square; set(gca,'YLim',[0 1],'xtick',0:0.25:1,'ytick',0:0.25:1);
% 
% subplot(132)
% h = histogram(rAll,linspace(0,1,35)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.4 1]; h.FaceAlpha = 0.7;hold on;
% % h = histogram(score_shuf,linspace(-1,1,31),'DisplayStyle','stairs'); h.LineWidth = 2;  h.EdgeColor = 'k'; 
% h = histogram(rHeld,linspace(0,1,35)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [1 0.4 0.2]; h.FaceAlpha = 0.7; 
% % h = histogram(score,linspace(-1,1,31),'DisplayStyle','stairs'); h.LineWidth = 2; h.EdgeColor = 'k';
% fixPlot(gca,'r',{'all' 'held'})
% axis square; set(gca,'YLim',[0 30],'xtick',0:0.25:1,'ytick',0:10:30); grid on;
% 
% subplot(133)
% plot(rAll,rHeld,'k.','MarkerSize',15);
% fixPlot(gca,'','')
% axis square; set(gca,'YLim',[0.5 1],'xtick',0:0.25:1,'ytick',0:0.25:1); grid on;
% xlabel('r all'); ylabel('r held');


function y = getLinComb(beta,x)
    y = sum(repmat(beta,size(x,1),1) .* x,2);
end


function corrScore = plotPrediction(h,predResp,resp,doPlot)
    predResp = cellfun(@max,predResp);
    corrScore = corr(resp,predResp);
    
    if doPlot
        plot(h,resp,predResp,'k.','markersize',10); hold(h,'on');
        fixPlot(h,num2str(round(corrScore,2)))
    end
end

% function fixPlot(h,titleStr)
%     h.LineWidth = 1; h.Color = 'w';
%     h.XColor = 'k'; h.YColor = 'k';
%     h.Box = 'on';
%     h.XLim = [0 1]; h.YLim = [0 1];
%     h.XTick = 0:0.5:1; h.YTick = 0:0.5:1;
%     h.TickDir = 'out'; h.LineWidth = 1;
% 
%     h.FontSize = 12; h.FontName = 'Lato';
% 
%     h.XLabel.String = 'Response';
%     h.XLabel.FontSize = 12; h.XLabel.FontName = 'Lato';
%     h.YLabel.String = 'Prediction';
%     h.YLabel.FontSize = 12; h.YLabel.FontName = 'Lato';
% 
%     ht = title(h,titleStr);
%     ht.Color = 'k'; ht.FontSize = 16; ht.FontName = 'Lato';
% 
%     axis(h,'square');
% end

function [respVal,rAllVal,rFull] = regress_cv(y,X,kFold)
    n = length(y);
    c = cvpartition(n,'KFold',kFold);
    beta = nan(size(X,2),kFold);
    respVal = nan(size(y));
    rAllVal = nan(1,kFold);
    for ii=1:kFold
        idxTrain = training(c,ii);
        idxVal = ~idxTrain;
        XTrain = X(idxTrain,:);
        yTrain = y(idxTrain);
        XVal = X(idxVal,:);
        yVal = y(idxVal);
        beta(:,ii) = regress(yTrain,XTrain);
        yPred = XVal * beta(:,ii);
        respVal(idxVal) = yPred;
        rAllVal(ii) = corr(yVal,yPred);
    end
    rFull = corr(respVal,y);
end


function fixPlot(h,titleStr,legendStr)
    h.LineWidth = 2; h.Color = 'w';
    h.XColor = 'k'; h.YColor = 'k';
    h.Box = 'off'; h.XLim = [0.5 1];
    h.TickDir = 'out'; h.LineWidth = 2;
    
    h.FontSize = 20; h.FontName = 'Lato';
    
    h.XLabel.String = 'r';
    h.XLabel.FontSize = 20; h.XLabel.FontName = 'Lato';
    h.YLabel.String = 'Probability';
    h.YLabel.FontSize = 20; h.YLabel.FontName = 'Lato';
    
    if ~isempty(titleStr)
        hl = legend(h,legendStr);
        hl.FontSize = 12; hl.TextColor = 'k'; hl.Color = 'w'; hl.Box = 'off';
        hl.Location = 'NorthWest';
    end
    
    
    if ~isempty(titleStr)
        ht = title(h,titleStr);
        ht.Interpreter = 'none';
        ht.Color = 'k'; ht.FontSize = 14; ht.FontName = 'Lato';
    end
end