function configureDisplay

clear all; close all %#ok<CLFUN>

Priority(5);  %Make sure priority is set to "real-time"  

% priorityLevel=MaxPriority(w);
% Priority(priorityLevel);

configurePstate('GM')
disp('PState configured');

configureMstate
disp('MState configured');

configCom;
disp('Com configured');

configSync;
disp('Sync configured');

screenconfig;
disp('Screens configured');
