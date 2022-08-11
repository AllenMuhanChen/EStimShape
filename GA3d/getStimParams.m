function stim = getStimParams(idToSearch)
    getPaths;
    [prefix,run,gen,lin,stm] = splitDelimitedStimID2(idToSearch);
    load([stimPath '/' prefix{1} '_r-' num2str(run) '_g-' num2str(gen) '/stimParams.mat']);
    
    stim = stimuli{lin,stm};
end