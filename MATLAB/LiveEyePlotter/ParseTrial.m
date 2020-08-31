

function ParseTrial(trialInit_tstamp, trialStop_tstamp, fig)
global conn;
conn = DBConnect(); %outside of function
global screen_width_deg; global screen_height_deg; global fixation_color; global fixation_size;

%% Parsing
[xs_left, ys_left, xs_right, ys_right] = Parse_behmsgeye(trialInit_tstamp, trialStop_tstamp);
TargetOn_tstamp = TStampBetween(trialInit_tstamp, trialStop_tstamp, "TargetOn");
[targetPos_x, targetPos_y, targetEyeWindowSize] = Parse_TargetOn(TargetOn_tstamp);


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
xlim([-screen_width_deg, screen_width_deg]);
ylim([-screen_height_deg, screen_height_deg]);
pos = fig.Children(1).Position; 
xAxisLengthPoints = pos(3);
xAxisLengthDegrees = fig.Children(1).XLim(2)-fig.Children(1).XLim(1);
xDeg2PointsScalar = xAxisLengthPoints/xAxisLengthDegrees;
%plot(targetPos_x, targetPos_y, 'Marker', 'o', 'MarkerSize', targetEyeWindowSize * xDeg2PointsScalar);
rectangle('Position', [targetPos_x, targetPos_y, (targetEyeWindowSize * xDeg2PointsScalar), (targetEyeWindowSize * xDeg2PointsScalar)], 'Curvature', [1,1], 'EdgeColor','r');
hold off;

subplot(1,2,2);  
plot(xs_right, ys_right, 'Color',[1,1,1]);
axis equal;
hold on;
%plot(0, 0, 'Marker', 'square', 'MarkerEdgeColor',fixation_color, 'MarkerFaceColor', fixation_color)
rectangle('Position', [0, 0, fixation_size, fixation_size], 'EdgeColor',fixation_color, 'FaceColor', fixation_color);
set(gca,'Color','k')
title('Right Eye'); xlabel('X-Position (degrees)'); ylabel('Y-Position (degrees)');
xlim([-screen_width_deg screen_width_deg]);
ylim([-screen_height_deg, screen_height_deg]);
pos = fig.Children(2).Position; 
xAxisLengthPoints = pos(3);
xAxisLengthDegrees = fig.Children(2).XLim(2)-fig.Children(2).XLim(1);
xDeg2PointsScalar = xAxisLengthPoints/xAxisLengthDegrees;
rectangle('Position', [targetPos_x, targetPos_y, (targetEyeWindowSize * xDeg2PointsScalar), (targetEyeWindowSize * xDeg2PointsScalar)], 'Curvature', [1,1], 'EdgeColor','r');
hold off; 
%plot(targetPos_x, targetPos_y, 'Marker', 'o', 'MarkerSize', xDeg2PointsScalar * targetEyeWindowSize);
end 