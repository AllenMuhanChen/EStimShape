function updatePstate(psymbol,pval)

global Pstate
idx = -1;
for i = 1:length(Pstate.param)
    if strcmp(psymbol,Pstate.param{i}{1})
    	idx = i;
        break;
    end
end

if idx == -1
    disp(['Param not found while trying to set ' psymbol ' = ' pval '.']);
end


switch Pstate.param{idx}{2}
    
   case 'float'
      Pstate.param{idx}{3} = str2num(pval);
   case 'int'
      Pstate.param{idx}{3} = str2num(pval);
   case 'string'
      Pstate.param{idx}{3} = pval;
end
   


