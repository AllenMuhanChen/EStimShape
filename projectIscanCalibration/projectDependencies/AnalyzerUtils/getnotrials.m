function nt = getnotrials(Analyzer)


nc = getnoconditions(Analyzer);

nt = 0;
for c = 1:nc
    nr = length(Analyzer.loops.conds{c}.repeats);
    nt = nt+nr;
end