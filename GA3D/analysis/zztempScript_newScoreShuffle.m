clc; close all; clear;
loadedFile = load('plots/population/ids.mat');
population = loadedFile.population;

for cc=1:length(population)
    filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
    disp([num2str(cc) ': ' filePrefix]);
    [score(cc),score_shuf{cc}] = doSingleCell(num2str(population(cc).prefix),population(cc).runNum,1,population(cc).nGen-population(cc).nPostHoc,40,population(cc).monkeyId);
end

score_shuf(isnan(score)) = [];
score(isnan(score)) = [];
save('/Users/ramanujan/Documents/hopkins/papers/1b_phys_2p/ep/fig 2/population/shuffScore.mat','score_shuf','score')

% score_shuf(isnan(score_shuf)) = [];

% clf
% load('~/Desktop/matlab.mat');

% for both monkeys cdf
% clf
% h = cdfplot(score); h.LineWidth = 2; h.Color = 'k'; hold on;
% h = cdfplot(score_shuf); h.LineWidth = 2; h.LineStyle = '--'; h.Color = 'k';
% fixPlot(gca,'Solid Preference Index',{'real' 'shuffle'})
% axis square; set(gca,'YLim',[0 1],'xtick',-1:0.5:1,'ytick',0:0.25:1);

% clf
% h = histogram(score_shuf,linspace(-1,1,27)); h.EdgeColor = 'none'; h.FaceColor = [0.2 0.4 1]; h.FaceAlpha = 0.7;hold on;
% h = histogram(score_shuf,linspace(-1,1,31),'DisplayStyle','stairs'); h.LineWidth = 2;  h.EdgeColor = 'k'; 
% h = histogram(score,linspace(-1,1,27)); h.LineWidth = 2; h.EdgeColor = 'none'; h.FaceColor = [1 0.4 0.2]; h.FaceAlpha = 0.7; 
% h = histogram(score,linspace(-1,1,31),'DisplayStyle','stairs'); h.LineWidth = 2; h.EdgeColor = 'k';
% fixPlot(gca,'Solid Preference Index',{'real' 'shuffle'})
% axis square; set(gca,'YLim',[0 50],'xtick',-1:0.5:1,'ytick',0:25:50); grid on;


%     screen2png('plots/population/3dScore_cdf.png');
%     plot2svg('plots/population/3dScore_cdf.svg');

function [score,score_shuf,resp] = doSingleCell(prefix,runNum,startGen,endGen,nStim,monkeyId)
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

        genResp = mean(squeeze(rData.resp),2);
        linResp(:,1) = genResp(1:nStim);
        linResp(:,2) = genResp(nStim+1:2*nStim);

        [specResp,shadeResp,highResp,lowResp] = getControlResp(sData,linResp);
        allShade = [allShade shadeResp]; allSpec = [allSpec specResp]; 
        allHigh = [allHigh highResp]; allLow = [allLow lowResp];
    end
    
    if nGen > 1
        if mean(allShade(:)) > mean(allSpec(:))
            resp3d = mean(allShade(:));
        else
            resp3d = mean(allSpec(:));
        end
        if mean(allHigh(:)) > mean(allLow(:))
            resp2d = mean(allHigh(:));
        else
            resp2d = mean(allLow(:));
        end
        score = (resp3d - resp2d) / max(resp3d,resp2d);
    else
        score = nan;
    end
    
    rr = [allShade(:) allSpec(:) allHigh(:) allLow(:)];
    [M,N] = size(rr);
    rowIndex = repmat((1:M)',[1 N]);
    
    nRand = 100000;
    if nGen > 1
        score_shuf = nan(1,nRand);
        for ii=1:nRand
            [~,randomizedColIndex] = sort(rand(M,N),2);
            newLinearIndex = sub2ind([M,N],rowIndex,randomizedColIndex);
            shuffR = rr(newLinearIndex);
            allShade_s = shuffR(:,1); allSpec_s = shuffR(:,2); 
            allHigh_s = shuffR(:,3); allLow_s = shuffR(:,4); 


            if mean(allShade_s(:)) > mean(allSpec_s(:))
                resp3d_s = mean(allShade_s(:));
            else
                resp3d_s = mean(allSpec_s(:));
            end
            if mean(allHigh_s(:)) > mean(allLow_s(:))
                resp2d_s = mean(allHigh_s(:));
            else
                resp2d_s = mean(allLow_s(:));
            end
            score_shuf(ii) = (resp3d_s - resp2d_s) / max(resp3d_s,resp2d_s);
        end
    else
        score_shuf = nan;
    end
end

function [specResp,shadeResp,highResp,lowResp] = getControlResp(sData,linResp)
    stim = [sData.stimuli{1,:}];
    ids = [stim.id];
    controlIds = [ids.isControl];
    
    for linNum=1:2
        controlResp = reshape(linResp(controlIds,linNum),4,sum(controlIds)/4);
        specResp(linNum,:) = controlResp(1,:);
        shadeResp(linNum,:) = controlResp(4,:);
        
        highResp(linNum,:) = controlResp(2,:);
        lowResp(linNum,:) = controlResp(3,:);
    end
end

function fixPlot(h,titleStr,legendStr)
    h.LineWidth = 2; h.Color = 'w';
    h.XColor = 'k'; h.YColor = 'k';
    h.Box = 'off'; h.XLim = [-1 1];
    h.TickDir = 'out'; h.LineWidth = 2;
    
    h.FontSize = 20; h.FontName = 'Lato';
    
    h.XLabel.String = 'Solid Preference Index';
    h.XLabel.FontSize = 20; h.XLabel.FontName = 'Lato';
    h.YLabel.String = 'Probability';
    h.YLabel.FontSize = 20; h.YLabel.FontName = 'Lato';
    
    hl = legend(h,legendStr);
    hl.FontSize = 12; hl.TextColor = 'k'; hl.Color = 'w'; hl.Box = 'off';
    hl.Location = 'NorthWest';
    
    ht = title(h,titleStr);
    ht.Interpreter = 'none';
    ht.Color = 'k'; ht.FontSize = 14; ht.FontName = 'Lato';
end