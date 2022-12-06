clc; close all; clear;
loadedFile = load('plots/population/ids.mat');
population = loadedFile.population;

score = nan(length(population),1);
sig3d = nan(length(population),6);
sig2d = nan(length(population),6);
for cc=1:length(population)
    filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
    disp([num2str(cc) ': ' filePrefix]);
    [score(cc),sig3d(cc,:),sig2d(cc,:)] = doSingleCell(num2str(population(cc).prefix),population(cc).runNum,1,population(cc).nGen-population(cc).nPostHoc,40,population(cc).monkeyId);
end

sig2d(isnan(score),:) = [];
sig3d(isnan(score),:) = [];
score(isnan(score)) = [];
save('/Users/ramanujan/Documents/hopkins/papers/1b_phys_2p/ep/fig 2/population/shuffScore_percell.mat','sig2d','sig3d','score')

%% many sig thresholds
% clf;
% set(gcf,'color','w','pos',[50,1,660,954]);
% sigLevel = 0.05;
% thresh = [0.05 0.01 0.005 0.001 0.0005 0.0001];
% for ii=1:6
%     subplot(3,2,ii);
%     sigLevel = thresh(ii);
%     h = histogram(score,linspace(-1,1,27)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [0.5 0.5 0.5]; h.FaceAlpha = 1; hold on;
%     h = histogram(score(score > sig3d(:,thresh == sigLevel) & score > 0),linspace(-1,1,27)); h.EdgeColor = 'none'; h.FaceColor = [1 0.6 0.1]; h.FaceAlpha = 1; 
%     h = histogram(score(score < sig2d(:,thresh == sigLevel) & score < 0),linspace(-1,1,27)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.6 1]; h.FaceAlpha = 1; 
%     legStr = {'all 143' ['3d ' num2str(sum(score > sig3d(:,thresh == sigLevel) & score > 0)) '/' num2str(sum(score > 0))] ['2d ' num2str(sum(score < sig2d(:,thresh == sigLevel) & score < 0)) '/' num2str(sum(score < 0))]};
%     fixPlot(gca,[-1 1],[0 30],'solid index','count',-1:0.5:1,0:10:30,['p<' num2str(sigLevel)],legStr)
%     axis square; set(gca,'YLim',[0 30],'xtick',-1:0.5:1,'ytick',0:10:30); grid on;
% end
% screen2png('plots/population/3dScore_cdf_hist_randTest.png');
% screen2png('~/Desktop/3dScore_cdf_hist_randTest.png');

%% p < 0.05
clf;
set(gcf,'color','w','pos',[118,374,477,433]);

nBin = 27;
sigLevel = 0.05;
thresh = [0.05 0.01 0.005 0.001 0.0005 0.0001];
h = histogram(score,linspace(-1,1,27)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [0.5 0.5 0.5]; h.FaceAlpha = 1; hold on;
h = histogram(score(score > sig3d(:,thresh == sigLevel) & score > 0),linspace(-1,1,27)); h.EdgeColor = 'none'; h.FaceColor = [1 0.6 0.1]; h.FaceAlpha = 1; 
h = histogram(score(score < sig2d(:,thresh == sigLevel) & score < 0),linspace(-1,1,27)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.6 1]; h.FaceAlpha = 1; 
legStr = {'all 143' ['3d ' num2str(sum(score > sig3d(:,thresh == sigLevel) & score > 0)) '/' num2str(sum(score > 0))] ['2d ' num2str(sum(score < sig2d(:,thresh == sigLevel) & score < 0)) '/' num2str(sum(score < 0))]};
fixPlot(gca,[-1 1],[0 30],'solid index','count',-1:0.5:1,0:10:30,'ga',legStr)
axis square; set(gca,'YLim',[0 30],'xtick',-1:0.5:1,'ytick',0:10:30); grid on;

% screen2png('plots/population/3dScore_cdf_hist_randTest.png');
% screen2png('~/Desktop/3dScore_cdf_hist_randTest.png');

function [score,sig3d,sig2d] = doSingleCell(prefix,runNum,startGen,endGen,nStim,monkeyId)
    getPaths;

    gens = startGen:endGen;
    nGen = endGen - startGen + 1;
    folderName = [prefix '_r-' num2str(runNum)];
    
    allShade = []; allSpec = [];
    allHigh = []; allLow = [];
    for genNum=2:nGen
        genId = gens(genNum);
        fullFolderName = [folderName '_g-' num2str(genId)];

        rData = load([respPath '/' fullFolderName '/resp.mat']);
        sData = load([stimPath '/' fullFolderName '/stimParams.mat']);

        genResp = squeeze(rData.resp);

        [specResp,shadeResp,highResp,lowResp] = getControlResp(sData,genResp);
        allShade = [allShade; shadeResp]; allSpec = [allSpec; specResp]; 
        allHigh = [allHigh; highResp]; allLow = [allLow; lowResp];
    end
    
    if nGen > 1
        if mean(allShade(:)) > mean(allSpec(:))
            resp3d = mean(allShade(:));
            resp3dAll = allShade;
        else
            resp3d = mean(allSpec(:));
            resp3dAll = allSpec;
        end
        if mean(allHigh(:)) > mean(allLow(:))
            resp2d = mean(allHigh(:));
            resp2dAll = allHigh;
        else
            resp2d = mean(allLow(:));
            resp2dAll = allLow;
        end
        score = (resp3d - resp2d) / max(resp3d,resp2d);
        
        rr = [resp3dAll resp2dAll];
        [M,N] = size(rr);
        rowIndex = repmat((1:M)',[1 N]);
        sc = nan(1,10000);
        for ii=1:10000
            [~,randomizedColIndex] = sort(rand(M,N),2);
            newLinearIndex = sub2ind([M,N],rowIndex,randomizedColIndex);
            shuffR = rr(newLinearIndex);
            resp3d = mean(mat2vec(shuffR(:,1:5)));
            resp2d = mean(mat2vec(shuffR(:,6:10)));
            sc(ii) = (resp3d - resp2d) / max(resp3d,resp2d);
        end
        
        thresh = [0.05 0.01 0.005 0.001 0.0005 0.0001];
        sig3d = arrayfun(@(x) prctile(sc,100-(x*100)/2),thresh);
        sig2d = arrayfun(@(x) prctile(sc,(x*100)/2),thresh);
    else
        score = nan;
        sig3d = nan(1,6);
        sig2d = nan(1,6);
    end
    
    
end

function [specResp,shadeResp,highResp,lowResp] = getControlResp(sData,genResp)
    stim = [sData.stimuli{1,:}];
    ids = [stim.id];
    controlIds = repmat([ids.isControl],1,2);
    
    controlResp = genResp(controlIds,:);
    specResp = controlResp(1:4:end,:);
    shadeResp = controlResp(4:4:end,:);

    highResp = controlResp(2:4:end,:);
    lowResp = controlResp(3:4:end,:);
end
