close all

if ~exist('corrScores','var')
    load('data/corrScores.mat')
end

figure('pos',[826,521,1580,734],'color','w');

h = subplot(241); histogram([corrScores.neu_s],15,'DisplayStyle','stairs','LineWidth',2); fixPlot(h,'corrcoef - s','# cells',0:0.5:1,0:5:20,'s');
h = subplot(242); histogram([corrScores.neu_r],15,'DisplayStyle','stairs','LineWidth',2); fixPlot(h,'corrcoef - r','# cells',0:0.5:1,0:5:20,'r');
h = subplot(243); histogram([corrScores.neu_t],15,'DisplayStyle','stairs','LineWidth',2); fixPlot(h,'corrcoef - t','# cells',0:0.5:1,0:5:20,'t');
% h = subplot(244); histogram([corrScores.neu_surf],15,'DisplayStyle','stairs','LineWidth',2); fixPlot(h,'corrcoef - surf','# cells',0:0.5:1,0:5:20,'surf');

subplot(244);  hold on; 
cdfplot([corrScores.neu_s]);
cdfplot([corrScores.neu_r]); 
cdfplot([corrScores.neu_t]); 
fixPlot(gca,'r value','probability',0:0.5:1,0:0.5:1);

h = subplot(245);  hold on; line([0 1],[0 1],'LineWidth',3,'LineStyle',':','color','k');
plot([corrScores.neu_s],[corrScores.neu_r],'.','markersize',15); fixPlot(h,'s','r',0:0.5:1,0:0.5:1);
h = subplot(246);  hold on; line([0 1],[0 1],'LineWidth',3,'LineStyle',':','color','k');
plot([corrScores.neu_r],[corrScores.neu_t],'.','markersize',15); fixPlot(h,'r','t',0:0.5:1,0:0.5:1);
h = subplot(247);  hold on; line([0 1],[0 1],'LineWidth',3,'LineStyle',':','color','k');
plot([corrScores.neu_t],[corrScores.neu_s],'.','markersize',15); fixPlot(h,'t','s',0:0.5:1,0:0.5:1);

h = subplot(248);
notBoxPlot([corrScores.neu_s],1*ones(length([corrScores.neu_s]),1))
notBoxPlot([corrScores.neu_r],2*ones(length([corrScores.neu_r]),1))
notBoxPlot([corrScores.neu_t],3*ones(length([corrScores.neu_t]),1))
% notBoxPlot([corrScores.neu_surf],4*ones(length([corrScores.neu_surf]),1))
notBoxPlot([corrScores.neu_comb],5*ones(length([corrScores.neu_comb]),1))
fixPlot(h,'types','corrcoef',0:6,0:0.5:1);
set(h,'XTick',1:5,'XTickLabel',{'s','r','t','surf','comb'})
grid(h,'off');

% screen2png('plots/population/prediction_corr_comparisons.png')
close


function fixPlot(h,xL,yL,xticks,yticks,titleStr)
    h.LineWidth = 2; h.Color = 'w';
    h.XColor = 'k'; h.YColor = 'k';
    h.Box = 'on'; grid(h,'on');
    
    if exist('xticks','var')
        h.XLim = [min(xticks) max(xticks)]; 
        h.XTick = xticks; 
    end
    
    if exist('yticks','var') && ~isempty(yticks)
        h.YLim = [min(yticks) max(yticks)];
        h.YTick = yticks; 
    end
    
    h.TickDir = 'out'; h.LineWidth = 2;

    h.FontSize = 12; h.FontName = 'Lato';

    h.XLabel.String = xL;
    h.XLabel.FontSize = 18; h.XLabel.FontName = 'Lato';
    h.YLabel.String = yL;
    h.YLabel.FontSize = 18; h.YLabel.FontName = 'Lato';

    if exist('titleStr','var')
        ht = title(h,titleStr);
        ht.Color = 'k'; ht.FontSize = 20; ht.FontName = 'Lato';
    end

    axis(h,'square');
end
