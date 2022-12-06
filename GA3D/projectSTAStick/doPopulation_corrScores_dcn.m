close all

if ~exist('corrScores','var')
    load('data/corrScores_dcn.mat')
end

subplot(341)
scatter([corrScores.neu_s],[corrScores.dcn_s],30,[corrScores.dcn_cor]);
axis square; axis([0 1 0 1]); set(gca,'clim',[0 0.8]);
xlabel('prediction accuracy for neural sta predicting neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('shaft')

subplot(342)
scatter([corrScores.neu_r],[corrScores.dcn_r],30,[corrScores.dcn_cor]);
axis square; axis([0 1 0 1]); set(gca,'clim',[0 0.8]);
xlabel('prediction accuracy for neural sta predicting neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('junction')

subplot(343)
scatter([corrScores.neu_t],[corrScores.dcn_t],30,[corrScores.dcn_cor]);
axis square; axis([0 1 0 1]); set(gca,'clim',[0 0.8]);
xlabel('prediction accuracy for neural sta predicting neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('termination')

subplot(344)
scatter([corrScores.neu_comb],[corrScores.dcn_comb],30,[corrScores.dcn_cor]);
axis square; axis([0 1 0 1]); set(gca,'clim',[0 0.8]); colorbar('Location','west')
xlabel('prediction accuracy for neural sta predicting neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('linear comb')

%%
subplot(345)
plot([corrScores.dcn_cor],[corrScores.xSta_s],'k.','MarkerSize',20);
axis square; axis([0 1 0 1]);
xlabel('correlation between best dcn responses and neural responses')
ylabel('correlation between neural STA and DCN STA')
title('corr between shaft stas')

subplot(346)
plot([corrScores.dcn_cor],[corrScores.xSta_r],'k.','MarkerSize',20);
axis square; axis([0 1 0 1]);
xlabel('correlation between best dcn responses and neural responses')
ylabel('correlation between neural STA and DCN STA')
title('corr between junction stas')

subplot(347)
plot([corrScores.dcn_cor],[corrScores.xSta_t],'k.','MarkerSize',20);
axis square; axis([0 1 0 1]);
xlabel('correlation between best dcn responses and neural responses')
ylabel('correlation between neural STA and DCN STA')
title('corr between termination stas')

subplot(348)
h = cdfplot([corrScores.xSta_s]); h.LineWidth=2; hold on;
h = cdfplot([corrScores.xSta_r]); h.LineWidth=2; hold on;
h = cdfplot([corrScores.xSta_t]); h.LineWidth=2; hold on;
legend({'s' 'r' 't'},'Location','northwest')
axis square; axis([0 1 0 1]); set(gca,'XTick',0:0.25:1)

%%
subplot(349)
plot([corrScores.dcn_cor],[corrScores.dcn_s],'k.','MarkerSize',20);
axis square; axis([0 1 0 1]);
xlabel('correlation between best dcn responses and neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('shaft')

subplot(3,4,10)
plot([corrScores.dcn_cor],[corrScores.dcn_r],'k.','MarkerSize',20);
axis square; axis([0 1 0 1]);
xlabel('correlation between best dcn responses and neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('junction')

subplot(3,4,11)
plot([corrScores.dcn_cor],[corrScores.dcn_t],'k.','MarkerSize',20);
axis square; axis([0 1 0 1]);
xlabel('correlation between best dcn responses and neural responses')
ylabel('prediction accuracy for dcn sta predicting dcn responses')
line([0 1], [0 1]); title('termination')

subplot(3,4,12)
h = cdfplot([corrScores.dcn_cor]); h.LineWidth=2; h.Color = 'k';
axis square; axis([0 1 0 1]); set(gca,'XTick',0:0.25:1)

%%
% load('data/ids.mat','population');
% goodIdx = find(cellfun(@(x) ~isempty(x),{corrScores.dcn_s}));
% selectedIdx = find([corrScores.nScore] > 0.3 & ([corrScores.xSta_r] > 0.4 | [corrScores.xSta_s] > 0.4 | [corrScores.xSta_t] > 0.4)); % & [corrScores.dcn_cor] > 0.6);
% a = corrScores(goodIdx(selectedIdx));
% b = population(goodIdx(selectedIdx));
% 
% for ii=1:length(b)
%     runId = [num2str(b(ii).prefix) '_r-' num2str(b(ii).runNum)];
%     nGen = b(ii).nGen - b(ii).nPostHoc;
%     load(['data/dcnData/' runId '_data_alexnet.mat'])
%     aresp = adata(3).resp(:,adata(3).maxCorrUnitIdx);
%     aresp(aresp<0) = 0;
%     aresp = aresp/max(aresp);
%     plot(nresp,aresp,'k.','k.','MarkerSize',20)
%     disp([runId ': ' num2str(nGen) ': ' num2str(corr(nresp,aresp))])
%     pause
% end
    