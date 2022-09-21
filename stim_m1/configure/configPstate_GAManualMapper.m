function configPstate_GAManualMapper
% manual mapping with closed loop bsplines

    global Pstate

    Pstate = struct; %clear it

    paramNames = {'x_pos','y_pos','xysize','ori','stimpath','stimnr','fore_r','fore_g','fore_b','background','contrast'};
    dataTypes = {'int','int','float','float','string','int','float','float','float','int','float'};
    defaultValues = {1000,700,5,0,'/GaManualMapper',1,1,1,1,0,100};
    redundantValues = {0,0,0,0,1,1,0,0,0,0,0};
    units = {'pixels','pixels','deg','deg','','','','','','','%'};

    for i=1:length(paramNames)
        Pstate.param{i} = {paramNames{i} dataTypes{i} defaultValues{i} redundantValues{i} units{i}};
    end
end