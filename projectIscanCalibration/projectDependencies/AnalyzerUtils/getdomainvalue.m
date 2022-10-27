%this function returns the names of the domains, the values for each domain
%in each condition, and the condition id for the blank (if present,
%otherwise empty)
function [domains,domval,blankid]=getdomainvalue(Analyzer)

nc = getnoconditions(Analyzer);

%get blank id
bflag=0;
blankid=[];
if stimblank(nc,Analyzer) %if present, blank is always the last condition 
    blankid=nc;
    bflag=1;
end

%get domain names
domains=Analyzer.loops.conds{1}.symbol;
ndom=length(domains);

%get values for every condition
for i=1:nc-bflag
    for j=1:ndom
        domval(i,j)=Analyzer.loops.conds{i}.val{j};
    end
end

