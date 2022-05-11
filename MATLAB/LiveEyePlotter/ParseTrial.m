

function ParseTrial(trialInit_tstamp, trialStop_tstamp, fig)
global conn;
conn = getDbConn(); %outside of function
global screen_width_deg; global screen_height_deg; global fixation_color; global fixation_size;

%% Parsing
[xs_left, ys_left, xs_right, ys_right] = Parse_behmsgeye(trialInit_tstamp, trialStop_tstamp);
TargetOn_tstamp = TStampBetween(trialInit_tstamp, trialStop_tstamp, "TargetOn");
[targetPos_x, targetPos_y, targetEyeWindowSize] = Parse_TargetOn(TargetOn_tstamp); %should replace this with new parser

%% Plotting
figure(fig);
subplot(1,2,1);
plot(xs_left,ys_left, 'Color', [1,1,1]);
axis equal;
hold on;
%plot(0, 0, 'Marker', 'square', 'MarkerEdgeColor',fixation_color, 'MarkerFaceColor', fixation_color)
rectangle('Position', [0, 0, fixation_size, fixation_size], 'EdgeColor',fixation_color, 'FaceColor', fixation_color);
set(gca,'Color','k')
title('Left Eye'); xlabel('X-Position (degrees)'); ylabel('Y-Position (degrees)');
xlim([-screen_width_deg/2, screen_width_deg/2]);
ylim([-screen_height_deg/2, screen_height_deg/2]);
%plot(targetPos_x, targetPos_y, 'Marker', 'o', 'MarkerSize', targetEyeWindowSize * xDeg2PointsScalar);
%rectangle('Position', [targetPos_x, targetPos_y, (targetEyeWindowSize*2), (targetEyeWindowSize*2)], 'Curvature', [1,1], 'EdgeColor','r');
circle(targetPos_x, targetPos_y, targetEyeWindowSize);
hold off;

subplot(1,2,2);  
plot(xs_right, ys_right, 'Color',[1,1,1]);
axis equal;
hold on;
%plot(0, 0, 'Marker', 'square', 'MarkerEdgeColor',fixation_color, 'MarkerFaceColor', fixation_color)
rectangle('Position', [0, 0, fixation_size, fixation_size], 'EdgeColor',fixation_color, 'FaceColor', fixation_color);
set(gca,'Color','k')
title('Right Eye'); xlabel('X-Position (degrees)'); ylabel('Y-Position (degrees)');
xlim([-screen_width_deg/2 screen_width_deg/2]);
ylim([-screen_height_deg/2, screen_height_deg/2]);
circle(targetPos_x, targetPos_y, targetEyeWindowSize);
%rectangle('Position', [targetPos_x, targetPos_y, targetEyeWindowSize*2, targetEyeWindowSize*2], 'Curvature', [1,1], 'EdgeColor','r');
hold off; 
end 

function circle(x,y,r)
d = r*2;
px = x-r;
py = y-r;
rectangle('Position',[px py d d],'Curvature',[1,1], 'EdgeColor','r');
daspect([1,1,1])
end 