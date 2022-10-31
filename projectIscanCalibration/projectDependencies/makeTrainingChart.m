stats = [11	199	200	199	196	198	192	298
0	0	0	0	3	2	4	9
0	1	0	1	1	0	4	4];

stats = [stats zeros(3,1) sum(stats')'];

perstats = stats./repmat(sum(stats),[3 1]) * 100;

bar(perstats','stack'); colormap copper; set(gca,'xticklabel',sum(stats),'ytick',[0 25 50 75 100],'ylim',[0 100]); grid on; box off;
xlabel('Total trials'); legend({'Complete','Break','Fail'},'Location','SouthEast'); title('Stats over the course of the day');

filename = ['/Users/Ramanujan/Dropbox/Documents/Hopkins/NHP2PV4/projectSilvaTraining/TrainingStats/' datestr(now,'yymmdd') '.png'];

print(filename,'-dpng');