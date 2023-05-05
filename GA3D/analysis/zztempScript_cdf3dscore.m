
function [score,score_dcn] = zztempScript()
    loadedFile = load('plots/population/ids.mat');
    population = loadedFile.population;

    % for cc=1:length(population)
    %     filePrefix = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)];
    %     disp([num2str(cc) ': ' filePrefix]);
    %     doSingleCell(num2str(population(cc).prefix),population(cc).runNum,1,population(cc).nGen-population(cc).nPostHoc,40,population(cc).monkeyId);
    % end
        
    score = {population.score_3d};
    monkeyId = [population.monkeyId];
    goodCells = cellfun(@(x) ~isempty(x),score);
    monkeyId = monkeyId(goodCells);
    
    score = cell2mat(score);
    
    % for both monkeys cdf
    figure('color','w','pos',[1000,898,853,440])
    h = cdfplot(score(monkeyId == 1)); h.LineWidth = 2; hold on;
    h = cdfplot(score(monkeyId == 3)); h.LineWidth = 2; 
    h = cdfplot(score); h.LineWidth = 2; 
    % h = cdfplot(score_dcn); h.LineWidth = 2;
    fixPlot(gca,'Solid Preference Index',{'Monkey 1' 'Monkey 2' 'Both Monkeys'})
    axis equal; set(gca,'YLim',[0 1],'xtick',-1:0.5:1,'ytick',0:0.25:1);
    screen2png('plots/population/3dScore_cdf.png');
    plot2svg('plots/population/3dScore_cdf.svg');
    
    % for dcn comparison
    % figure('color','w','pos',[1000,898,853,440])
    % h = cdfplot(score); h.LineWidth = 2; 
    % h = cdfplot(score_dcn); h.LineWidth = 2;
    % fixPlot(gca,'Solid Preference Index',{'Real' 'Alexnet'})
    % axis equal; set(gca,'YLim',[0 1],'xtick',-1:0.5:1,'ytick',0:0.25:1);
    % screen2png(['plots/population/3dScore_cdf_' netLayerName '.png']);
    % plot2svg(['plots/population/3dScore_cdf_' netLayerName '.svg']);
end

function [score,score_dcn] = doSingleCell(prefix,runNum,startGen,endGen,nStim,monkeyId)
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
        score = [];
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