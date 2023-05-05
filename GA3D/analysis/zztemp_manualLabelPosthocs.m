a = load('plots/population/ids.mat');
population = a.population; 

getPaths;

for cc=1:length(population)
    if population(cc).nPostHoc > 0
        folderName = [num2str(population(cc).prefix) '_r-' num2str(population(cc).runNum)]; 
        postHocGens = population(cc).nGen-population(cc).nPostHoc+1 : population(cc).nGen;
        postHocIds = nan(1,population(cc).nPostHoc);
        for genNum=1:population(cc).nPostHoc
            genId = postHocGens(genNum);
            fullFolderName = [folderName '_g-' num2str(genId)];

            rData = load([respPath '/' fullFolderName '/resp.mat']);
            sData = load([stimPath '/' fullFolderName '/stimParams.mat']);

            imshow(['plots/' folderName '/' fullFolderName '/' fullFolderName '_l-1_allStim.png'])
            postHocIds(genNum) = validatedInput('Enter posthoc id: ',1:11);
        end
    else
        postHocIds = [];
    end
    population(cc).postHocIds = postHocIds;
%     save('plots/population/ids.mat','population','-append')
 end