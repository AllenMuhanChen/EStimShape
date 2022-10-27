function triallist=getcondtrial(Analyzer)

nrtrials=getnotrials(Analyzer);
nrcond=getnoconditions(Analyzer);

triallist=zeros(nrtrials,1);
for i=1:nrcond
    nrrep=getnorepeats(i,Analyzer);
    for r=1:nrrep
        trep=Analyzer.loops.conds{i}.repeats{r}.trialno;
        triallist(trep)=i;
    end
end
