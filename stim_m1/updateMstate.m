function updateMstate(pname,pval)
% disp('Mstate updating...');
global Mstate

if strcmp(pname,'screenDist') || strcmp(pname,'running')   
    eval(['Mstate.' pname ' = str2num(pval);']);
else
    eval(['Mstate.' pname ' = pval;']);
end

% disp('Mstate updated');

