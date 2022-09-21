function saveLog_NatGrat(trial,data)

global Mstate

root = '/log_files/';

expt = [Mstate.anim '_' Mstate.unit '_' Mstate.expt];

fname = [root expt '.mat'];

%need to change the name of the saved variable every trial, otherwise
%things get overwritten
eval(['condTrial' num2str(trial) '=data;'])
if trial==1
    save(fname,['condTrial' num2str(trial)]);
else
    save(fname,['condTrial' num2str(trial)],'-append');
end