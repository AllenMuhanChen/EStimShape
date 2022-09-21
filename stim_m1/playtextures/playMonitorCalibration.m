function playMonitorCalibration
global  screenPTR

cols1 = [linspace(0,255,10)' zeros(10,2)];
cols2 = circshift(cols1,1,2);
cols3 = circshift(cols1,2,2);
cols4 = [cols1(:,1) cols1(:,1) cols1(:,1)];
cols = round([cols1; cols2; cols3; cols4]);

for ii=1:size(cols,1)
    newText = [num2str(ii) ': ' num2str(cols(ii,1)) ', ' num2str(cols(ii,2)) ', ' num2str(cols(ii,3))];
    Screen(screenPTR, 'FillRect', cols(ii,:)); 
    Screen(screenPTR,'DrawText',newText,40,30,255);
    Screen('Flip', screenPTR);
    pause
end
Screen(screenPTR, 'FillRect', 0.5)
Screen(screenPTR, 'Flip');

Screen('Close')   %Get rid of all textures/offscreen windows

