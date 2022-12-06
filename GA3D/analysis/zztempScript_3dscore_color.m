loadedFile = load('plots/population/ids.mat');
population = loadedFile.population;

for ii=1:length(population)
    if population(ii).monkeyId==1
        load(['stim/dobby/' num2str(population(ii).prefix) '_r-' num2str(population(ii).runNum) '_g-1/stimParams.mat'])
    else
        load(['stim/gizmo/' num2str(population(ii).prefix) '_r-' num2str(population(ii).runNum) '_g-1/stimParams.mat'])
    end
    population(ii).stimColor = stimuli{1}.shape.color;
end

%%
cols = reshape([population.stimColor],3,169)';
cols = cols(~cellfun(@isempty,{population.score_3d}),:);
sc3d = [population.score_3d];

[sc3d,id3d] = sort(sc3d);
cols = cols(id3d,:);

hFig = figure('color','w','pos',[1000,900,480,438]);
% h = cdfplot(sc3d);
h = histogram(sc3d,-1:0.01:1,'Normalization','cdf','DisplayStyle','stairs');
h.LineWidth =2;
a = cumsum(histcounts(sc3d,-1:0.01:1))/143;
grid on;  hold on; axis square

h = gca;
h.LineWidth = 2; h.Color = 'w';
h.XColor = 'k'; h.YColor = 'k';
h.XLim = [-1 1]; h.YLim = [0 1.1];
h.YTick = [0 0.5 1];
h.TickDir = 'out'; h.LineWidth = 2;
h.FontSize = 20; h.FontName = 'Lato';
h.XLabel.String = 'Solid Preference Index';
h.XLabel.FontSize = 20; h.XLabel.FontName = 'Lato';
h.YLabel.String = 'Probability';
h.YLabel.FontSize = 20; h.YLabel.FontName = 'Lato';

for ii=1:length(sc3d)
    if sum(cols(ii,:)) == 3
        cols(ii,:) = [0 0 0];
    end
    line([sc3d(ii) sc3d(ii)],[1.05 1.1],'color',cols(ii,:),'linewidth',2);
    
    yy = a(histcounts(sc3d(ii),-1:0.01:1) == 1);
    plot(sc3d(ii),yy,'o','MarkerEdgeColor','k','MarkerFaceColor',cols(ii,:));
end
screen2png('~/Desktop/plot1.png');

%%
widx = sum(cols == 0,2)==3;
cidx = ~widx;

hFig = figure('color','w','pos',[1000,900,480,438]);
h = histogram(sc3d(widx),-1:0.05:1,'DisplayStyle','stairs','Normalization','cdf'); h.LineWidth =2; hold on
h = histogram(sc3d(cidx),-1:0.05:1,'DisplayStyle','stairs','Normalization','cdf'); h.LineWidth =2;
grid on;  hold on; axis square

h = gca;
h.LineWidth = 2; h.Color = 'w';
h.XColor = 'k'; h.YColor = 'k';
h.XLim = [-1 1]; h.YLim = [0 1];
h.YTick = [0 0.5 1];
h.TickDir = 'out'; h.LineWidth = 2;
h.FontSize = 20; h.FontName = 'Lato';
h.XLabel.String = 'Solid Preference Index';
h.XLabel.FontSize = 20; h.XLabel.FontName = 'Lato';
h.YLabel.String = 'Probability';
h.YLabel.FontSize = 20; h.YLabel.FontName = 'Lato';

hl = legend(h,{'white' 'color'});
hl.FontSize = 12; hl.TextColor = 'k'; hl.Color = 'w'; hl.Box = 'off';
hl.Location = 'NorthWest';
screen2png('~/Desktop/plot2.png');

%%

widx = widx(sc3d>0); cidx = ~widx;
sc3d = sc3d(sc3d>0);

hFig = figure('color','w','pos',[1000,900,480,438]);
h = histogram(sc3d(widx),-1:0.01:1,'DisplayStyle','stairs','Normalization','cdf'); h.LineWidth =2; hold on
h = histogram(sc3d(cidx),-1:0.01:1,'DisplayStyle','stairs','Normalization','cdf'); h.LineWidth =2;
grid on;  hold on; axis square

h = gca;
h.LineWidth = 2; h.Color = 'w';
h.XColor = 'k'; h.YColor = 'k';
h.XLim = [0 1]; h.YLim = [0 1];
h.YTick = [0 0.5 1];
h.TickDir = 'out'; h.LineWidth = 2;
h.FontSize = 20; h.FontName = 'Lato';
h.XLabel.String = 'Solid Preference Index';
h.XLabel.FontSize = 20; h.XLabel.FontName = 'Lato';
h.YLabel.String = 'Probability';
h.YLabel.FontSize = 20; h.YLabel.FontName = 'Lato';

hl = legend(h,{'white' 'color'});
hl.FontSize = 12; hl.TextColor = 'k'; hl.Color = 'w'; hl.Box = 'off';
hl.Location = 'NorthWest';
screen2png('~/Desktop/plot3.png');
