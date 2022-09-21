function pval = getParamVal(psymbol)

global Pstate

idx = -1;

for i = 1:length(Pstate.param)
    if strcmp(psymbol,Pstate.param{i}{1})
    	idx = i;
        break;
    end
end

if idx == -1
    disp(['Cannot find parameter: ' psymbol]);
else
    pval = Pstate.param{idx}{3};
end
