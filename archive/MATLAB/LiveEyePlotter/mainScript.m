%% Initialization
clear all;
close all;

global conn;
global screen_width_deg; global screen_height_deg; global fixation_color; global fixation_size;
conn = getDbConn(); %outside of function

%% Set-up for Saving Data
home_path = "C:\Users\a1_allen\Documents\Saccade Training Eye Traces";
path = fullfile(home_path,date);
if ~exist(date)
    disp("Creating new directory at "+path)
    mkdir(path);
end 

%% 
%Variables for Plotting
%Screen Size
monkey_screen_width_mm = SystemVar(conn, "xper_monkey_screen_width");
monkey_screen_height_mm = SystemVar(conn, "xper_monkey_screen_height");
monkey_screen_distance_mm = SystemVar(conn, "xper_monkey_screen_distance");
screen_width_deg = rad2deg(2*atan((monkey_screen_width_mm/2)/(2*monkey_screen_distance_mm)));
screen_height_deg = rad2deg(2*atan((monkey_screen_height_mm)/(2*monkey_screen_distance_mm)));
%Fixation Point
fixation_color = [SystemVar(conn, "xper_fixation_point_color", 0), SystemVar(conn, "xper_fixation_point_color", 1), SystemVar(conn, "xper_fixation_point_color", 2)];
fixation_size_mm = SystemVar(conn, "xper_fixation_point_size"); %in mm within xper
fixation_size = rad2deg(2*atan(fixation_size_mm/(2*monkey_screen_distance_mm)));

%% Main Loop
programStop=0;
recentTrialStop = maxTrialStop();
previousTrialStop = recentTrialStop;


fig = figure('Name', 'Live Eye Traces', 'NumberTitle', 'off','Position', [6, 1378, 1592, 1098]);
set(fig, 'InvertHardCopy', 'off');
while ~programStop
    recentTrialStop = maxTrialStop();
    

    if recentTrialStop > previousTrialStop %There's a new trial in the db
        if ~isempty(TStampBetween(previousTrialStop, recentTrialStop, "FixationSucceed")) %Fixation was successful
            disp("New trial found")
            try
            ParseTrial(previousTrialStop, recentTrialStop, fig);
            figure(fig);
            filename = [datestr(now, 'HH-MM-SS') '.fig'];
           % savefig(fullfile(path,filename));
            filename = [datestr(now, 'HH-MM-SS') '.png'];
            %saveas(fig, fullfile(path,filename));
            
            catch E
                warning('Problematic Loading... Skipping')
                msgText = getReport(E)
            end 
                
        end 
    end 
    
    
    previousTrialStop = recentTrialStop;
end 